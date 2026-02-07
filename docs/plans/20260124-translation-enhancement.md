# 翻訳機能強化 実装計画

**作成日**: 2026-01-24
**目的**: 翻訳バックエンドを選択可能にし、Opus-MT 以外（Ollama LLM / DeepL API）を追加。既存 API との後方互換性を維持しつつ async 化する。

---

## ゴール
- 環境変数で翻訳バックエンドを `opus_mt` / `ollama` / `deepl` から選択できる。
- バックエンドごとの設定を `config.py` から読み出せる。
- 公開関数 `translate_to_english` / `translate_from_english` のシグネチャ互換を保ちつつ非同期化。
- 既存のデフォルト挙動（Opus-MT + 同期 API）は維持（ラッパーで互換）。

## 非ゴール
- 翻訳品質のプロンプト最適化。
- DeepL の Pro/Free エンドポイント自動切替（将来余地のみ）。

## 追加・変更する環境変数
| 変数 | 用途 | デフォルト | 備考 |
|------|------|------------|------|
| `TRANSLATION_PROVIDER` | 翻訳バックエンド | `opus_mt` | `opus_mt` / `ollama` / `deepl` |
| `TRANSLATION_MODEL` | Ollama 翻訳モデル | (空=worker_model) | Ollama 使用時のみ |
| `DEEPL_API_KEY` | DeepL API キー | (空) | DeepL 使用時必須 |
| `TRANSLATION_DEVICE` | Opus-MT 実行デバイス | `auto` | 既存。GPU/CPU 選択 |
| `ENABLE_TRANSLATION` | 翻訳有効化 | `true` | 既存 |

## ディレクトリ構成
```
src/tools/translate/
├── __init__.py       # 公開APIラッパー（後方互換維持）
├── base.py           # Protocol と共通型定義
├── opus_mt.py        # 既存実装をクラス化し async ラップ
├── ollama.py         # LLM 翻訳実装
├── deepl.py          # DeepL API 実装
└── factory.py        # プロバイダ選択ファクトリ
```

## 変更ファイル
- `src/config.py` : `translation_provider`, `translation_model`, `deepl_api_key` を追加。
- `src/tools/translate.py` : 上記ディレクトリ構成へ移行（旧ファイル削除）。
- `src/nodes/translator.py` : 翻訳呼び出しを async 化し、新ラッパーを await。
- `src/main.py` : `demo_translate` を async 版に対応。
- `tests/tools/translate/…` : バックエンド別テストを新設。
- `tests/nodes/test_translator.py` : async 化＆バックエンド切替のモックテスト。
- `tests/test_config.py` : 新設定のデフォルトと ENV 反映をテスト。

## 実装ステップ（TDD）
1. `tests/tools/translate/test_base.py` で Protocol/型を固定（Red→Green）。
2. `tests/tools/translate/test_opus_mt.py` に既存テストを移植し async 化（Red→Green）。
3. `tests/tools/translate/test_factory.py` でプロバイダ選択をテスト（Red→Green）。
4. `tests/tools/translate/test_ollama.py` / `test_deepl.py` を追加（LLM/HTTP をモック）。（Red→Green）
5. `src/nodes/translator.py` を async 呼び出しに更新し、既存テストを調整。
6. `src/main.py` のデモを await 対応。
7. 旧 `src/tools/translate.py` と `tests/tools/test_translate.py` を削除。

## 検証
```bash
uv run pytest tests/tools/translate/ tests/nodes/test_translator.py tests/test_config.py
```

## ロールバック方針
- `TRANSLATION_PROVIDER=opus_mt` を指定し、旧デフォルト相当のバックエンドを使用する。
- 旧同期 API が必要な場合は `__init__.py` のラッパーで互換を維持するため、設定を戻せば従来挙動に復帰。

