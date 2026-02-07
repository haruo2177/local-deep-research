"""Reviewer node - evaluates information sufficiency."""

from __future__ import annotations

import json
import logging
from typing import Any

from src.config import settings
from src.llm import call_llm
from src.logging_utils import preview_text
from src.prompts.templates import format_reviewer_prompt

MIN_ITERATIONS = 2
logger = logging.getLogger(__name__)


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
    logger.info(
        "Reviewer start step=%s content_items=%s",
        steps_completed,
        len(content),
    )

    if steps_completed >= settings.max_iterations:
        logger.info(
            "Reviewer forcing sufficient due to max_iterations=%s",
            settings.max_iterations,
        )
        return {"is_sufficient": True}

    # Require minimum iterations before allowing "sufficient"
    if steps_completed < MIN_ITERATIONS:
        logger.info(
            "Reviewer insufficient because minimum iterations not reached min=%s",
            MIN_ITERATIONS,
        )
        return {"is_sufficient": False}

    prompt = format_reviewer_prompt(task, content)
    response = await call_llm(prompt, model=settings.worker_model)
    logger.info("Reviewer response preview=%s", preview_text(response))

    try:
        data = json.loads(response)
        is_sufficient = data.get("sufficient", False)
    except json.JSONDecodeError:
        is_sufficient = False

    logger.info("Reviewer end sufficient=%s", is_sufficient)
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
