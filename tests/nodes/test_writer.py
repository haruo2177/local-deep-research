"""Tests for the Writer node."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestWriterNode:
    """Tests for the writer_node function."""

    async def test_writer_returns_report(self) -> None:
        """writer_node should return a dict with report as string."""
        from src.nodes.writer import writer_node

        with patch("src.nodes.writer.call_llm") as mock_llm:
            mock_llm.return_value = "# Final Report\n\nThis is the report."
            state = {
                "task": "Research topic",
                "content": ["Summary 1", "Summary 2"],
                "references": ["https://example.com/1", "https://example.com/2"],
            }

            result = await writer_node(state)

            assert "report" in result
            assert isinstance(result["report"], str)
            assert len(result["report"]) > 0

    async def test_writer_uses_planner_model(self) -> None:
        """writer_node should use planner_model for high-quality output."""
        from src.config import settings
        from src.nodes.writer import writer_node

        with patch("src.nodes.writer.call_llm") as mock_llm:
            mock_llm.return_value = "Report content"
            state = {
                "task": "Test task",
                "content": ["Content"],
                "references": ["https://example.com"],
            }

            await writer_node(state)

            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs["model"] == settings.planner_model

    async def test_writer_includes_all_content(self) -> None:
        """writer_node should pass all content to the LLM."""
        from src.nodes.writer import writer_node

        with patch("src.nodes.writer.call_llm") as mock_llm:
            mock_llm.return_value = "Report"
            state = {
                "task": "Test task",
                "content": ["Content A", "Content B", "Content C"],
                "references": [],
            }

            await writer_node(state)

            call_args = mock_llm.call_args[0][0]
            assert "Content A" in call_args
            assert "Content B" in call_args
            assert "Content C" in call_args

    async def test_writer_formats_references(self) -> None:
        """writer_node should include references in the prompt."""
        from src.nodes.writer import writer_node

        with patch("src.nodes.writer.call_llm") as mock_llm:
            mock_llm.return_value = "Report"
            state = {
                "task": "Test task",
                "content": ["Content"],
                "references": [
                    "https://example.com/page1",
                    "https://example.com/page2",
                ],
            }

            await writer_node(state)

            call_args = mock_llm.call_args[0][0]
            assert "https://example.com/page1" in call_args
            assert "https://example.com/page2" in call_args

    async def test_writer_handles_empty_content(self) -> None:
        """writer_node should handle empty content list."""
        from src.nodes.writer import writer_node

        with patch("src.nodes.writer.call_llm") as mock_llm:
            mock_llm.return_value = "Report with no specific content"
            state = {
                "task": "Test task",
                "content": [],
                "references": [],
            }

            result = await writer_node(state)

            assert "report" in result

    async def test_writer_handles_llm_error(self) -> None:
        """writer_node should raise WriterError when LLM fails."""
        from src.llm import LLMError
        from src.nodes.writer import WriterError, writer_node

        with patch("src.nodes.writer.call_llm") as mock_llm:
            mock_llm.side_effect = LLMError("Connection failed")
            state = {
                "task": "Test task",
                "content": ["Content"],
                "references": [],
            }

            with pytest.raises(WriterError) as exc_info:
                await writer_node(state)

            assert (
                "LLM" in str(exc_info.value) or "failed" in str(exc_info.value).lower()
            )


class TestWriterError:
    """Tests for the WriterError exception class."""

    def test_writer_error_is_exception(self) -> None:
        """WriterError should be an Exception subclass."""
        from src.nodes.writer import WriterError

        assert issubclass(WriterError, Exception)

    def test_writer_error_message(self) -> None:
        """WriterError should store the error message."""
        from src.nodes.writer import WriterError

        error = WriterError("Test error")
        assert str(error) == "Test error"
