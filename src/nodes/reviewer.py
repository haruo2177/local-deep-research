"""Reviewer node - evaluates information sufficiency."""

from __future__ import annotations

import json
from typing import Any

from src.config import settings
from src.llm import call_llm
from src.prompts.templates import format_reviewer_prompt


async def reviewer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate if gathered information is sufficient.

    Args:
        state: The current research state with task, content, and steps_completed.

    Returns:
        A dict with is_sufficient (bool).
    """
    task = state.get("task", "")
    content = state.get("content", [])
    steps_completed = state.get("steps_completed", 0)

    if steps_completed >= settings.max_iterations:
        return {"is_sufficient": True}

    prompt = format_reviewer_prompt(task, content)
    response = await call_llm(prompt, model=settings.worker_model)

    try:
        data = json.loads(response)
        is_sufficient = data.get("sufficient", False)
    except json.JSONDecodeError:
        is_sufficient = False

    return {"is_sufficient": is_sufficient}


def should_continue_research(state: dict[str, Any]) -> str:
    """Determine routing based on reviewer's decision.

    Args:
        state: The current research state with is_sufficient.

    Returns:
        "writer" if sufficient, "researcher" otherwise.
    """
    if state.get("is_sufficient", False):
        return "writer"
    return "researcher"
