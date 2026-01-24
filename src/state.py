"""LangGraph state definition for the research workflow."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class ResearchState(TypedDict):
    """State schema for the Deep Research LangGraph workflow.

    Attributes:
        task: The original user query/research question (may be translated to English).
        plan: List of search queries derived from the task.
        steps_completed: Number of research iterations completed.
        content: Accumulated summaries from scraped pages (uses Annotated for appending).
        current_search_query: The query being processed in the current iteration.
        references: List of source URLs for citations.
        scraped_urls: List of URLs that have already been scraped (to avoid duplicates).
        is_sufficient: Flag indicating if gathered information is sufficient.
        report: The final generated research report.
        source_language: ISO 639-1 language code of the original task (e.g., "ja", "en").
        original_task: The original user query before translation.
    """

    task: str
    plan: list[str]
    steps_completed: int
    content: Annotated[list[str], operator.add]
    current_search_query: str
    references: Annotated[list[str], operator.add]
    scraped_urls: Annotated[list[str], operator.add]
    is_sufficient: bool
    report: str
    source_language: str
    original_task: str
