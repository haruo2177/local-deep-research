"""Tests for main CLI entry point."""

from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import AsyncMock, patch

import pytest

from src.config import settings
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
        assert call_args["empty_cycles"] == 0
        assert call_args["empty_cycle_streak"] == 0
        assert call_args["source_language"] == ""
        assert call_args["original_task"] == ""
        assert result == "Research Report"

    def test_main_without_demo_runs_research(self) -> None:
        """Running without --demo should execute full research mode."""
        with (
            patch.object(sys, "argv", ["main", "What is AI?"]),
            patch("src.main.start_required_services") as mock_start,
            patch(
                "src.main.validate_runtime_dependencies", new_callable=AsyncMock
            ) as mock_validate,
            patch("src.main.run_research", new_callable=AsyncMock) as mock_run,
            patch("src.main.stop_required_services") as mock_stop,
            patch("sys.stdout", new=StringIO()) as mock_stdout,
        ):
            mock_run.return_value = "# AI Research Report\n\nAI is..."
            main()
            output = mock_stdout.getvalue()

        mock_start.assert_called_once()
        mock_validate.assert_called_once()
        mock_run.assert_called_once_with("What is AI?")
        mock_stop.assert_called_once()
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
                patch("src.main.start_required_services") as mock_start,
                patch(
                    "src.main.validate_runtime_dependencies", new_callable=AsyncMock
                ) as mock_validate,
                patch("src.main.run_research", new_callable=AsyncMock) as mock_run,
                patch("src.main.stop_required_services") as mock_stop,
                patch("sys.stdout", new=StringIO()),
            ):
                mock_run.return_value = "# Test Report\n\nContent here."
                main()

            mock_start.assert_called_once()
            mock_validate.assert_called_once()
            mock_stop.assert_called_once()
            # Verify file was written
            assert os.path.exists(output_path)
            with open(output_path, encoding="utf-8") as f:
                content = f.read()
            assert "# Test Report" in content
            assert "Content here." in content

    def test_main_prints_dependency_error_and_skips_research(self) -> None:
        """Main should print actionable dependency error and exit early."""
        from src.main import DependencyError

        with (
            patch.object(sys, "argv", ["main", "What is AI?"]),
            patch("src.main.start_required_services") as mock_start,
            patch(
                "src.main.validate_runtime_dependencies", new_callable=AsyncMock
            ) as mock_validate,
            patch("src.main.run_research", new_callable=AsyncMock) as mock_run,
            patch("src.main.stop_required_services") as mock_stop,
            patch("sys.stdout", new=StringIO()) as mock_stdout,
        ):
            mock_validate.side_effect = DependencyError(
                "Ollama connection error at http://localhost:11434/api/tags."
            )
            main()
            output = mock_stdout.getvalue()

        mock_start.assert_called_once()
        mock_validate.assert_called_once()
        mock_run.assert_not_called()
        mock_stop.assert_called_once()
        assert "Error:" in output
        assert "Ollama connection error" in output

    def test_main_skips_stop_when_start_fails(self) -> None:
        """Stop should be skipped when service start fails."""
        from src.main import DependencyError

        with (
            patch.object(sys, "argv", ["main", "What is AI?"]),
            patch("src.main.start_required_services") as mock_start,
            patch(
                "src.main.validate_runtime_dependencies", new_callable=AsyncMock
            ) as mock_validate,
            patch("src.main.run_research", new_callable=AsyncMock) as mock_run,
            patch("src.main.stop_required_services") as mock_stop,
            patch("sys.stdout", new=StringIO()),
        ):
            mock_start.side_effect = DependencyError("docker compose failed")
            main()

        mock_start.assert_called_once()
        mock_validate.assert_not_called()
        mock_run.assert_not_called()
        mock_stop.assert_not_called()

    def test_run_research_returns_empty_on_no_report(self) -> None:
        """run_research should return empty string if no report in result."""
        from src.main import run_research

        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"task": "test"}

        with patch("src.main.build_graph", return_value=mock_graph):
            import asyncio

            result = asyncio.run(run_research("Test topic"))

        assert result == ""


class TestServiceStartupFallback:
    """Tests for docker compose startup fallback behavior."""

    def test_start_required_services_falls_back_to_cpu_when_nvidia_unavailable(
        self,
    ) -> None:
        """Startup should retry with CPU config when NVIDIA runtime is unavailable."""
        from src.main import DependencyError, start_required_services

        nvidia_error = (
            'Failed to run `docker compose up -d ollama searxng`: '
            'could not select device driver "nvidia" with capabilities: [[gpu]]'
        )
        with patch("src.main._run_compose") as mock_run:
            mock_run.side_effect = [DependencyError(nvidia_error), None]
            start_required_services()

        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0].args[0] == [
            "-f",
            "docker-compose.yaml",
            "-f",
            "docker-compose.gpu.yaml",
            "up",
            "-d",
            "ollama",
            "searxng",
        ]
        assert mock_run.call_args_list[1].args[0] == [
            "-f",
            "docker-compose.yaml",
            "up",
            "-d",
            "ollama",
            "searxng",
        ]

    def test_start_required_services_raises_non_nvidia_errors(self) -> None:
        """Startup should not swallow compose errors unrelated to NVIDIA runtime."""
        from src.main import DependencyError, start_required_services

        with patch("src.main._run_compose") as mock_run:
            mock_run.side_effect = DependencyError("docker compose failed")
            with pytest.raises(DependencyError, match="docker compose failed"):
                start_required_services()

        assert mock_run.call_count == 1


class TestOllamaModelAvailability:
    """Tests for required Ollama model checks."""

    def test_required_ollama_models_unique_in_stable_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Required model list should preserve order and remove duplicates."""
        from src.main import _required_ollama_models

        monkeypatch.setattr(settings, "planner_model", "planner:1")
        monkeypatch.setattr(settings, "worker_model", "worker:1")
        monkeypatch.setattr(settings, "_writer_model", "planner:1")

        assert _required_ollama_models() == ["planner:1", "worker:1"]

    async def test_check_required_ollama_models_raises_with_pull_commands(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing models should raise DependencyError with pull commands."""
        from src.main import DependencyError, _check_required_ollama_models

        monkeypatch.setattr(settings, "planner_model", "planner:1")
        monkeypatch.setattr(settings, "worker_model", "worker:1")
        monkeypatch.setattr(settings, "_writer_model", "writer:1")

        with patch("src.main._fetch_ollama_model_names", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"worker:1"}
            with pytest.raises(DependencyError) as exc_info:
                await _check_required_ollama_models(ollama_base="http://localhost:11434")

        message = str(exc_info.value)
        assert "Missing Ollama models: planner:1, writer:1." in message
        assert "Copy and run this command, then retry:" in message
        assert (
            "docker compose -f docker-compose.yaml up -d ollama && "
            "docker exec ollama ollama pull planner:1 && "
            "docker exec ollama ollama pull writer:1"
        ) in message

    async def test_check_required_ollama_models_passes_when_all_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Model check should pass when all required models are available."""
        from src.main import _check_required_ollama_models

        monkeypatch.setattr(settings, "planner_model", "planner:1")
        monkeypatch.setattr(settings, "worker_model", "worker:1")
        monkeypatch.setattr(settings, "_writer_model", "writer:1")

        with patch("src.main._fetch_ollama_model_names", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"planner:1", "worker:1", "writer:1"}
            await _check_required_ollama_models(ollama_base="http://localhost:11434")


class TestServiceHealthRetries:
    """Tests for service health-check retry behavior."""

    async def test_check_service_with_retries_succeeds_after_transient_failure(
        self,
    ) -> None:
        """Retry helper should succeed when a later attempt passes."""
        from src.main import DependencyError, _check_service_with_retries

        with (
            patch("src.main._check_service", new_callable=AsyncMock) as mock_check,
            patch("src.main.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_check.side_effect = [DependencyError("temporary"), None]
            await _check_service_with_retries(
                service_name="SearXNG",
                url="http://localhost:8080/healthz",
                hint="hint",
                retries=3,
                retry_delay=0.01,
            )

        assert mock_check.await_count == 2
        mock_sleep.assert_awaited_once_with(0.01)

    async def test_check_service_with_retries_raises_after_max_retries(self) -> None:
        """Retry helper should raise the final DependencyError after max retries."""
        from src.main import DependencyError, _check_service_with_retries

        with (
            patch("src.main._check_service", new_callable=AsyncMock) as mock_check,
            patch("src.main.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_check.side_effect = [
                DependencyError("fail-1"),
                DependencyError("fail-2"),
                DependencyError("fail-3"),
            ]
            with pytest.raises(DependencyError, match="fail-3"):
                await _check_service_with_retries(
                    service_name="SearXNG",
                    url="http://localhost:8080/healthz",
                    hint="hint",
                    retries=3,
                    retry_delay=0.01,
                )

        assert mock_check.await_count == 3
        assert mock_sleep.await_count == 2
