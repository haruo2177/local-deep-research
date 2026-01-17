"""Tests for prompt templates."""

from __future__ import annotations

import pytest

from src.prompts.templates import (
    PLANNER_PROMPT,
    REVIEWER_PROMPT,
    SUMMARIZER_PROMPT,
    WRITER_PROMPT,
    format_planner_prompt,
    format_reviewer_prompt,
    format_summarizer_prompt,
    format_writer_prompt,
)


class TestPlannerPrompt:
    """Tests for planner prompt template."""

    def test_planner_prompt_contains_task_placeholder(self) -> None:
        """PLANNER_PROMPT should contain {task} placeholder."""
        assert "{task}" in PLANNER_PROMPT

    def test_planner_prompt_requests_json(self) -> None:
        """PLANNER_PROMPT should request JSON output."""
        assert "JSON" in PLANNER_PROMPT

    def test_format_planner_prompt_substitutes_task(self) -> None:
        """format_planner_prompt should substitute task variable."""
        result = format_planner_prompt("量子コンピュータとは")
        assert "量子コンピュータとは" in result
        assert "{task}" not in result

    def test_format_planner_prompt_empty_task_raises(self) -> None:
        """format_planner_prompt should raise ValueError for empty task."""
        with pytest.raises(ValueError, match="task cannot be empty"):
            format_planner_prompt("")

    def test_format_planner_prompt_whitespace_only_raises(self) -> None:
        """format_planner_prompt should raise ValueError for whitespace-only task."""
        with pytest.raises(ValueError, match="task cannot be empty"):
            format_planner_prompt("   ")


class TestSummarizerPrompt:
    """Tests for summarizer prompt template."""

    def test_summarizer_prompt_contains_content_placeholder(self) -> None:
        """SUMMARIZER_PROMPT should contain {content} placeholder."""
        assert "{content}" in SUMMARIZER_PROMPT

    def test_format_summarizer_prompt_substitutes_content(self) -> None:
        """format_summarizer_prompt should substitute content variable."""
        result = format_summarizer_prompt("This is a long article about AI.")
        assert "This is a long article about AI." in result
        assert "{content}" not in result

    def test_format_summarizer_prompt_with_max_length(self) -> None:
        """format_summarizer_prompt should include max_length instruction."""
        result = format_summarizer_prompt("Some content", max_length=200)
        assert "200" in result


class TestReviewerPrompt:
    """Tests for reviewer prompt template."""

    def test_reviewer_prompt_contains_both_placeholders(self) -> None:
        """REVIEWER_PROMPT should contain {task} and {content} placeholders."""
        assert "{task}" in REVIEWER_PROMPT
        assert "{content}" in REVIEWER_PROMPT

    def test_format_reviewer_prompt_joins_content_list(self) -> None:
        """format_reviewer_prompt should join content list with newlines."""
        content = ["Summary 1", "Summary 2", "Summary 3"]
        result = format_reviewer_prompt("What is AI?", content)
        assert "Summary 1" in result
        assert "Summary 2" in result
        assert "Summary 3" in result
        assert "{task}" not in result
        assert "{content}" not in result


class TestWriterPrompt:
    """Tests for writer prompt template."""

    def test_writer_prompt_contains_all_placeholders(self) -> None:
        """WRITER_PROMPT should contain all three placeholders."""
        assert "{task}" in WRITER_PROMPT
        assert "{content}" in WRITER_PROMPT
        assert "{references}" in WRITER_PROMPT

    def test_format_writer_prompt_formats_references(self) -> None:
        """format_writer_prompt should format references as markdown links."""
        content = ["Summary about AI"]
        references = ["https://example.com/ai", "https://example.org/ml"]
        result = format_writer_prompt("What is AI?", content, references)
        assert "https://example.com/ai" in result
        assert "https://example.org/ml" in result
        assert "{task}" not in result
        assert "{content}" not in result
        assert "{references}" not in result

    def test_format_writer_prompt_empty_references(self) -> None:
        """format_writer_prompt should handle empty references."""
        content = ["Summary"]
        result = format_writer_prompt("Question?", content, [])
        assert "Question?" in result
        assert "{references}" not in result
