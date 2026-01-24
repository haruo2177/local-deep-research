# 翻訳機能追加実装計画

## 概要
Helsinki-NLP/Opus-MTを使用して、入力言語を自動検出し、出力結果を検出した言語に翻訳する機能を追加する。

## 更新後のワークフロー

```
START → Planner → TranslatorInput → Researcher → Scraper → Reviewer → Writer → TranslatorOutput → END
                       ↑                                       │
                       └────────── not sufficient ─────────────┘
```

- **TranslatorInput**: 言語検出 + タスクを英語に翻訳（内部処理用）
- **TranslatorOutput**: 最終レポートをユーザーの元言語に翻訳

---

## 実装手順（TDD）

### Phase 1: 依存関係追加

**ファイル**: `pyproject.toml`

追加する依存関係:
```toml
"transformers>=4.36.0",
"sentencepiece>=0.2.0",
"torch>=2.1.0",
"langdetect>=1.0.9",
```

### Phase 2: 翻訳ツール実装

#### 2.1 テスト作成
**ファイル**: `tests/tools/test_translate.py` （新規）

テスト項目:
- `TranslationResult` データクラス
- `detect_language()` - 日本語、英語、中国語の検出
- `translate_to_english()` - 各言語から英語への翻訳
- `translate_from_english()` - 英語から各言語への翻訳
- エラーハンドリング（非対応言語）

#### 2.2 実装
**ファイル**: `src/tools/translate.py` （新規）

```python
# 主要な関数
def detect_language(text: str) -> str
def translate_to_english(text: str, source_language: str) -> TranslationResult
def translate_from_english(text: str, target_language: str) -> TranslationResult

# 対応言語
SUPPORTED_LANGUAGES = {
    "ja": "Helsinki-NLP/opus-mt-ja-en",
    "zh": "Helsinki-NLP/opus-mt-zh-en",
    "ko": "Helsinki-NLP/opus-mt-ko-en",
    "de": "Helsinki-NLP/opus-mt-de-en",
    "fr": "Helsinki-NLP/opus-mt-fr-en",
    "es": "Helsinki-NLP/opus-mt-es-en",
    "ru": "Helsinki-NLP/opus-mt-ru-en",
}
```

### Phase 3: 状態拡張

#### 3.1 テスト更新
**ファイル**: `tests/test_state.py`

追加テスト:
- `source_language` フィールドの存在確認
- `original_task` フィールドの存在確認

#### 3.2 実装
**ファイル**: `src/state.py`

追加フィールド:
```python
source_language: str      # ISO 639-1 コード (例: "ja", "en")
original_task: str        # 翻訳前の元タスク
```

### Phase 4: 設定拡張

#### 4.1 テスト更新
**ファイル**: `tests/test_config.py`

追加テスト:
- `enable_translation` 設定
- `translation_device` 設定

#### 4.2 実装
**ファイル**: `src/config.py`

追加設定:
```python
enable_translation: bool = True        # 翻訳機能の有効/無効
translation_device: str = "cpu"        # "cpu" または "cuda"
```

### Phase 5: 翻訳ノード実装

#### 5.1 テスト作成
**ファイル**: `tests/nodes/test_translator.py` （新規）

テスト項目:
- `translator_input_node` - 言語検出と翻訳
- `translator_output_node` - レポート翻訳
- 英語入力時のパススルー
- 翻訳無効時の動作

#### 5.2 実装
**ファイル**: `src/nodes/translator.py` （新規）

```python
async def translator_input_node(state: dict) -> dict:
    """言語検出 + タスクを英語に翻訳"""

async def translator_output_node(state: dict) -> dict:
    """レポートを元言語に翻訳"""
```

### Phase 6: グラフ統合

#### 6.1 テスト更新
**ファイル**: `tests/test_graph.py`

追加テスト:
- `translator_input` ノードの存在
- `translator_output` ノードの存在
- エッジの接続確認

#### 6.2 実装
**ファイル**: `src/graph.py`

変更内容:
- `translator_input` ノード追加（planner → translator_input → researcher）
- `translator_output` ノード追加（writer → translator_output → END）

---

## ファイル一覧

### 新規作成
| ファイル | 説明 |
|---------|------|
| `src/tools/translate.py` | 翻訳ツール（言語検出、翻訳処理） |
| `src/nodes/translator.py` | 翻訳ノード（入力/出力） |
| `tests/tools/test_translate.py` | 翻訳ツールテスト |
| `tests/nodes/test_translator.py` | 翻訳ノードテスト |

### 変更
| ファイル | 変更内容 |
|---------|---------|
| `pyproject.toml` | transformers, sentencepiece, torch, langdetect 追加 |
| `src/state.py` | source_language, original_task フィールド追加 |
| `src/config.py` | enable_translation, translation_device 追加 |
| `src/graph.py` | translator_input, translator_output ノード追加 |
| `tests/test_state.py` | 新フィールドのテスト追加 |
| `tests/test_graph.py` | 新ノードのテスト追加 |
| `tests/conftest.py` | 翻訳関連フィクスチャ追加 |

---

## 検証方法

### 自動テスト
```bash
# 全テスト実行
uv run pytest

# 翻訳関連のみ
uv run pytest tests/tools/test_translate.py tests/nodes/test_translator.py

# 型チェック
uv run mypy src/

# リンター
uv run ruff check src/ tests/
```

### 手動検証
```bash
# 日本語入力でテスト
uv run python -m src.main "人工知能の歴史について教えてください"

# 英語入力でテスト（翻訳なしで動作確認）
uv run python -m src.main "Tell me about the history of AI"
```

### 期待される結果
1. 日本語入力 → 内部処理は英語 → 日本語レポート出力
2. 英語入力 → 翻訳なし → 英語レポート出力
3. 設定で `ENABLE_TRANSLATION=false` → 翻訳スキップ

---

## 注意事項

### 初回実行時
- Helsinki-NLP/Opus-MTモデルが自動ダウンロードされる（言語ペアあたり約300MB）
- 初回のみ時間がかかる

### メモリ使用量
- モデルは`@lru_cache`でキャッシュ（最大4モデル）
- GPU使用時は `TRANSLATION_DEVICE=cuda` を設定

### 長文翻訳
- Opus-MTの入力制限（約512トークン）に注意
- 必要に応じてチャンク分割を実装
