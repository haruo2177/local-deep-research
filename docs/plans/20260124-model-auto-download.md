# モデル自動ダウンロード実装計画

**作成日**: 2026-01-24
**目的**: 指定された Ollama モデルが未取得の場合に自動で pull し、LLM 呼び出しを失敗させないようにする。

---

## ゴール
- Ollama 経由で指定したモデルがローカルに無い場合、自動で `ollama pull` 相当を実行できる。
- CI/非対話環境でもハングしない（確認プロンプトの挙動を ENV で制御）。
- 既存の LLM 呼び出しフローを最小変更で拡張し、テストで回帰を防ぐ。

## 非ゴール
- 翻訳バックエンドの拡張（別計画）。
- モデル選択の ENV 設計（別計画）。

## 追加・変更する環境変数
| 変数 | 用途 | デフォルト | 備考 |
|------|------|------------|------|
| `AUTO_PULL_CONFIRM` | 未取得モデルの自動 pull 動作 | `ask` | `ask`=対話確認, `yes`=無条件許可, `no`=拒否 |

## 変更ファイル
- `src/llm.py` : LLM 呼び出し前にモデル存在チェック＋必要に応じて pull。`aiohttp` で `/api/tags` と `/api/pull` を使用。
- `tests/test_llm.py` : 自動 pull 挙動をモックしてテスト。
- （必要なら）`pyproject.toml` : 追加依存は不要（`aiohttp` 既存）。

## 実装概要
1. `ensure_model_available(model: str)` を追加。
   - `_check_model_exists` : `GET /api/tags` で存在判定。
   - `_pull_model` : `POST /api/pull` ストリームを逐次読み取り、`error` フィールドで例外。
   - `_prompt_user_confirmation` : `AUTO_PULL_CONFIRM=ask` のときのみ stdin で確認。
2. `call_llm` 内で Ollama モデル利用時に `ensure_model_available` を await。
3. 確認モードの分岐: `no` なら例外、`yes` なら即 pull、`ask` は一度だけ質問。
4. 過剰な API 呼び出し防止のため、プロセス内メモ化（確認済みモデル名の set）を導入。

## テストケース（例）
- 既存モデルなら `_pull_model` を呼ばない。
- 未存在モデルで `AUTO_PULL_CONFIRM=yes` ならプロンプトなしで pull。
- `AUTO_PULL_CONFIRM=no` なら例外を投げる。
- `ask` で `n` 応答なら例外、`y` なら pull される。
- 非 Ollama モデル指定時は ensure をスキップ。

## 実装順序（TDD）
1. `tests/test_llm.py` に auto-pull シナリオを追加（Red）。
2. `src/llm.py` に `ensure_model_available` と呼び出しを実装（Green）。
3. リファクタ・ロギング微調整。

## 検証
```bash
uv run pytest tests/test_llm.py -v

# 手動確認（存在しないモデルを指定）
PLANNER_MODEL=llama3.2:1b AUTO_PULL_CONFIRM=yes uv run python -m src.main --demo plan "test"
```

## ロールバック方針
- `AUTO_PULL_CONFIRM=no` を設定すれば pull を無効化し、従来の「モデル未取得なら失敗」挙動に戻せる。

