# モデル自動ダウンロードと翻訳バックエンド拡張 実装計画

**作成日**: 2026-01-24
**目的**: 以下2点を実装する
1. Ollamaモデルの自動ダウンロード（未取得モデルを自動pull）
2. 翻訳手段の選択（Opus-MT / Ollama LLM / DeepL API）

---

## ゴール

- 未ダウンロードのOllamaモデルを自動でpullできる
- 環境変数で翻訳バックエンドを切り替えられる（`opus_mt` / `ollama` / `deepl`）
- デフォルト挙動（Opus-MT + 既定モデル）は維持
- TDDで既存テストを維持しつつ、新機能をカバー

## 非ゴール

- 翻訳品質のチューニング（温度、プロンプト最適化など）
- `WRITER_MODEL` の分離（必要であれば別途対応）

---

## 追加・変更する環境変数

| 変数 | 用途 | デフォルト | 備考 |
|------|------|------------|------|
| `PLANNER_MODEL` | Planner/Writer用 | `deepseek-r1:7b` | 既存 |
| `WORKER_MODEL` | Scraper/Reviewer用 | `qwen2.5:3b` | 既存 |
| `TRANSLATION_PROVIDER` | 翻訳バックエンド | `opus_mt` | `opus_mt` / `ollama` / `deepl` |
| `TRANSLATION_MODEL` | Ollama翻訳用モデル | (worker_model) | `ollama`時のみ使用 |
| `DEEPL_API_KEY` | DeepL APIキー | (空) | `deepl`時は必須 |
| `TRANSLATION_DEVICE` | 翻訳デバイス | `auto` | 既存。`opus_mt`時のみ使用 |
| `ENABLE_TRANSLATION` | 翻訳有効化 | `true` | 既存 |
| `AUTO_PULL_CONFIRM` | 未取得モデルのpull確認 | `ask` | `ask`=初回対話確認、`yes`=自動許可、`no`=拒否（CI用） |

---

## Part 1: Ollamaモデル自動ダウンロード

### 変更ファイル

- `src/llm.py` - 自動pull機能を追加
- `tests/test_llm.py` - テスト追加

### 実装内容

```python
# src/llm.py に追加
import aiohttp

async def _check_model_exists(model: str) -> bool:
    """Ollama API (GET /api/tags) でモデル存在確認"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{settings.ollama_url}/api/tags") as resp:
            if resp.status != 200:
                raise ConnectionError(f"Ollama API error: {resp.status}")
            data = await resp.json()
            return any(m["name"] == model for m in data.get("models", []))

async def _pull_model(model: str) -> None:
    """Ollama API (POST /api/pull) でモデルダウンロード

    Note: ダウンロード中は進捗をログ出力（ストリーミングレスポンス処理）
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{settings.ollama_url}/api/pull",
            json={"name": model},
        ) as resp:
            async for line in resp.content:
                data = json.loads(line)
                if "status" in data:
                    logger.info(f"Pulling {model}: {data['status']}")
                if data.get("error"):
                    raise RuntimeError(f"Pull failed: {data['error']}")

async def _prompt_user_confirmation(model: str) -> bool:
    """非同期環境での対話確認（run_in_executor で stdin 読み取り）"""
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None,
        lambda: input(f"Model '{model}' not found. Download? [y/N]: ")
    )
    return answer.lower() in ("y", "yes")

async def ensure_model_available(model: str) -> None:
    """モデルが存在しなければpullを実行

    - `AUTO_PULL_CONFIRM=ask`（デフォルト）：初回のみ対話プロンプトで確認し、Yes の場合に pull 実行
    - `AUTO_PULL_CONFIRM=yes`：無条件で pull（非対話／CI 向け）
    - `AUTO_PULL_CONFIRM=no`：pull せずエラー返却（大容量モデル回避）
    """
    if await _check_model_exists(model):
        return

    confirm_mode = os.getenv("AUTO_PULL_CONFIRM", "ask").lower()

    if confirm_mode == "no":
        raise RuntimeError(f"Model '{model}' not found and auto-pull is disabled")

    if confirm_mode == "ask":
        if not await _prompt_user_confirmation(model):
            raise RuntimeError(f"Model '{model}' not found (user declined download)")

    logger.info(f"Downloading model: {model}")
    await _pull_model(model)
```

`call_llm()` を修正し、LLM呼び出し前に `ensure_model_available()` を呼ぶ。
Ollama 呼び出しのみ対象にし、OpenAI 等のリモートモデル経由ではスキップ。

### Ollama API

- `GET {ollama_url}/api/tags` - モデル一覧取得
- `POST {ollama_url}/api/pull` - モデルダウンロード（ストリーミングレスポンス）

### テストケース

```python
class TestCheckModelExists:
    async def test_returns_true_for_existing_model(self): ...
    async def test_returns_false_for_missing_model(self): ...
    async def test_handles_connection_error(self): ...

class TestPullModel:
    async def test_calls_ollama_pull_api(self): ...
    async def test_raises_error_on_failure(self): ...

class TestEnsureModelAvailable:
    async def test_does_not_pull_existing_model(self): ...
    async def test_pulls_missing_model(self): ...
    async def test_prompts_and_respects_no(self): ...
    async def test_env_yes_skips_prompt(self): ...

class TestCallLlmAutoPull:
    async def test_auto_pulls_missing_model(self): ...
    async def test_skips_for_non_ollama_models(self): ...
```

---

## Part 2: 翻訳バックエンド拡張

### アーキテクチャ

Strategy パターンで複数バックエンドを抽象化:

```
src/tools/translate/
├── __init__.py       # 公開API（後方互換性維持）
├── base.py           # TranslationBackend Protocol + TranslationResult
├── opus_mt.py        # 既存Opus-MT実装をリファクタ
├── ollama.py         # Ollama LLM翻訳（新規）
├── deepl.py          # DeepL API翻訳（新規）
└── factory.py        # get_translation_backend() ファクトリ
```

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/config.py` | 新設定追加 |
| `src/tools/translate.py` | ディレクトリ構造へ移行 |
| `src/nodes/translator.py` | async翻訳対応 |

### 設定追加 (config.py)

```python
# 新規フィールド
translation_provider: str = "opus_mt"  # opus_mt / ollama / deepl
translation_model: str = ""            # Ollama翻訳用（空ならworker_model）
deepl_api_key: str = ""                # DeepL APIキー
```

### バックエンド実装

**base.py - Protocol定義:**
```python
from dataclasses import dataclass
from typing import Protocol

@dataclass
class TranslationResult:
    """翻訳結果を格納するデータクラス（既存定義を移行）"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str

class TranslationError(Exception):
    """翻訳エラーの基底クラス（各バックエンドで発生する例外をラップ）"""
    pass

class TranslationBackend(Protocol):
    async def translate_to_english(self, text: str, source_language: str) -> TranslationResult: ...
    async def translate_from_english(self, text: str, target_language: str) -> TranslationResult: ...
```

**opus_mt.py:**
- 既存コードをクラス化
- 同期処理を `asyncio.to_thread` でラップ

```python
class OpusMTBackend:
    """Opus-MT による翻訳バックエンド（既存実装をクラス化）"""

    def _sync_translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> TranslationResult:
        """同期処理（既存の translate_to_english/translate_from_english のロジック）"""
        model, tokenizer = _load_model(source_lang, target_lang)
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        outputs = model.generate(**inputs)
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return TranslationResult(
            original_text=text,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
        )

    async def translate_to_english(
        self, text: str, source_language: str
    ) -> TranslationResult:
        return await asyncio.to_thread(
            self._sync_translate, text, source_language, "en"
        )

    async def translate_from_english(
        self, text: str, target_language: str
    ) -> TranslationResult:
        return await asyncio.to_thread(
            self._sync_translate, text, "en", target_language
        )
```

**ollama.py:**
```python
# 翻訳プロンプトテンプレート
TRANSLATION_PROMPT = """Translate the following text from {source_lang} to {target_lang}.
Output ONLY the translated text, nothing else. Do not add any explanations or notes.

Text: {text}

Translation:"""

class OllamaBackend:
    """Ollama LLM による翻訳バックエンド"""

    def __init__(self, model: str | None = None):
        self.model = model or settings.translation_model or settings.worker_model

    async def translate_to_english(
        self, text: str, source_language: str
    ) -> TranslationResult:
        prompt = TRANSLATION_PROMPT.format(
            source_lang=source_language, target_lang="English", text=text
        )
        translated = await call_llm(prompt, model=self.model, temperature=0.1)
        return TranslationResult(
            original_text=text,
            translated_text=translated.strip(),
            source_language=source_language,
            target_language="en",
        )

    async def translate_from_english(
        self, text: str, target_language: str
    ) -> TranslationResult:
        # 言語コード → 言語名のマッピング
        lang_names = {"ja": "Japanese", "zh": "Chinese", "ko": "Korean", ...}
        target_name = lang_names.get(target_language, target_language)
        prompt = TRANSLATION_PROMPT.format(
            source_lang="English", target_lang=target_name, text=text
        )
        translated = await call_llm(prompt, model=self.model, temperature=0.1)
        return TranslationResult(
            original_text=text,
            translated_text=translated.strip(),
            source_language="en",
            target_language=target_language,
        )
```

**deepl.py:**
```python
class DeepLBackend:
    """DeepL API による翻訳バックエンド"""

    # Free版エンドポイント（Pro版は api.deepl.com）
    # 将来的に DEEPL_API_URL 環境変数で切替可能にする余地を残す
    DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"

    # 言語コード変換マッピング（内部コード → DeepL API コード）
    DEEPL_LANG_CODES = {
        "ja": "JA", "en": "EN", "zh": "ZH", "ko": "KO",
        "de": "DE", "fr": "FR", "es": "ES", "ru": "RU",
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.deepl_api_key
        if not self.api_key:
            raise TranslationError("DEEPL_API_KEY is required for DeepL backend")

    def _to_deepl_code(self, lang: str) -> str:
        """内部言語コードを DeepL API コードに変換"""
        return self.DEEPL_LANG_CODES.get(lang, lang.upper())

    async def translate_to_english(
        self, text: str, source_language: str
    ) -> TranslationResult:
        async with aiohttp.ClientSession() as session:
            data = {
                "auth_key": self.api_key,
                "text": text,
                "source_lang": self._to_deepl_code(source_language),
                "target_lang": "EN",
            }
            async with session.post(self.DEEPL_API_URL, data=data) as response:
                if response.status != 200:
                    error = await response.text()
                    raise TranslationError(f"DeepL API error: {response.status} - {error}")
                result = await response.json()
                translated = result["translations"][0]["text"]
                return TranslationResult(
                    original_text=text,
                    translated_text=translated,
                    source_language=source_language,
                    target_language="en",
                )

    async def translate_from_english(
        self, text: str, target_language: str
    ) -> TranslationResult:
        async with aiohttp.ClientSession() as session:
            data = {
                "auth_key": self.api_key,
                "text": text,
                "source_lang": "EN",
                "target_lang": self._to_deepl_code(target_language),
            }
            async with session.post(self.DEEPL_API_URL, data=data) as response:
                if response.status != 200:
                    error = await response.text()
                    raise TranslationError(f"DeepL API error: {response.status} - {error}")
                result = await response.json()
                translated = result["translations"][0]["text"]
                return TranslationResult(
                    original_text=text,
                    translated_text=translated,
                    source_language="en",
                    target_language=target_language,
                )
```
※ Pro/Free の切替やリージョン（エンドポイント）切替は対象外。将来的に `DEEPL_API_URL` 環境変数を追加する余地を残す。

**factory.py:**
```python
from .base import TranslationBackend
from .opus_mt import OpusMTBackend
from .ollama import OllamaBackend
from .deepl import DeepLBackend
from src.config import settings

def get_translation_backend() -> TranslationBackend:
    """設定に基づいて適切な翻訳バックエンドを返す"""
    provider = settings.translation_provider.lower()

    if provider == "opus_mt":
        return OpusMTBackend()
    elif provider == "ollama":
        return OllamaBackend()
    elif provider == "deepl":
        return DeepLBackend()
    else:
        raise ValueError(f"Unknown translation provider: {provider}")
```

### テストファイル構造

```
tests/tools/translate/
├── __init__.py
├── test_base.py          # Protocol, TranslationResult
├── test_opus_mt.py       # 既存テスト移行
├── test_ollama.py        # 新規
├── test_deepl.py         # 新規
└── test_factory.py       # 新規
```

---

## 実装順序（TDD）

### Phase 1: モデル自動ダウンロード
1. `tests/test_llm.py` にテスト追加（Red）
2. `_check_model_exists()` 実装（Green）
3. `_pull_model()` 実装（Green）
4. `ensure_model_available()` 実装（Green）
5. `call_llm()` 修正（Green）
6. リファクタリング

### Phase 2: 翻訳バックエンド基盤
1. `tests/tools/translate/test_base.py` 作成
2. `src/tools/translate/base.py` 作成
3. `tests/tools/translate/test_opus_mt.py` 移行
4. `src/tools/translate/opus_mt.py` リファクタ
5. `tests/tools/translate/test_factory.py` 作成
6. `src/tools/translate/factory.py` 作成

### Phase 3: 設定拡張
1. `tests/test_config.py` にテスト追加
2. `src/config.py` に新設定追加

### Phase 4: Ollamaバックエンド
1. `tests/tools/translate/test_ollama.py` 作成
2. `src/tools/translate/ollama.py` 実装

### Phase 5: DeepLバックエンド
1. `tests/tools/translate/test_deepl.py` 作成
2. `src/tools/translate/deepl.py` 実装

### Phase 6: 統合
1. `src/tools/translate/__init__.py` で公開API整備
2. `src/nodes/translator.py` をasync翻訳に対応
3. 旧 `src/tools/translate.py` 削除
4. 全テスト実行・統合テスト（translator を呼ぶ全ノードの非同期化を含む）

**`__init__.py` での後方互換性維持:**
```python
# src/tools/translate/__init__.py
from .base import TranslationResult, TranslationError, TranslationBackend
from .factory import get_translation_backend

# 後方互換性のため、既存の関数シグネチャを維持
# 既存コード: from src.tools.translate import translate_to_english
_backend: TranslationBackend | None = None

def _get_backend() -> TranslationBackend:
    global _backend
    if _backend is None:
        _backend = get_translation_backend()
    return _backend

async def translate_to_english(text: str, source_language: str) -> TranslationResult:
    """後方互換性のためのラッパー関数"""
    return await _get_backend().translate_to_english(text, source_language)

async def translate_from_english(text: str, target_language: str) -> TranslationResult:
    """後方互換性のためのラッパー関数"""
    return await _get_backend().translate_from_english(text, target_language)

__all__ = [
    "TranslationResult",
    "TranslationError",
    "TranslationBackend",
    "get_translation_backend",
    "translate_to_english",
    "translate_from_english",
]
```

**`translator.py` の修正箇所:**
```python
# 変更前（現在の同期呼び出し）
result = translate_to_english(task, source_language)

# 変更後（非同期呼び出し）
result = await translate_to_english(task, source_language)
```

**統合テストケース:**
- 各バックエンドでの翻訳ノード実行
- バックエンド切替時の設定反映確認
- エラー時のフォールバック動作（翻訳失敗時は元テキストを保持）

---

## 検証方法

### ユニットテスト
```bash
uv run pytest tests/test_llm.py -v
uv run pytest tests/test_config.py -v
uv run pytest tests/tools/translate/ -v
```

### 手動検証

**モデル自動ダウンロード:**
```bash
# 存在しないモデルを指定して実行
PLANNER_MODEL=llama3.2:1b uv run python -m src.main --demo plan "test"
# → 自動でモデルがダウンロードされることを確認
```

**翻訳バックエンドの切り替え:**
```bash
# Opus-MT（デフォルト）
uv run python -m src.main --demo translate "こんにちは"

# Ollama LLM
TRANSLATION_PROVIDER=ollama uv run python -m src.main --demo translate "こんにちは"

# DeepL
TRANSLATION_PROVIDER=deepl DEEPL_API_KEY=xxx uv run python -m src.main --demo translate "こんにちは"
```

### 全テスト・リンター
```bash
uv run pytest --cov=src
uv run mypy src/
uv run ruff check src/ tests/
```

---

## 影響範囲とリスク

- 既存翻訳（Opus-MT）パスに手を入れるため、キャッシュやモデルダウンロード周りのリグレッションに注意
- Ollama翻訳はプロンプト品質に依存するため、簡易プロンプトテンプレートを用意
- DeepLはAPIキー必須のため、未設定時は明確なエラーメッセージを出力

### エラーハンドリング方針

各バックエンドで発生する例外は `TranslationError` にラップして統一的に処理：

| バックエンド | 発生しうるエラー | 対応 |
|-------------|-----------------|------|
| Opus-MT | モデルロード失敗、メモリ不足 | `TranslationError` でラップ |
| Ollama | 接続エラー、タイムアウト、モデル未取得 | `TranslationError` でラップ |
| DeepL | APIキー未設定、レート制限、文字数上限 | `TranslationError` でラップ |

翻訳ノード（`translator.py`）では `TranslationError` をキャッチし、翻訳失敗時は元テキストを保持する既存の挙動を維持。

---

## ロールバック方針

- 新しい環境変数は任意入力なので、デフォルト値に戻せば従来挙動に復帰
- バックエンド抽象化が原因の不具合は `TRANSLATION_PROVIDER=opus_mt` で切替を固定して暫定回避
- モデル自動ダウンロードは `ensure_model_available()` をスキップするオプションを用意（将来対応）

---

## 成果物一覧

**新規ファイル:**
- `src/tools/translate/base.py`
- `src/tools/translate/opus_mt.py`
- `src/tools/translate/ollama.py`
- `src/tools/translate/deepl.py`
- `src/tools/translate/factory.py`
- `src/tools/translate/__init__.py`
- `tests/tools/translate/test_base.py`
- `tests/tools/translate/test_opus_mt.py`
- `tests/tools/translate/test_ollama.py`
- `tests/tools/translate/test_deepl.py`
- `tests/tools/translate/test_factory.py`

**変更ファイル:**
- `src/llm.py`（自動pull追加）
- `src/config.py`（設定追加）
- `src/nodes/translator.py`（async対応）
- `tests/test_llm.py`（テスト追加）
- `tests/test_config.py`（テスト追加）

**削除ファイル:**
- `src/tools/translate.py`（ディレクトリへ移行）
- `tests/tools/test_translate.py`（ディレクトリへ移行）
