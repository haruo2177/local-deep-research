"""Researcher node - executes search queries."""

from __future__ import annotations

from typing import Any

from src.tools.search import SearchError, search

MAX_URLS_PER_SEARCH = 5


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

    if steps_completed >= len(plan):
        return {
            "current_search_query": "",
            "references": [],
            "steps_completed": steps_completed,
        }

    current_query = plan[steps_completed]

    try:
        results = await search(current_query, num_results=MAX_URLS_PER_SEARCH * 2)
    except SearchError:
        return {
            "current_search_query": current_query,
            "references": [],
            "steps_completed": steps_completed + 1,
        }

    new_urls = []
    existing_set = set(existing_references)

    for result in results:
        if result.url and result.url not in existing_set:
            new_urls.append(result.url)
            existing_set.add(result.url)
            if len(new_urls) >= MAX_URLS_PER_SEARCH:
                break

    return {
        "current_search_query": current_query,
        "references": new_urls,
        "steps_completed": steps_completed + 1,
    }
