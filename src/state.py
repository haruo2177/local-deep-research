"""LangGraph state definition for the research workflow."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class ResearchState(TypedDict):
    """State schema for the Deep Research LangGraph workflow.

    Attributes:
        task: The original user query/research question.
        plan: List of search queries derived from the task.
        steps_completed: Number of research iterations completed.
        content: Accumulated summaries from scraped pages (uses Annotated for appending).
        current_search_query: The query being processed in the current iteration.
        references: List of source URLs for citations.
        is_sufficient: Flag indicating if gathered information is sufficient.
    """

    task: str
    plan: list[str]
    steps_completed: int
    content: Annotated[list[str], operator.add]
    current_search_query: str
    references: Annotated[list[str], operator.add]
    is_sufficient: bool
