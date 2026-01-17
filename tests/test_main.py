"""Tests for main CLI entry point."""

from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import AsyncMock, patch

from src.main import main


class TestDemoMode:
    """Tests for demo mode functionality."""

    def test_demo_search_prints_results(self) -> None:
        """Demo search should print search results."""
        mock_results = [
            AsyncMock(
                title="Result 1", url="https://example.com/1", snippet="Snippet 1"
            ),
            AsyncMock(
                title="Result 2", url="https://example.com/2", snippet="Snippet 2"
            ),
        ]

        with (
            patch.object(sys, "argv", ["main", "--demo", "search", "test query"]),
            patch("src.main.search", new_callable=AsyncMock) as mock_search,
            patch("sys.stdout", new=StringIO()) as mock_stdout,
        ):
            mock_search.return_value = mock_results
            main()
            output = mock_stdout.getvalue()

        assert "Result 1" in output
        assert "https://example.com/1" in output

    def test_demo_scrape_prints_markdown(self) -> None:
        """Demo scrape should print markdown content."""
        mock_result = AsyncMock(
            success=True,
            url="https://example.com",
            markdown="# Hello World\n\nThis is content.",
        )

        with (
            patch.object(
                sys, "argv", ["main", "--demo", "scrape", "https://example.com"]
            ),
            patch("src.main.scrape", new_callable=AsyncMock) as mock_scrape,
            patch("sys.stdout", new=StringIO()) as mock_stdout,
        ):
            mock_scrape.return_value = mock_result
            main()
            output = mock_stdout.getvalue()

        assert "https://example.com" in output
        assert "Hello World" in output

    def test_demo_scrape_prints_error_on_failure(self) -> None:
        """Demo scrape should print error message on failure."""
        mock_result = AsyncMock(
            success=False,
            url="https://example.com",
            markdown="",
            error_message="Connection failed",
        )

        with (
            patch.object(
                sys, "argv", ["main", "--demo", "scrape", "https://example.com"]
            ),
            patch("src.main.scrape", new_callable=AsyncMock) as mock_scrape,
            patch("sys.stdout", new=StringIO()) as mock_stdout,
        ):
            mock_scrape.return_value = mock_result
            main()
            output = mock_stdout.getvalue()

        assert "Failed" in output

    def test_demo_requires_input(self) -> None:
        """Demo mode should require input argument."""
        with (
            patch.object(sys, "argv", ["main", "--demo", "search"]),
            patch("sys.stdout", new=StringIO()) as mock_stdout,
            patch("sys.stderr", new=StringIO()),
        ):
            main()
            output = mock_stdout.getvalue()
            assert "Error" in output

    def test_demo_plan_prints_queries(self) -> None:
        """Demo plan should print generated search queries."""
        with (
            patch.object(sys, "argv", ["main", "--demo", "plan", "What is LangGraph?"]),
            patch("src.main.planner_node", new_callable=AsyncMock) as mock_planner,
            patch("sys.stdout", new=StringIO()) as mock_stdout,
        ):
            mock_planner.return_value = {
                "plan": ["LangGraph documentation", "LangGraph tutorial"]
            }
            main()
            output = mock_stdout.getvalue()

        assert "LangGraph documentation" in output
        assert "LangGraph tutorial" in output

    def test_demo_summarize_prints_summary(self) -> None:
        """Demo summarize should print LLM summary."""
        with (
            patch.object(
                sys, "argv", ["main", "--demo", "summarize", "Long text here"]
            ),
            patch("src.main.call_llm", new_callable=AsyncMock) as mock_llm,
            patch("sys.stdout", new=StringIO()) as mock_stdout,
        ):
            mock_llm.return_value = "This is a summary of the text."
            main()
            output = mock_stdout.getvalue()

        assert "This is a summary" in output
