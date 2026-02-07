"""Researcher node - executes search queries."""

from __future__ import annotations

import logging
from typing import Any

from src.tools.search import SearchError, search

MAX_URLS_PER_SEARCH = 5
logger = logging.getLogger(__name__)


async def researcher_node(state: dict[str, Any]) -> dict[str, Any]:
    """Execute search queries and collect URLs.

    Args:
        state: The current research state containing plan and steps_completed.

    Returns:
        A dict with current_search_query, references (new URLs), and steps_completed.
    """
    plan = state.get("plan", [])
    steps_completed = state.get("steps_completed", 0)
    existing_references = state.get("references", [])
    empty_cycles = state.get("empty_cycles", 0)
    empty_cycle_streak = state.get("empty_cycle_streak", 0)

    if steps_completed >= len(plan):
        # Plan is exhausted; count as an empty cycle but advance progress
        steps_completed += 1
        empty_cycles += 1
        empty_cycle_streak += 1
        total_cycles = steps_completed if steps_completed > 0 else 1
        ratio = empty_cycles / total_cycles

        logger.info(
            "Empty cycle %s/%s, empty=%s, ratio=%.2f%%, streak=%s",
            steps_completed,
            total_cycles,
            empty_cycles,
            ratio * 100,
            empty_cycle_streak,
        )

        return {
            "current_search_query": "",
            "references": [],
            "steps_completed": steps_completed,
            "empty_cycles": empty_cycles,
            "empty_cycle_streak": empty_cycle_streak,
        }

    current_query = plan[steps_completed]
    logger.info(
        "Researcher start step=%s/%s query=%s",
        steps_completed + 1,
        len(plan),
        current_query,
    )

    try:
        results = await search(current_query, num_results=MAX_URLS_PER_SEARCH * 2)
    except SearchError:
        logger.exception("Researcher search failed query=%s", current_query)
        # Search failure still advances the step but does not count as empty cycle
        return {
            "current_search_query": current_query,
            "references": [],
            "steps_completed": steps_completed + 1,
            "empty_cycles": empty_cycles,
            "empty_cycle_streak": 0,
        }

    new_urls = []
    existing_set = set(existing_references)

    for result in results:
        if result.url and result.url not in existing_set:
            new_urls.append(result.url)
            existing_set.add(result.url)
            if len(new_urls) >= MAX_URLS_PER_SEARCH:
                break

    logger.info(
        "Researcher end query=%s raw_results=%s new_urls=%s",
        current_query,
        len(results),
        len(new_urls),
    )
    return {
        "current_search_query": current_query,
        "references": new_urls,
        "steps_completed": steps_completed + 1,
        "empty_cycles": empty_cycles,
        "empty_cycle_streak": 0,
    }
