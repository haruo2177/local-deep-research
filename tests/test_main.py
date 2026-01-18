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


class TestFullResearchMode:
    """Tests for full research execution mode."""

    def test_run_research_calls_graph(self) -> None:
        """Full research mode should call the graph with correct initial state."""
        from src.main import run_research

        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"report": "Research Report"}

        with patch("src.main.build_graph", return_value=mock_graph):
            import asyncio

            result = asyncio.run(run_research("Test topic"))

        mock_graph.ainvoke.assert_called_once()
        call_args = mock_graph.ainvoke.call_args[0][0]
        assert call_args["task"] == "Test topic"
        assert call_args["plan"] == []
        assert call_args["steps_completed"] == 0
        assert call_args["content"] == []
        assert call_args["references"] == []
        assert call_args["scraped_urls"] == []
        assert call_args["is_sufficient"] is False
        assert call_args["report"] == ""
        assert result == "Research Report"

    def test_main_without_demo_runs_research(self) -> None:
        """Running without --demo should execute full research mode."""
        with (
            patch.object(sys, "argv", ["main", "What is AI?"]),
            patch("src.main.run_research", new_callable=AsyncMock) as mock_run,
            patch("sys.stdout", new=StringIO()) as mock_stdout,
        ):
            mock_run.return_value = "# AI Research Report\n\nAI is..."
            main()
            output = mock_stdout.getvalue()

        mock_run.assert_called_once_with("What is AI?")
        assert "AI Research Report" in output

    def test_output_flag_saves_to_file(self) -> None:
        """--output flag should save report to file."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "report.md")

            with (
                patch.object(
                    sys, "argv", ["main", "--output", output_path, "Test topic"]
                ),
                patch("src.main.run_research", new_callable=AsyncMock) as mock_run,
                patch("sys.stdout", new=StringIO()),
            ):
                mock_run.return_value = "# Test Report\n\nContent here."
                main()

            # Verify file was written
            assert os.path.exists(output_path)
            with open(output_path, encoding="utf-8") as f:
                content = f.read()
            assert "# Test Report" in content
            assert "Content here." in content

    def test_run_research_returns_empty_on_no_report(self) -> None:
        """run_research should return empty string if no report in result."""
        from src.main import run_research

        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"task": "test"}

        with patch("src.main.build_graph", return_value=mock_graph):
            import asyncio

            result = asyncio.run(run_research("Test topic"))

        assert result == ""
