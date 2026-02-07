# モデル/翻訳切替 実装計画

**作成日**: 2026-01-24
**目的**: 以下2点を環境変数ベースで切り替え可能にする。
- モデル（Planner/Worker/Writer/翻訳）を環境変数で変更可能にする
- 翻訳手段（Opus-MT以外の翻訳経路）を環境変数で選択可能にする

---

## ゴール
- 設定ファイルを書き換えずに環境変数だけでLLMモデルと翻訳バックエンドを差し替えられる。
- デフォルト挙動（Opus-MT + 既定モデル）は壊さない。
- TDDで既存テストを維持しつつ、新設定の分岐をカバーする。

## 非ゴール
- 新規クラウドAPIの導入（OpenAI/Azure等）※将来の拡張を見据えた抽象化のみ実施
- 翻訳品質のチューニング（温度、プロンプト最適化など）

---

## 追加・変更する環境変数（案）
| 変数 | 用途 | デフォルト | 備考 |
|------|------|------------|------|
| `PLANNER_MODEL` | Planner用モデル | `deepseek-r1:7b` | 既存。明示的にドキュメント化し、Writerにも転用可否を制御 |
| `WORKER_MODEL` | Researcher/Scraper要約用 | `qwen2.5:3b` | 既存 |
| `WRITER_MODEL` | Writer用モデル | `PLANNER_MODEL` と同一 | **新規**。別モデル指定を許可 |
| `TRANSLATION_PROVIDER` | 翻訳バックエンド選択 | `opus_mt` | `opus_mt` / `ollama` / `none`（`ENABLE_TRANSLATION=false`と同等） |
| `TRANSLATION_MODEL_OVERRIDES` | 翻訳モデル上書き | `` (空) | JSON文字列。キーは `ja-en` / `en-ja` などのペア |
| `TRANSLATION_OLLAMA_MODEL` | Ollama翻訳時のモデル | `WORKER_MODEL` | `TRANSLATION_PROVIDER=ollama` のみ使用 |
| `TRANSLATION_DEVICE` | 翻訳実行デバイス | `auto` | 既存。`ollama`時は無視 |

---

## アーキテクチャ方針
- `src/tools/translate.py` を「バックエンド選択→実装委譲」の構造に変更。
  - `TranslationBackend` 抽象クラス（interface）
  - `OpusMtBackend`（既存HuggingFaceモデル。言語ペアごとのモデル名を環境変数で上書き可能）
  - `OllamaBackend`（LLMプロンプトでの双方向翻訳。モデルは環境変数で指定）
- 設定は `src/config.py` に集約し、`settings.translation_provider` などの新フィールドを追加。
- ノード層（`translator_input_node` / `translator_output_node`）はバックエンドを注入して利用。既定はOpus-MTで互換保持。

---

## 実装ステップ（TDD）

### Phase 1: 設定拡張
- **テスト**: `tests/test_config.py`
  - 新フィールド: `writer_model`, `translation_provider`, `translation_model_overrides`, `translation_ollama_model`
  - 環境変数での上書き確認（既存のデフォルト破壊しないこと）
- **実装**: `src/config.py`
  - 上記フィールド追加・パース。`TRANSLATION_MODEL_OVERRIDES` はJSONパース失敗時に空辞書でフォールバック。
  - Writerが独立モデルを持てるよう `writer_model` を追加（未指定時は `planner_model` を再利用）。

### Phase 2: 翻訳バックエンド抽象化
- **テスト**: `tests/tools/test_translate.py` を分割/拡張
  - Opus-MT: 既存テストをバックエンドクラス向けに調整。モデル上書きが適用されることをモックで確認。
  - Ollama: `TranslationBackend` インターフェースをモックし、`TRANSLATION_PROVIDER=ollama` でLLM呼び出し関数が使われることを確認（LLMはモック）。
- **実装**: `src/tools/translate.py`
  - バックエンドクラス追加とファクトリ関数 `get_translation_backend(settings)` を実装。
  - 公開関数 `translate_to_english` / `translate_from_english` は内部でバックエンドを解決するように変更し、インターフェース互換を維持。
  - LangDetectまわりの既存挙動は変更しない。

### Phase 3: ノード統合
- **テスト**: `tests/nodes/test_translator.py`
  - `TRANSLATION_PROVIDER=ollama` 時にLLM翻訳が呼ばれる（モックで検証）。
  - `TRANSLATION_PROVIDER=none` または `ENABLE_TRANSLATION=false` で翻訳処理をスキップ。
  - `WRITER_MODEL` が指定された場合にWriterがそのモデルを使用する回帰テストを追加（`tests/nodes/test_writer.py`）。
- **実装**: `src/nodes/translator.py` / `src/nodes/writer.py`
  - バックエンド注入。Writerは `settings.writer_model` を使用。

### Phase 4: ドキュメント更新
- **ファイル**: `README.md`（設定一覧に新環境変数を追記）
- **ファイル**: `docs/plans/` 以外に追加の運用ノートがあれば更新（例: `CLAUDE.md` に翻訳バックエンドの切替手順）。

---

## 影響範囲とリスク
- 既存翻訳（Opus-MT）パスに手を入れるため、キャッシュやモデルダウンロード周りのリグレッションに注意。
- `TRANSLATION_MODEL_OVERRIDES` のJSONパース失敗時は安全に無視するフォールバックを実装し、起動エラーを避ける。
- Ollama翻訳はプロンプト品質に依存するため、簡易プロンプトテンプレートを用意し、テストではモックで挙動を固定。

---

## 成果物一覧
- **新規/変更ファイル**
  - `src/config.py`（設定追加）
  - `src/tools/translate.py`（バックエンド抽象化 + env対応）
  - `src/nodes/translator.py`（バックエンド注入）
  - `src/nodes/writer.py`（`writer_model` 対応）
  - `tests/test_config.py`, `tests/tools/test_translate.py`, `tests/nodes/test_translator.py`, `tests/nodes/test_writer.py`（TDD追加/更新）
  - `README.md`（環境変数ドキュメント）

---

## 検証方法
```bash
# 新設定の単体テスト
uv run pytest tests/test_config.py tests/tools/test_translate.py

# ノード統合テスト（翻訳ON/OFF, Ollama経路）
uv run pytest tests/nodes/test_translator.py tests/nodes/test_writer.py

# 既存回帰チェック
uv run pytest
```

## ロールバック方針
- 新しい環境変数は任意入力なので、デフォルト値に戻せば従来挙動に復帰する。
- バックエンド抽象化が原因の不具合は `TRANSLATION_PROVIDER=opus_mt` かつ `TRANSLATION_MODEL_OVERRIDES=""` で切替を固定して暫定回避。

---

以上の方針で実装を進めれば、環境変数だけでモデルと翻訳手段を安全に切り替えられるようになります。
