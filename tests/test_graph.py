"""Tests for graph.py - LangGraph workflow construction."""

from __future__ import annotations

from typing import Any

import pytest

from src.graph import build_graph
from src.nodes.reviewer import should_continue_research


class TestBuildGraph:
    """Tests for build_graph function."""

    def test_build_graph_returns_compiled_graph(self) -> None:
        """build_graph should return a compiled StateGraph."""
        graph = build_graph()
        assert graph is not None
        # Compiled graph should have invoke/ainvoke methods
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")

    def test_graph_has_all_nodes(self) -> None:
        """Graph should have all 7 nodes registered (including translators)."""
        graph = build_graph()
        # Get the underlying graph structure
        nodes = graph.get_graph().nodes
        node_names = set(nodes.keys())

        expected_nodes = {
            "planner",
            "translator_input",
            "researcher",
            "scraper",
            "reviewer",
            "writer",
            "translator_output",
        }
        # __start__ and __end__ are automatically added
        assert expected_nodes.issubset(node_names)

    def test_graph_has_translator_input_node(self) -> None:
        """Graph should have translator_input node."""
        graph = build_graph()
        nodes = graph.get_graph().nodes
        assert "translator_input" in nodes

    def test_graph_has_translator_output_node(self) -> None:
        """Graph should have translator_output node."""
        graph = build_graph()
        nodes = graph.get_graph().nodes
        assert "translator_output" in nodes

    def test_graph_has_start_and_end(self) -> None:
        """Graph should have START and END nodes."""
        graph = build_graph()
        nodes = graph.get_graph().nodes
        node_names = set(nodes.keys())

        assert "__start__" in node_names
        assert "__end__" in node_names


class TestGraphEdges:
    """Tests for graph edge definitions."""

    def test_start_to_planner_edge(self) -> None:
        """START should connect to planner."""
        graph = build_graph()
        edges = graph.get_graph().edges

        # Find edges from __start__
        start_edges = [e for e in edges if e[0] == "__start__"]
        assert len(start_edges) == 1
        assert start_edges[0][1] == "planner"

    def test_planner_to_translator_input_edge(self) -> None:
        """Planner should connect to translator_input."""
        graph = build_graph()
        edges = graph.get_graph().edges

        planner_edges = [e for e in edges if e[0] == "planner"]
        assert len(planner_edges) == 1
        assert planner_edges[0][1] == "translator_input"

    def test_translator_input_to_researcher_edge(self) -> None:
        """translator_input should connect to researcher."""
        graph = build_graph()
        edges = graph.get_graph().edges

        translator_input_edges = [e for e in edges if e[0] == "translator_input"]
        assert len(translator_input_edges) == 1
        assert translator_input_edges[0][1] == "researcher"

    def test_researcher_to_scraper_edge(self) -> None:
        """Researcher should connect to scraper."""
        graph = build_graph()
        edges = graph.get_graph().edges

        researcher_edges = [e for e in edges if e[0] == "researcher"]
        assert len(researcher_edges) == 1
        assert researcher_edges[0][1] == "scraper"

    def test_scraper_to_reviewer_edge(self) -> None:
        """Scraper should connect to reviewer."""
        graph = build_graph()
        edges = graph.get_graph().edges

        scraper_edges = [e for e in edges if e[0] == "scraper"]
        assert len(scraper_edges) == 1
        assert scraper_edges[0][1] == "reviewer"

    def test_reviewer_has_conditional_edges(self) -> None:
        """Reviewer should have conditional edges to researcher and writer."""
        graph = build_graph()
        edges = graph.get_graph().edges

        reviewer_edges = [e for e in edges if e[0] == "reviewer"]
        targets = {e[1] for e in reviewer_edges}

        assert "researcher" in targets
        assert "writer" in targets

    def test_writer_to_translator_output_edge(self) -> None:
        """Writer should connect to translator_output."""
        graph = build_graph()
        edges = graph.get_graph().edges

        writer_edges = [e for e in edges if e[0] == "writer"]
        assert len(writer_edges) == 1
        assert writer_edges[0][1] == "translator_output"

    def test_translator_output_to_end_edge(self) -> None:
        """translator_output should connect to END."""
        graph = build_graph()
        edges = graph.get_graph().edges

        translator_output_edges = [e for e in edges if e[0] == "translator_output"]
        assert len(translator_output_edges) == 1
        assert translator_output_edges[0][1] == "__end__"


class TestShouldContinueResearch:
    """Tests for should_continue_research conditional edge function."""

    def test_returns_writer_when_sufficient(self) -> None:
        """Should return 'writer' when is_sufficient is True."""
        state: dict[str, Any] = {"is_sufficient": True}
        result = should_continue_research(state)
        assert result == "writer"

    def test_returns_researcher_when_not_sufficient(self) -> None:
        """Should return 'researcher' when is_sufficient is False."""
        state: dict[str, Any] = {"is_sufficient": False}
        result = should_continue_research(state)
        assert result == "researcher"

    def test_returns_researcher_when_key_missing(self) -> None:
        """Should return 'researcher' when is_sufficient key is missing."""
        state: dict[str, Any] = {}
        result = should_continue_research(state)
        assert result == "researcher"


class TestGraphExecution:
    """Tests for graph execution flow with mocked nodes."""

    @pytest.mark.asyncio
    async def test_graph_executes_with_mocked_nodes(self) -> None:
        """Graph should execute through all nodes with mocks."""
        from langgraph.graph import END, START, StateGraph

        from src.state import ResearchState

        call_order: list[str] = []

        async def mock_planner(state: dict[str, Any]) -> dict[str, Any]:
            call_order.append("planner")
            return {"plan": ["query1"]}

        async def mock_researcher(state: dict[str, Any]) -> dict[str, Any]:
            call_order.append("researcher")
            return {
                "current_search_query": "query1",
                "references": ["http://example.com"],
                "steps_completed": 1,
            }

        async def mock_scraper(state: dict[str, Any]) -> dict[str, Any]:
            call_order.append("scraper")
            return {"content": ["Summary of example.com"], "scraped_urls": ["http://example.com"]}

        async def mock_reviewer(state: dict[str, Any]) -> dict[str, Any]:
            call_order.append("reviewer")
            return {"is_sufficient": True}

        async def mock_writer(state: dict[str, Any]) -> dict[str, Any]:
            call_order.append("writer")
            return {"report": "Final Report"}

        # Build test graph with mock nodes
        graph: StateGraph[ResearchState, Any, Any] = StateGraph(ResearchState)
        graph.add_node("planner", mock_planner)
        graph.add_node("researcher", mock_researcher)
        graph.add_node("scraper", mock_scraper)
        graph.add_node("reviewer", mock_reviewer)
        graph.add_node("writer", mock_writer)

        graph.add_edge(START, "planner")
        graph.add_edge("planner", "researcher")
        graph.add_edge("researcher", "scraper")
        graph.add_edge("scraper", "reviewer")
        graph.add_conditional_edges(
            "reviewer",
            should_continue_research,
            {"researcher": "researcher", "writer": "writer"},
        )
        graph.add_edge("writer", END)

        compiled = graph.compile()

        initial_state = {
            "task": "Test research task",
            "plan": [],
            "steps_completed": 0,
            "content": [],
            "current_search_query": "",
            "references": [],
            "scraped_urls": [],
            "is_sufficient": False,
            "report": "",
        }

        result = await compiled.ainvoke(initial_state)

        # All nodes should have been called in order
        assert call_order == ["planner", "researcher", "scraper", "reviewer", "writer"]

        # Final result should contain report
        assert "report" in result
        assert result["report"] == "Final Report"

    @pytest.mark.asyncio
    async def test_graph_loops_when_not_sufficient(self) -> None:
        """Graph should loop back to researcher when info is not sufficient."""
        from langgraph.graph import END, START, StateGraph

        from src.state import ResearchState

        call_count = {"reviewer": 0, "researcher": 0}

        async def mock_planner(state: dict[str, Any]) -> dict[str, Any]:
            return {"plan": ["query1", "query2"]}

        async def mock_researcher(state: dict[str, Any]) -> dict[str, Any]:
            call_count["researcher"] += 1
            steps = state.get("steps_completed", 0)
            return {
                "current_search_query": f"query{steps + 1}",
                "references": [f"http://example{steps + 1}.com"],
                "steps_completed": steps + 1,
            }

        async def mock_scraper(state: dict[str, Any]) -> dict[str, Any]:
            refs = state.get("references", [])
            scraped = state.get("scraped_urls", [])
            new_urls = [url for url in refs if url not in scraped]
            return {"content": ["Summary"], "scraped_urls": new_urls}

        async def mock_reviewer(state: dict[str, Any]) -> dict[str, Any]:
            call_count["reviewer"] += 1
            # First call: not sufficient, second call: sufficient
            return {"is_sufficient": call_count["reviewer"] >= 2}

        async def mock_writer(state: dict[str, Any]) -> dict[str, Any]:
            return {"report": "Final Report"}

        # Build test graph with mock nodes
        graph: StateGraph[ResearchState, Any, Any] = StateGraph(ResearchState)
        graph.add_node("planner", mock_planner)
        graph.add_node("researcher", mock_researcher)
        graph.add_node("scraper", mock_scraper)
        graph.add_node("reviewer", mock_reviewer)
        graph.add_node("writer", mock_writer)

        graph.add_edge(START, "planner")
        graph.add_edge("planner", "researcher")
        graph.add_edge("researcher", "scraper")
        graph.add_edge("scraper", "reviewer")
        graph.add_conditional_edges(
            "reviewer",
            should_continue_research,
            {"researcher": "researcher", "writer": "writer"},
        )
        graph.add_edge("writer", END)

        compiled = graph.compile()

        initial_state = {
            "task": "Test research task",
            "plan": [],
            "steps_completed": 0,
            "content": [],
            "current_search_query": "",
            "references": [],
            "scraped_urls": [],
            "is_sufficient": False,
            "report": "",
        }

        result = await compiled.ainvoke(initial_state)

        # Researcher should be called at least twice (initial + loop)
        assert call_count["researcher"] >= 2
        # Reviewer should be called at least twice
        assert call_count["reviewer"] >= 2
        # Result should contain report
        assert "report" in result
