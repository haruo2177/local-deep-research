"""Tests for LangGraph state definition."""

from __future__ import annotations


class TestResearchStateFields:
    """Test ResearchState has required fields."""

    def test_state_has_task_field(self) -> None:
        """ResearchState should have a 'task' field."""
        from src.state import ResearchState

        assert "task" in ResearchState.__annotations__

    def test_state_has_plan_field(self) -> None:
        """ResearchState should have a 'plan' field."""
        from src.state import ResearchState

        assert "plan" in ResearchState.__annotations__

    def test_state_has_steps_completed_field(self) -> None:
        """ResearchState should have a 'steps_completed' field."""
        from src.state import ResearchState

        assert "steps_completed" in ResearchState.__annotations__

    def test_state_has_content_field(self) -> None:
        """ResearchState should have a 'content' field."""
        from src.state import ResearchState

        assert "content" in ResearchState.__annotations__

    def test_state_has_current_search_query_field(self) -> None:
        """ResearchState should have a 'current_search_query' field."""
        from src.state import ResearchState

        assert "current_search_query" in ResearchState.__annotations__

    def test_state_has_references_field(self) -> None:
        """ResearchState should have a 'references' field."""
        from src.state import ResearchState

        assert "references" in ResearchState.__annotations__

    def test_state_has_is_sufficient_field(self) -> None:
        """ResearchState should have an 'is_sufficient' field."""
        from src.state import ResearchState

        assert "is_sufficient" in ResearchState.__annotations__


class TestResearchStateTypes:
    """Test ResearchState field types."""

    def test_task_is_string(self) -> None:
        """Task field should be a string type."""
        import typing

        from src.state import ResearchState

        hints = typing.get_type_hints(ResearchState)
        assert hints["task"] is str

    def test_is_sufficient_is_bool(self) -> None:
        """is_sufficient field should be a bool type."""
        import typing

        from src.state import ResearchState

        hints = typing.get_type_hints(ResearchState)
        assert hints["is_sufficient"] is bool

    def test_steps_completed_is_int(self) -> None:
        """steps_completed field should be an int type."""
        import typing

        from src.state import ResearchState

        hints = typing.get_type_hints(ResearchState)
        assert hints["steps_completed"] is int


class TestResearchStateCreation:
    """Test creating ResearchState instances."""

    def test_create_minimal_state(self, empty_research_state: dict) -> None:
        """Should be able to create a state with minimal data."""
        from src.state import ResearchState

        state: ResearchState = empty_research_state  # type: ignore
        assert state["task"] == ""

    def test_create_populated_state(self, sample_research_state: dict) -> None:
        """Should be able to create a state with sample data."""
        from src.state import ResearchState

        state: ResearchState = sample_research_state  # type: ignore
        assert state["task"] == "What is LangGraph?"
        assert len(state["plan"]) == 3
