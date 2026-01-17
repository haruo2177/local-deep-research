# Pythonプロジェクト構造の構築 (Phase 2)

**作成日**: 2026-01-17
**対象**: 実装計画 Phase 2

---

## 概要

TDDアプローチでPythonプロジェクト構造を構築する。uvをパッケージマネージャーとして使用。

## 作成ファイル構造

```
local-deep-research/
├── pyproject.toml
├── .python-version
├── src/
│   ├── __init__.py
│   ├── main.py           # エントリーポイント（スタブ）
│   ├── config.py         # 設定管理（TDD実装）
│   ├── state.py          # 状態定義（TDD実装）
│   ├── graph.py          # スタブ
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── planner.py    # スタブ
│   │   ├── researcher.py # スタブ
│   │   ├── scraper.py    # スタブ
│   │   ├── reviewer.py   # スタブ
│   │   └── writer.py     # スタブ
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── search.py     # スタブ
│   │   └── scrape.py     # スタブ
│   └── prompts/
│       ├── __init__.py
│       └── templates.py  # スタブ
└── tests/
    ├── __init__.py
    ├── conftest.py       # 共通fixture
    ├── test_config.py    # config.pyのテスト
    ├── test_state.py     # state.pyのテスト
    ├── nodes/
    │   └── __init__.py
    ├── tools/
    │   └── __init__.py
    └── integration/
        └── __init__.py
```

---

## 実装手順

### Step 1: プロジェクト初期化

1. `pyproject.toml` 作成（依存関係 + ツール設定）
2. `.python-version` 作成（`3.10`）
3. `uv sync` で依存関係インストール

### Step 2: テストインフラ構築

1. `tests/__init__.py` 作成
2. `tests/conftest.py` 作成（共通fixture）
3. `src/__init__.py` 作成
4. `uv run pytest` で動作確認

### Step 3: config.py のTDD実装

1. `tests/test_config.py` 作成（失敗するテスト）
2. `uv run pytest tests/test_config.py` → RED
3. `src/config.py` 実装
4. `uv run pytest tests/test_config.py` → GREEN

### Step 4: state.py のTDD実装

1. `tests/test_state.py` 作成（失敗するテスト）
2. `uv run pytest tests/test_state.py` → RED
3. `src/state.py` 実装
4. `uv run pytest tests/test_state.py` → GREEN

### Step 5: スタブファイル作成

残りのファイルをスタブとして作成（Phase 3以降で実装）

### Step 6: 品質チェック

```bash
uv run pytest --cov=src
uv run mypy src/
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

---

## 主要ファイル内容

### pyproject.toml

```toml
[project]
name = "local-deep-research"
version = "0.1.0"
description = "A local Deep Research system using LangGraph, Ollama, and SearXNG"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"

dependencies = [
    "langgraph>=0.6.0",
    "langchain-ollama>=0.2.0",
    "langchain-core>=0.3.0",
    "crawl4ai>=0.4.0",
    "aiohttp>=3.9.0",
    "pydantic>=2.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.23.0",
    "mypy>=1.8.0",
    "ruff>=0.4.0",
    "aioresponses>=0.7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

[tool.mypy]
python_version = "3.10"
strict = true
ignore_missing_imports = true
exclude = ["tests/", ".venv/"]

[tool.ruff]
target-version = "py310"
line-length = 88
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "ASYNC"]
ignore = ["E501"]

[tool.coverage.run]
source = ["src"]
branch = true
```

### conftest.py（主要fixture）

- `mock_config`: テスト用設定辞書
- `empty_research_state`: 空の研究状態
- `sample_research_state`: サンプルデータ入り状態
- `mock_llm`: モックLLMクライアント
- `sample_search_results`: 検索結果サンプル

### src/config.py

```python
@dataclass
class Settings:
    ollama_url: str = "http://localhost:11434"
    searxng_url: str = "http://localhost:8080"
    planner_model: str = "deepseek-r1:7b"
    worker_model: str = "qwen2.5:3b"
    max_context_length: int = 4096
    max_iterations: int = 5
```

### src/state.py

```python
class ResearchState(TypedDict):
    task: str
    plan: list[str]
    steps_completed: int
    content: Annotated[list[str], operator.add]
    current_search_query: str
    references: Annotated[list[str], operator.add]
    is_sufficient: bool
```

---

## 検証コマンド

```bash
# 依存関係インストール
uv sync

# テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=src --cov-report=term

# 型チェック
uv run mypy src/

# リンター
uv run ruff check src/ tests/

# フォーマットチェック
uv run ruff format --check src/ tests/

# 全品質チェック（一括）
uv run pytest && uv run mypy src/ && uv run ruff check src/ tests/
```

---

## 変更対象ファイル

| ファイル | 操作 |
|---------|------|
| `pyproject.toml` | 新規作成 |
| `.python-version` | 新規作成 |
| `src/**/*.py` | 新規作成（14ファイル） |
| `tests/**/*.py` | 新規作成（8ファイル） |
| `.gitignore` | 追記（coverage, mypy, ruff） |

---

## 検証チェックリスト

- [ ] `uv sync` が正常完了
- [ ] `uv run pytest` が実行可能
- [ ] `uv run mypy src/` がエラーなし
- [ ] `uv run ruff check src/ tests/` がエラーなし
- [ ] `tests/test_config.py` が全てPASS
- [ ] `tests/test_state.py` が全てPASS

### 確認日時
- YYYY-MM-DD HH:mm: [PASS/FAIL]
