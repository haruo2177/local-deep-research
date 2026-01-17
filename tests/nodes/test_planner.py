"""Tests for the Planner node."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestPlannerNode:
    """Tests for the planner_node function."""

    async def test_planner_returns_plan_list(self) -> None:
        """planner_node should return a dict with plan as a list."""
        from src.nodes.planner import planner_node

        with patch("src.nodes.planner.call_llm") as mock_llm:
            mock_llm.return_value = '{"queries": ["query 1", "query 2", "query 3"]}'
            state = {"task": "What is LangGraph?"}

            result = await planner_node(state)

            assert "plan" in result
            assert isinstance(result["plan"], list)
            assert len(result["plan"]) == 3

    async def test_planner_parses_json_response(self) -> None:
        """planner_node should parse JSON response and extract queries."""
        from src.nodes.planner import planner_node

        with patch("src.nodes.planner.call_llm") as mock_llm:
            mock_llm.return_value = (
                '{"queries": ["search for LangGraph docs", "LangGraph examples"]}'
            )
            state = {"task": "What is LangGraph?"}

            result = await planner_node(state)

            assert result["plan"] == ["search for LangGraph docs", "LangGraph examples"]

    async def test_planner_retries_on_invalid_json(self) -> None:
        """planner_node should retry when LLM returns invalid JSON."""
        from src.nodes.planner import planner_node

        with patch("src.nodes.planner.call_llm") as mock_llm:
            mock_llm.side_effect = [
                "not valid json",
                '{"queries": ["valid query"]}',
            ]
            state = {"task": "Test task"}

            result = await planner_node(state)

            assert mock_llm.call_count == 2
            assert result["plan"] == ["valid query"]

    async def test_planner_max_retries_exceeded(self) -> None:
        """planner_node should raise PlannerError after max retries."""
        from src.nodes.planner import PlannerError, planner_node

        with patch("src.nodes.planner.call_llm") as mock_llm:
            mock_llm.return_value = "always invalid json"
            state = {"task": "Test task"}

            with pytest.raises(PlannerError) as exc_info:
                await planner_node(state)

            assert mock_llm.call_count == 3
            assert (
                "retry" in str(exc_info.value).lower()
                or "failed" in str(exc_info.value).lower()
            )

    async def test_planner_uses_task_as_fallback(self) -> None:
        """planner_node should use task as query when queries list is empty."""
        from src.nodes.planner import planner_node

        with patch("src.nodes.planner.call_llm") as mock_llm:
            mock_llm.return_value = '{"queries": []}'
            state = {"task": "What is LangGraph?"}

            result = await planner_node(state)

            assert result["plan"] == ["What is LangGraph?"]

    async def test_planner_calls_correct_model(self) -> None:
        """planner_node should use planner_model from settings."""
        from src.config import settings
        from src.nodes.planner import planner_node

        with patch("src.nodes.planner.call_llm") as mock_llm:
            mock_llm.return_value = '{"queries": ["test"]}'
            state = {"task": "Test task"}

            await planner_node(state)

            mock_llm.assert_called_once()
            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs["model"] == settings.planner_model

    async def test_planner_handles_llm_error(self) -> None:
        """planner_node should raise PlannerError when LLM fails."""
        from src.llm import LLMError
        from src.nodes.planner import PlannerError, planner_node

        with patch("src.nodes.planner.call_llm") as mock_llm:
            mock_llm.side_effect = LLMError("Connection failed")
            state = {"task": "Test task"}

            with pytest.raises(PlannerError) as exc_info:
                await planner_node(state)

            assert (
                "LLM" in str(exc_info.value)
                or "connection" in str(exc_info.value).lower()
            )

    async def test_planner_empty_task_raises(self) -> None:
        """planner_node should raise ValueError for empty task."""
        from src.nodes.planner import planner_node

        state = {"task": ""}

        with pytest.raises(ValueError) as exc_info:
            await planner_node(state)

        assert (
            "empty" in str(exc_info.value).lower()
            or "task" in str(exc_info.value).lower()
        )

    async def test_planner_whitespace_task_raises(self) -> None:
        """planner_node should raise ValueError for whitespace-only task."""
        from src.nodes.planner import planner_node

        state = {"task": "   "}

        with pytest.raises(ValueError):
            await planner_node(state)


class TestPlannerError:
    """Tests for the PlannerError exception class."""

    def test_planner_error_is_exception(self) -> None:
        """PlannerError should be an Exception subclass."""
        from src.nodes.planner import PlannerError

        assert issubclass(PlannerError, Exception)

    def test_planner_error_message(self) -> None:
        """PlannerError should store the error message."""
        from src.nodes.planner import PlannerError

        error = PlannerError("Test error")
        assert str(error) == "Test error"
