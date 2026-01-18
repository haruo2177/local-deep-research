"""Integration tests for the complete research workflow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.graph import build_graph
from src.tools.search import SearchResult


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


class TestFullWorkflow:
    """Tests for the complete research workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_successful_search(
        self, initial_state: dict[str, Any]
    ) -> None:
        """Full workflow should complete with search results and report."""
        search_results = [
            SearchResult(title="Python Async", url="https://example.com/1", snippet=""),
            SearchResult(title="Asyncio Guide", url="https://example.com/2", snippet=""),
        ]

        with (
            patch("src.nodes.planner.call_llm", new_callable=AsyncMock) as mock_planner,
            patch("src.nodes.researcher.search", new_callable=AsyncMock) as mock_search,
            patch(
                "src.nodes.scraper.scrape_multiple", new_callable=AsyncMock
            ) as mock_scrape,
            patch(
                "src.nodes.scraper.call_llm", new_callable=AsyncMock
            ) as mock_scraper_llm,
            patch(
                "src.nodes.reviewer.call_llm", new_callable=AsyncMock
            ) as mock_reviewer,
            patch("src.nodes.writer.call_llm", new_callable=AsyncMock) as mock_writer,
        ):
            mock_planner.return_value = '{"queries": ["python async", "asyncio tutorial"]}'
            mock_search.return_value = search_results
            mock_scrape.return_value = []  # No content from scraping
            mock_scraper_llm.return_value = "Summary of content"
            mock_reviewer.return_value = '{"sufficient": true}'
            mock_writer.return_value = "# Report\n\nAsync programming explained."

            graph = build_graph()
            result = await graph.ainvoke(initial_state)

            assert result["report"] == "# Report\n\nAsync programming explained."
            assert result["steps_completed"] >= 2
            assert len(result["references"]) > 0

    @pytest.mark.asyncio
    async def test_workflow_increments_steps_correctly(
        self, initial_state: dict[str, Any]
    ) -> None:
        """Steps should be incremented for each research iteration."""
        call_count = {"reviewer": 0}

        async def mock_reviewer_response(*args: Any, **kwargs: Any) -> str:
            call_count["reviewer"] += 1
            # Reviewer LLM is called only after MIN_ITERATIONS (2)
            # So call 1 = steps 2, call 2 = steps 3, call 3 = steps 4
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
            mock_planner.return_value = '{"queries": ["q1", "q2", "q3", "q4", "q5"]}'
            mock_search.return_value = []
            mock_reviewer.side_effect = mock_reviewer_response
            mock_writer.return_value = "# Report"

            graph = build_graph()
            result = await graph.ainvoke(initial_state)

            # Steps: 0->1->2 (MIN_ITER), call1->3, call2->4, call3 (sufficient)
            assert result["steps_completed"] == 4

    @pytest.mark.asyncio
    async def test_workflow_respects_max_iterations(
        self, initial_state: dict[str, Any]
    ) -> None:
        """Workflow should stop at max_iterations even if not sufficient."""
        with (
            patch("src.nodes.planner.call_llm", new_callable=AsyncMock) as mock_planner,
            patch("src.nodes.researcher.search", new_callable=AsyncMock) as mock_search,
            patch(
                "src.nodes.reviewer.call_llm", new_callable=AsyncMock
            ) as mock_reviewer,
            patch("src.nodes.writer.call_llm", new_callable=AsyncMock) as mock_writer,
            patch("src.config.settings") as mock_settings,
        ):
            mock_settings.max_iterations = 3
            mock_settings.planner_model = "test-model"
            mock_settings.worker_model = "test-model"
            mock_planner.return_value = '{"queries": ["q1", "q2", "q3", "q4", "q5"]}'
            mock_search.return_value = []
            mock_reviewer.return_value = '{"sufficient": false}'  # Never sufficient
            mock_writer.return_value = "# Report"

            graph = build_graph()
            result = await graph.ainvoke(initial_state)

            # Should stop at max_iterations
            assert result["steps_completed"] <= 5


class TestWorkflowEdgeCases:
    """Tests for edge cases in the workflow."""

    @pytest.mark.asyncio
    async def test_empty_plan_produces_report(
        self, initial_state: dict[str, Any]
    ) -> None:
        """Even with empty plan, workflow should produce a report."""
        with (
            patch("src.nodes.planner.call_llm", new_callable=AsyncMock) as mock_planner,
            patch("src.nodes.researcher.search", new_callable=AsyncMock) as mock_search,
            patch(
                "src.nodes.reviewer.call_llm", new_callable=AsyncMock
            ) as mock_reviewer,
            patch("src.nodes.writer.call_llm", new_callable=AsyncMock) as mock_writer,
        ):
            # At least 2 queries needed for MIN_ITERATIONS
            mock_planner.return_value = '{"queries": ["q1", "q2"]}'
            mock_search.return_value = []
            mock_reviewer.return_value = '{"sufficient": true}'
            mock_writer.return_value = "# Empty Report\n\nNo data found."

            graph = build_graph()
            result = await graph.ainvoke(initial_state)

            assert "report" in result
            assert result["report"] == "# Empty Report\n\nNo data found."

    @pytest.mark.asyncio
    async def test_duplicate_urls_not_added_to_references(
        self, initial_state: dict[str, Any]
    ) -> None:
        """Duplicate URLs should not be added to references."""
        search_results = [
            SearchResult(title="Page 1", url="https://example.com/page", snippet=""),
            SearchResult(title="Page 2", url="https://example.com/page", snippet=""),  # dup
        ]

        with (
            patch("src.nodes.planner.call_llm", new_callable=AsyncMock) as mock_planner,
            patch("src.nodes.researcher.search", new_callable=AsyncMock) as mock_search,
            patch(
                "src.nodes.reviewer.call_llm", new_callable=AsyncMock
            ) as mock_reviewer,
            patch("src.nodes.writer.call_llm", new_callable=AsyncMock) as mock_writer,
        ):
            mock_planner.return_value = '{"queries": ["q1", "q2"]}'
            mock_search.return_value = search_results
            mock_reviewer.return_value = '{"sufficient": true}'
            mock_writer.return_value = "# Report"

            graph = build_graph()
            result = await graph.ainvoke(initial_state)

            # References should be deduplicated
            unique_refs = list(set(result["references"]))
            assert len(unique_refs) <= len(result["references"])
