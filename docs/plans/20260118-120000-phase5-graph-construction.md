# フェーズ5: グラフ構築と統合 - 実装計画

## 概要

すべてのノード（Planner → Researcher → Scraper → Reviewer → Writer）を接続し、完全な研究パイプラインを構築する。

## 変更対象ファイル

| ファイル | アクション | 説明 |
|---------|-----------|------|
| [tests/test_graph.py](../../tests/test_graph.py) | 新規作成 | グラフ構造のTDDテスト |
| [src/graph.py](../../src/graph.py) | 修正 | StateGraphとエッジの実装 |
| [tests/test_main.py](../../tests/test_main.py) | 修正 | フル実行モードのテスト追加 |
| [src/main.py](../../src/main.py) | 修正 | フル研究実行モードの実装 |

## 実装手順（TDDアプローチ）

### ステップ1: グラフ構造テストの作成

`tests/test_graph.py` に以下のテストケースを作成:

1. **グラフ構築テスト**
   - `test_build_graph_returns_compiled_graph` - `build_graph()` がコンパイル済みStateGraphを返すことを確認
   - `test_graph_has_all_nodes` - 5つのノード全て（planner, researcher, scraper, reviewer, writer）が登録されていることを確認
   - `test_graph_has_start_edge` - START → planner エッジが存在することを確認

2. **エッジ定義テスト**
   - `test_planner_to_researcher_edge` - planner → researcher エッジの確認
   - `test_researcher_to_scraper_edge` - researcher → scraper エッジの確認
   - `test_scraper_to_reviewer_edge` - scraper → reviewer エッジの確認
   - `test_reviewer_conditional_edge` - reviewer からの条件付きルーティングの確認

3. **条件付きルーティングテスト**
   - `test_should_continue_research_returns_writer_when_sufficient` - `is_sufficient=True` 時のルーティング
   - `test_should_continue_research_returns_researcher_when_not_sufficient` - `is_sufficient=False` 時のルーティング

### ステップ2: `src/graph.py` の実装

```python
from langgraph.graph import END, START, StateGraph

from src.nodes.planner import planner_node
from src.nodes.researcher import researcher_node
from src.nodes.reviewer import reviewer_node, should_continue_research
from src.nodes.scraper import scraper_node
from src.nodes.writer import writer_node
from src.state import ResearchState


def build_graph() -> StateGraph:
    """研究ワークフローグラフを構築して返す。"""
    graph = StateGraph(ResearchState)

    # ノードの追加
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("scraper", scraper_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("writer", writer_node)

    # エッジの追加
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "scraper")
    graph.add_edge("scraper", "reviewer")

    # Reviewerからの条件付きエッジ
    graph.add_conditional_edges(
        "reviewer",
        should_continue_research,
        {"researcher": "researcher", "writer": "writer"},
    )

    graph.add_edge("writer", END)

    return graph.compile()
```

### ステップ3: モックノードを使用した統合テスト

`tests/test_graph.py` にエンドツーエンドフローのテストを追加:

- `test_graph_executes_full_flow_with_sufficient_info` - Reviewerが1回目の反復後に情報十分と判定する完全フロー
- `test_graph_loops_when_info_not_sufficient` - 完了前にResearcherへループバックするフロー

### ステップ4: `main.py` のフル実行モード更新

`run_research()` 関数とCLI引数処理を追加:

```python
async def run_research(task: str) -> str:
    """研究パイプライン全体を実行する。"""
    from src.graph import build_graph

    graph = build_graph()

    initial_state = {
        "task": task,
        "plan": [],
        "steps_completed": 0,
        "content": [],
        "current_search_query": "",
        "references": [],
        "is_sufficient": False,
    }

    result = await graph.ainvoke(initial_state)
    return result.get("report", "")
```

CLI対応:
- `uv run python -m src.main "リサーチトピック"` - フル研究モード
- `uv run python -m src.main --output report.md "リサーチトピック"` - ファイル出力

### ステップ5: main.py のテスト追加

`tests/test_main.py` を更新:
- `test_run_research_calls_graph` - グラフが正しい初期状態で呼び出されることを確認
- `test_main_without_demo_runs_research` - フル実行パスのテスト
- `test_output_flag_saves_to_file` - ファイル出力機能のテスト

## グラフワークフロー図

```
START
  │
  ▼
┌─────────┐
│ Planner │  タスクから検索クエリを生成
└────┬────┘
     │
     ▼
┌──────────┐
│Researcher│◄────────────────┐
└────┬─────┘                 │
     │                       │
     ▼                       │
┌─────────┐                  │
│ Scraper │  URLを取得し     │
└────┬────┘  要約            │
     │                       │
     ▼                       │
┌─────────┐                  │
│Reviewer │──► 情報不十分 ───┘
└────┬────┘
     │ 情報十分
     ▼
┌────────┐
│ Writer │  最終レポート生成
└────┬───┘
     │
     ▼
    END
```

## 検証手順

1. **全テストの実行**
   ```bash
   uv run pytest tests/test_graph.py -v
   uv run pytest --cov=src --cov-report=term-missing
   ```

2. **型チェック**
   ```bash
   uv run mypy src/graph.py
   ```

3. **手動エンドツーエンドテスト**
   ```bash
   # Dockerサービスが起動していることを確認
   docker compose up -d

   # フル研究の実行
   uv run python -m src.main "LangGraphとは何か、どのように動作するか"
   ```

## 依存関係

すべての依存関係はインストール済み:
- `langgraph>=0.6.0` (StateGraph用)
- 全ノード実装・テスト済み（116テストパス）
- `should_continue_research` 関数は既に `reviewer.py:41-52` に実装済み

## 備考

- TDDに従う: まずテストを書き、その後実装
- 外部依存を避けるため、単体テストではモックLLMレスポンスを使用
- `should_continue_research` 条件付きエッジ関数は既に `reviewer.py` に実装されている
