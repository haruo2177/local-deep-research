# 実装ログ: Phase 2 - Pythonプロジェクト構造構築

**日時**: 2026-01-17 19:50

## 目標

TDDアプローチでPythonプロジェクト構造を構築する。

## 完了タスク

- [x] `pyproject.toml` 作成（依存関係 + ツール設定）
- [x] `.python-version` 作成（3.10）
- [x] `uv sync` で依存関係インストール（128パッケージ）
- [x] テストインフラ構築（`tests/conftest.py`）
- [x] TDD: `test_config.py` → `config.py` 実装（8テスト）
- [x] TDD: `test_state.py` → `state.py` 実装（12テスト）
- [x] スタブファイル作成（nodes, tools, prompts）
- [x] 品質チェック実行（pytest, mypy, ruff）

---

## やり取りの記録

### 1. 計画フェーズ

ユーザーから `docs/plans/20260117-134549-initial-implementation-plan.md` の Phase 2 実装を依頼された。計画モードで詳細計画を作成し、`docs/plans/20260117-192226-phase2-python-project-setup.md` に保存。

### 2. プロジェクト初期化

- `pyproject.toml` 作成: langgraph, langchain-ollama, crawl4ai 等の依存関係を定義
- `.python-version` 作成: Python 3.10 を指定
- `uv sync` 実行: 128パッケージをインストール

### 3. TDD実装サイクル

#### config.py

1. `tests/test_config.py` を先に作成（RED）
2. `src/config.py` を実装（GREEN）
3. 8テスト全てPASS

#### state.py

1. `tests/test_state.py` を先に作成（RED）
2. `src/state.py` を実装（GREEN）
3. 12テスト全てPASS

### 4. 品質チェックと修正

品質チェック実行時に複数のエラーが発生し、修正を行った（詳細は後述）。

### 5. ユーザー確認

- 変更内容と確認方法を説明
- `ResearchState` の構造と `Annotated[..., operator.add]` の意味を解説
- テストの確認内容を説明

---

## TDD記録

### config.py

1. RED: `test_config.py` 作成 → ImportError
2. GREEN: `config.py` 実装（Settings dataclass）
3. 結果: 8テスト PASS

**テスト内容:**
- デフォルト値テスト（ollama_url, searxng_url, planner_model, worker_model）
- 環境変数読み込みテスト（OLLAMA_URL, SEARXNG_URL）
- バリデーションテスト（max_context_length, max_iterations が正の整数）

### state.py

1. RED: `test_state.py` 作成 → ImportError
2. GREEN: `state.py` 実装（ResearchState TypedDict）
3. 結果: 12テスト PASS

**テスト内容:**
- フィールド存在確認（7テスト）: task, plan, steps_completed, content, current_search_query, references, is_sufficient
- 型確認（3テスト）: task=str, is_sufficient=bool, steps_completed=int
- インスタンス生成確認（2テスト）: 空の状態、サンプルデータ入り状態

---

## 問題と解決策（詳細）

### 1. ForwardRef エラー

**発生箇所**: `tests/test_state.py` の型確認テスト

**エラー内容**:
```python
# テストコード
assert ResearchState.__annotations__["task"] == str

# 実行結果
AssertionError: assert ForwardRef('str') == str
```

**原因**:
`from __future__ import annotations` を使用すると、全てのアノテーションが文字列として遅延評価される。`__annotations__` は生の文字列（ForwardRef）を返すため、`str` 型との比較が失敗する。

**解決策**:
```python
# 修正前
assert ResearchState.__annotations__["task"] == str

# 修正後
import typing
hints = typing.get_type_hints(ResearchState)
assert hints["task"] is str
```

`typing.get_type_hints()` は ForwardRef を解決して実際の型オブジェクトを返す。

---

### 2. mypy 型注釈エラー

**発生箇所**: `src/graph.py`, `src/nodes/*.py`

**エラー内容**:
```
src/graph.py:6: error: Function is missing a return type annotation
src/nodes/planner.py:8: error: Missing type parameters for generic type "dict"
```

**原因**:
- スタブ関数に戻り値の型注釈がなかった
- `dict` にジェネリック型パラメータがなかった

**解決策**:
```python
# 修正前
def build_graph():
    ...

async def planner_node(state: dict) -> dict:
    ...

# 修正後
def build_graph() -> None:
    ...

async def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    ...
```

---

### 3. ruff E721 エラー

**発生箇所**: `tests/test_state.py` の3箇所（62行目, 71行目, 80行目）

**エラー内容**:
```
tests/test_state.py:62:16: E721 Use `is` and `is not` for type comparisons, or `isinstance()` for isinstance checks
tests/test_state.py:71:16: E721 Use `is` and `is not` for type comparisons, or `isinstance()` for isinstance checks
tests/test_state.py:80:16: E721 Use `is` and `is not` for type comparisons, or `isinstance()` for isinstance checks
```

**原因**:
型オブジェクトの比較に `==` を使用していた。Pythonでは型オブジェクトはシングルトンなので、`is` を使うべき。

**解決策**:
```python
# 修正前
assert hints["task"] == str
assert hints["is_sufficient"] == bool
assert hints["steps_completed"] == int

# 修正後
assert hints["task"] is str
assert hints["is_sufficient"] is bool
assert hints["steps_completed"] is int
```

---

## 品質チェック結果

```
pytest: 20 passed
coverage: 48% (config.py, state.py = 100%)
mypy: All checks passed
ruff check: All checks passed
ruff format: 23 files already formatted
```

---

## 作成ファイル一覧

```
pyproject.toml
.python-version
src/__init__.py
src/main.py
src/config.py
src/state.py
src/graph.py
src/nodes/__init__.py
src/nodes/planner.py
src/nodes/researcher.py
src/nodes/scraper.py
src/nodes/reviewer.py
src/nodes/writer.py
src/tools/__init__.py
src/tools/search.py
src/tools/scrape.py
src/prompts/__init__.py
src/prompts/templates.py
tests/__init__.py
tests/conftest.py
tests/test_config.py
tests/test_state.py
tests/nodes/__init__.py
tests/tools/__init__.py
tests/integration/__init__.py
```

---

## Git操作

```
コミット: 1083e55 Phase 2: Pythonプロジェクト構造を構築 (TDD)
プッシュ: 250b99a..1083e55 main -> main
```

---

## 次回への引き継ぎ

- Phase 3: ノード実装の開始
  - `planner.py` から実装
  - モックLLMを使用したTDDアプローチ
- `.gitignore` は既に coverage, mypy, ruff cache を含む
