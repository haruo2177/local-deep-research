"""Tests for the Researcher node."""

from __future__ import annotations

from unittest.mock import patch

from src.tools.search import SearchResult


class TestResearcherNode:
    """Tests for the researcher_node function."""

    async def test_researcher_executes_current_query(self) -> None:
        """researcher_node should execute the current query from plan."""
        from src.nodes.researcher import researcher_node

        with patch("src.nodes.researcher.search") as mock_search:
            mock_search.return_value = [
                SearchResult(title="Result 1", url="https://example.com/1", snippet="")
            ]
            state = {
                "plan": ["query 1", "query 2", "query 3"],
                "steps_completed": 0,
                "references": [],
            }

            await researcher_node(state)

            mock_search.assert_called_once()
            call_args = mock_search.call_args[0]
            assert call_args[0] == "query 1"

    async def test_researcher_extracts_urls(self) -> None:
        """researcher_node should extract URLs from search results."""
        from src.nodes.researcher import researcher_node

        with patch("src.nodes.researcher.search") as mock_search:
            mock_search.return_value = [
                SearchResult(title="Result 1", url="https://example.com/1", snippet=""),
                SearchResult(title="Result 2", url="https://example.com/2", snippet=""),
            ]
            state = {
                "plan": ["test query"],
                "steps_completed": 0,
                "references": [],
            }

            result = await researcher_node(state)

            assert "references" in result
            assert "https://example.com/1" in result["references"]
            assert "https://example.com/2" in result["references"]

    async def test_researcher_limits_results(self) -> None:
        """researcher_node should limit results to top 5."""
        from src.nodes.researcher import researcher_node

        with patch("src.nodes.researcher.search") as mock_search:
            mock_search.return_value = [
                SearchResult(
                    title=f"Result {i}", url=f"https://example.com/{i}", snippet=""
                )
                for i in range(10)
            ]
            state = {
                "plan": ["test query"],
                "steps_completed": 0,
                "references": [],
            }

            result = await researcher_node(state)

            assert len(result["references"]) == 5

    async def test_researcher_increments_steps(self) -> None:
        """researcher_node should increment steps_completed by 1."""
        from src.nodes.researcher import researcher_node

        with patch("src.nodes.researcher.search") as mock_search:
            mock_search.return_value = []
            state = {
                "plan": ["query 1", "query 2"],
                "steps_completed": 0,
                "references": [],
            }

            result = await researcher_node(state)

            assert result["steps_completed"] == 1

    async def test_researcher_handles_empty_results(self) -> None:
        """researcher_node should continue with empty results."""
        from src.nodes.researcher import researcher_node

        with patch("src.nodes.researcher.search") as mock_search:
            mock_search.return_value = []
            state = {
                "plan": ["test query"],
                "steps_completed": 0,
                "references": [],
            }

            result = await researcher_node(state)

            assert result["references"] == []
            assert result["steps_completed"] == 1

    async def test_researcher_handles_search_error(self) -> None:
        """researcher_node should handle SearchError gracefully."""
        from src.nodes.researcher import researcher_node
        from src.tools.search import SearchError

        with patch("src.nodes.researcher.search") as mock_search:
            mock_search.side_effect = SearchError("Search failed")
            state = {
                "plan": ["test query"],
                "steps_completed": 0,
                "references": [],
            }

            result = await researcher_node(state)

            assert result["references"] == []
            assert result["steps_completed"] == 1

    async def test_researcher_skips_duplicate_urls(self) -> None:
        """researcher_node should skip duplicate URLs."""
        from src.nodes.researcher import researcher_node

        with patch("src.nodes.researcher.search") as mock_search:
            mock_search.return_value = [
                SearchResult(title="Result 1", url="https://example.com/1", snippet=""),
                SearchResult(title="Result 2", url="https://example.com/1", snippet=""),
                SearchResult(title="Result 3", url="https://example.com/2", snippet=""),
            ]
            state = {
                "plan": ["test query"],
                "steps_completed": 0,
                "references": ["https://example.com/1"],
            }

            result = await researcher_node(state)

            url_count = result["references"].count("https://example.com/1")
            assert url_count == 0
            assert "https://example.com/2" in result["references"]

    async def test_researcher_returns_current_search_query(self) -> None:
        """researcher_node should return the current search query."""
        from src.nodes.researcher import researcher_node

        with patch("src.nodes.researcher.search") as mock_search:
            mock_search.return_value = []
            state = {
                "plan": ["first query", "second query"],
                "steps_completed": 1,
                "references": [],
            }

            result = await researcher_node(state)

            assert result["current_search_query"] == "second query"
