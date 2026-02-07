# モデル環境変数切替（手動ダウンロード前提）実装計画

**作成日**: 2026-01-24
**目的**: LLMモデルを環境変数だけで切り替え可能にする。ただしモデルの取得はユーザーが事前に手動で実施する前提。

---

## ゴール
- Planner / Worker / Writer の各モデルを環境変数で指定できる。
- デフォルト値は既存挙動（Planner=Writer=`deepseek-r1:7b`, Worker=`qwen2.5:3b`）を維持。
- 翻訳関連の挙動はこの計画では変更しない（既存Opus-MTのまま）。

## 非ゴール
- モデルの自動ダウンロード（別計画で対応）。
- 翻訳バックエンド拡張（別計画で対応）。

## 追加・変更する環境変数
| 変数 | 用途 | デフォルト | 備考 |
|------|------|------------|------|
| `PLANNER_MODEL` | プランナー用 | `deepseek-r1:7b` | 既存。READMEの説明を「計画に使用するモデル」に修正 |
| `WORKER_MODEL` | リサーチャー/スクレイパー/レビュアー用 | `qwen2.5:3b` | 既存 |
| `WRITER_MODEL` | ライター専用モデル | （未設定時は `planner_model` の値を使用） | **新規**。明示的に指定すれば上書き可能 |

## 実装方法

`writer_model` のデフォルト値を `planner_model` と同一にするため、property を使用する：

```python
@dataclass
class Settings:
    # ... 既存フィールド ...
    _writer_model: str = field(default="")

    def __post_init__(self) -> None:
        # ... 既存処理 ...
        self._writer_model = os.getenv("WRITER_MODEL", "")

    @property
    def writer_model(self) -> str:
        """Return writer model, falling back to planner_model if not set."""
        return self._writer_model if self._writer_model else self.planner_model
```

## 変更ファイル
- `src/config.py` : `_writer_model` フィールドと `writer_model` property を追加。
- `src/nodes/writer.py` : `settings.writer_model` を使用するよう変更。
- `tests/test_config.py` : `WRITER_MODEL` の読み込みとデフォルト挙動をテスト。
- `tests/nodes/test_writer.py` : 既存の `test_writer_uses_planner_model` を `test_writer_uses_writer_model` に修正。
- `README.md` : 環境変数一覧を更新（`PLANNER_MODEL` の説明修正 + `WRITER_MODEL` 追加）。

## 実装順序（TDD）
1. `tests/test_config.py` に `writer_model` のデフォルト＆ENV反映テストを追加（Red）。
2. `src/config.py` に `_writer_model` フィールドと `writer_model` property を追加（Green）。
3. `tests/nodes/test_writer.py` の `test_writer_uses_planner_model` を `test_writer_uses_writer_model` に修正（Red）。
4. `src/nodes/writer.py` を `settings.writer_model` 参照に変更（Green）。
5. `README.md` を更新（Refactor/Doc）：
   - `PLANNER_MODEL` の説明を「計画・執筆に使用するモデル」→「計画に使用するモデル」に修正
   - `WRITER_MODEL` 行を追加：「執筆に使用するモデル（デフォルト: PLANNER_MODELと同一）」

## 検証
```bash
uv run pytest tests/test_config.py tests/nodes/test_writer.py
```

## ロールバック方針
- `WRITER_MODEL` を未設定に戻す（または環境変数を削除）ことで従来挙動に復帰。

