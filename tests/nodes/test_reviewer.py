"""Tests for the Reviewer node."""

from __future__ import annotations

from unittest.mock import patch


class TestReviewerNode:
    """Tests for the reviewer_node function."""

    async def test_reviewer_returns_is_sufficient(self) -> None:
        """reviewer_node should return a dict with is_sufficient key."""
        from src.nodes.reviewer import reviewer_node

        with patch("src.nodes.reviewer.call_llm") as mock_llm:
            mock_llm.return_value = '{"sufficient": true, "reason": "Enough info"}'
            state = {
                "task": "Test task",
                "content": ["Some content"],
                "steps_completed": 2,  # Must meet MIN_ITERATIONS
            }

            result = await reviewer_node(state)

            assert "is_sufficient" in result
            assert isinstance(result["is_sufficient"], bool)

    async def test_reviewer_sufficient_true(self) -> None:
        """reviewer_node should return is_sufficient=True when LLM says sufficient."""
        from src.nodes.reviewer import reviewer_node

        with patch("src.nodes.reviewer.call_llm") as mock_llm:
            mock_llm.return_value = (
                '{"sufficient": true, "reason": "Complete information"}'
            )
            state = {
                "task": "Test task",
                "content": ["Comprehensive content here"],
                "steps_completed": 2,  # Must meet MIN_ITERATIONS
            }

            result = await reviewer_node(state)

            assert result["is_sufficient"] is True

    async def test_reviewer_sufficient_false(self) -> None:
        """reviewer_node should return is_sufficient=False when info is incomplete."""
        from src.nodes.reviewer import reviewer_node

        with patch("src.nodes.reviewer.call_llm") as mock_llm:
            mock_llm.return_value = '{"sufficient": false, "reason": "Need more info"}'
            state = {
                "task": "Test task",
                "content": ["Partial content"],
                "steps_completed": 2,  # Must meet MIN_ITERATIONS
            }

            result = await reviewer_node(state)

            assert result["is_sufficient"] is False

    async def test_reviewer_forces_false_below_min_iterations(self) -> None:
        """reviewer_node should return is_sufficient=False if below MIN_ITERATIONS."""
        from src.nodes.reviewer import MIN_ITERATIONS, reviewer_node

        with patch("src.nodes.reviewer.call_llm") as mock_llm:
            # LLM should NOT be called when below MIN_ITERATIONS
            state = {
                "task": "Test task",
                "content": ["Content"],
                "steps_completed": MIN_ITERATIONS - 1,
            }

            result = await reviewer_node(state)

            assert result["is_sufficient"] is False
            mock_llm.assert_not_called()

    async def test_reviewer_max_iterations_forces_true(self) -> None:
        """reviewer_node should force is_sufficient=True at max iterations."""
        from src.config import settings
        from src.nodes.reviewer import reviewer_node

        with patch("src.nodes.reviewer.call_llm") as mock_llm:
            mock_llm.return_value = '{"sufficient": false, "reason": "Need more"}'
            state = {
                "task": "Test task",
                "content": ["Some content"],
                "steps_completed": settings.max_iterations,
            }

            result = await reviewer_node(state)

            assert result["is_sufficient"] is True

    async def test_reviewer_parses_json_response(self) -> None:
        """reviewer_node should parse JSON response from LLM."""
        from src.nodes.reviewer import reviewer_node

        with patch("src.nodes.reviewer.call_llm") as mock_llm:
            mock_llm.return_value = (
                '{"sufficient": true, "reason": "All info gathered"}'
            )
            state = {
                "task": "Test task",
                "content": ["Content"],
                "steps_completed": 2,  # Must meet MIN_ITERATIONS
            }

            result = await reviewer_node(state)

            assert result["is_sufficient"] is True

    async def test_reviewer_handles_invalid_json(self) -> None:
        """reviewer_node should default to False on invalid JSON."""
        from src.nodes.reviewer import reviewer_node

        with patch("src.nodes.reviewer.call_llm") as mock_llm:
            mock_llm.return_value = "Not valid JSON at all"
            state = {
                "task": "Test task",
                "content": ["Content"],
                "steps_completed": 2,  # Must meet MIN_ITERATIONS
            }

            result = await reviewer_node(state)

            assert result["is_sufficient"] is False

    async def test_reviewer_uses_worker_model(self) -> None:
        """reviewer_node should use worker_model from settings."""
        from src.config import settings
        from src.nodes.reviewer import reviewer_node

        with patch("src.nodes.reviewer.call_llm") as mock_llm:
            mock_llm.return_value = '{"sufficient": true, "reason": "ok"}'
            state = {
                "task": "Test task",
                "content": ["Content"],
                "steps_completed": 2,  # Must meet MIN_ITERATIONS
            }

            await reviewer_node(state)

            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs["model"] == settings.worker_model


class TestShouldContinueResearch:
    """Tests for the should_continue_research function."""

    def test_should_continue_returns_writer(self) -> None:
        """should_continue_research returns 'writer' when sufficient=True."""
        from src.nodes.reviewer import should_continue_research

        state = {"is_sufficient": True}

        result = should_continue_research(state)

        assert result == "writer"

    def test_should_continue_returns_researcher(self) -> None:
        """should_continue_research returns 'researcher' when sufficient=False."""
        from src.nodes.reviewer import should_continue_research

        state = {"is_sufficient": False}

        result = should_continue_research(state)

        assert result == "researcher"
