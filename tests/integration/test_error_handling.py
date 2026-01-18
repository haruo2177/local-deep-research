"""Integration tests for error handling across the system."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.graph import build_graph
from src.llm import LLMError
from src.nodes.planner import PlannerError
from src.nodes.writer import WriterError
from src.tools.search import SearchError


@pytest.fixture
def initial_state() -> dict[str, Any]:
    """Return a valid initial state for the graph."""
    return {
        "task": "Test research topic",
        "plan": [],
        "steps_completed": 0,
        "content": [],
        "current_search_query": "",
        "references": [],
        "is_sufficient": False,
        "report": "",
        "scraped_urls": [],
    }


class TestPlannerErrorPropagation:
    """Tests for error propagation from planner node."""

    @pytest.mark.asyncio
    async def test_planner_error_propagates(self, initial_state: dict[str, Any]) -> None:
        """Planner errors should propagate up the call stack."""
        with patch("src.nodes.planner.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("LLM connection failed")

            graph = build_graph()

            with pytest.raises(PlannerError) as exc_info:
                await graph.ainvoke(initial_state)

            assert "LLM call failed" in str(exc_info.value)


class TestSearchErrorHandling:
    """Tests for search error handling in researcher node."""

    @pytest.mark.asyncio
    async def test_search_error_handled_gracefully(
        self, initial_state: dict[str, Any]
    ) -> None:
        """Search errors should be handled and allow graph to continue."""
        with (
            patch("src.nodes.planner.call_llm", new_callable=AsyncMock) as mock_planner,
            patch("src.nodes.researcher.search", new_callable=AsyncMock) as mock_search,
            patch(
                "src.nodes.reviewer.call_llm", new_callable=AsyncMock
            ) as mock_reviewer,
            patch("src.nodes.writer.call_llm", new_callable=AsyncMock) as mock_writer,
        ):
            mock_planner.return_value = '{"queries": ["test query 1", "test query 2"]}'
            mock_search.side_effect = SearchError("Connection failed")
            mock_reviewer.return_value = '{"sufficient": true}'
            mock_writer.return_value = "# Report\n\nSearch failed."

            graph = build_graph()
            result = await graph.ainvoke(initial_state)

            # Researcher handles error and continues (empty URLs)
            assert "task" in result
            assert "report" in result


class TestWriterErrorPropagation:
    """Tests for error propagation from writer node."""

    @pytest.mark.asyncio
    async def test_writer_error_propagates(self, initial_state: dict[str, Any]) -> None:
        """Writer errors should propagate up the call stack."""
        with (
            patch("src.nodes.planner.call_llm", new_callable=AsyncMock) as mock_planner,
            patch("src.nodes.researcher.search", new_callable=AsyncMock) as mock_search,
            patch(
                "src.nodes.reviewer.call_llm", new_callable=AsyncMock
            ) as mock_reviewer,
            patch("src.nodes.writer.call_llm", new_callable=AsyncMock) as mock_writer,
        ):
            # Need at least MIN_ITERATIONS (2) queries in the plan
            mock_planner.return_value = '{"queries": ["test1", "test2"]}'
            mock_search.return_value = []
            mock_reviewer.return_value = '{"sufficient": true}'
            mock_writer.side_effect = LLMError("Writer LLM failed")

            graph = build_graph()

            with pytest.raises(WriterError) as exc_info:
                await graph.ainvoke(initial_state)

            assert "LLM call failed" in str(exc_info.value)


class TestGraphResilience:
    """Tests for graph resilience to transient errors."""

    @pytest.mark.asyncio
    async def test_graph_completes_with_empty_search_results(
        self, initial_state: dict[str, Any]
    ) -> None:
        """Graph should complete even when search returns no results."""
        with (
            patch("src.nodes.planner.call_llm", new_callable=AsyncMock) as mock_planner,
            patch("src.nodes.researcher.search", new_callable=AsyncMock) as mock_search,
            patch(
                "src.nodes.reviewer.call_llm", new_callable=AsyncMock
            ) as mock_reviewer,
            patch("src.nodes.writer.call_llm", new_callable=AsyncMock) as mock_writer,
        ):
            # Need at least MIN_ITERATIONS (2) queries
            mock_planner.return_value = '{"queries": ["test query 1", "test query 2"]}'
            mock_search.return_value = []  # Empty search results
            mock_reviewer.return_value = '{"sufficient": true}'
            mock_writer.return_value = "# Final Report\n\nNo information found."

            graph = build_graph()
            result = await graph.ainvoke(initial_state)

            assert "report" in result
            assert result["report"] == "# Final Report\n\nNo information found."

    @pytest.mark.asyncio
    async def test_graph_handles_multiple_iterations(
        self, initial_state: dict[str, Any]
    ) -> None:
        """Graph should handle multiple research iterations correctly."""
        call_count = {"reviewer": 0}

        async def mock_reviewer_response(*args: Any, **kwargs: Any) -> str:
            call_count["reviewer"] += 1
            # First 2 calls: not sufficient, then sufficient
            if call_count["reviewer"] < 3:
                return '{"sufficient": false}'
            return '{"sufficient": true}'

        with (
            patch("src.nodes.planner.call_llm", new_callable=AsyncMock) as mock_planner,
            patch("src.nodes.researcher.search", new_callable=AsyncMock) as mock_search,
            patch(
                "src.nodes.reviewer.call_llm", new_callable=AsyncMock
            ) as mock_reviewer,
            patch("src.nodes.writer.call_llm", new_callable=AsyncMock) as mock_writer,
        ):
            mock_planner.return_value = '{"queries": ["q1", "q2", "q3", "q4"]}'
            mock_search.return_value = []
            mock_reviewer.side_effect = mock_reviewer_response
            mock_writer.return_value = "# Report after iterations"

            graph = build_graph()
            result = await graph.ainvoke(initial_state)

            assert result["steps_completed"] >= 3  # At least 3 iterations
            assert "report" in result
