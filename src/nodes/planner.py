"""Planner node - generates research plan from user query."""

from __future__ import annotations

import json
import logging
from typing import Any

from src.config import settings
from src.llm import LLMError, call_llm
from src.logging_utils import preview_text
from src.prompts.templates import format_planner_prompt

MAX_RETRIES = 3
logger = logging.getLogger(__name__)


class PlannerError(Exception):
    """Planner node error."""


async def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate a research plan from the user's query.

    Args:
        state: The current research state containing the task.

    Returns:
        A dict with the plan (list of search queries).

    Raises:
        ValueError: If task is empty.
        PlannerError: If LLM call fails or JSON parsing fails after max retries.
    """
    task = state.get("task", "")

    if not task or not task.strip():
        raise ValueError("task cannot be empty")

    logger.info("Planner start task=%s", task)
    prompt = format_planner_prompt(task)

    for attempt in range(MAX_RETRIES):
        try:
            logger.info("Planner LLM call attempt=%s/%s", attempt + 1, MAX_RETRIES)
            response = await call_llm(prompt, model=settings.planner_model)
            logger.info("Planner response preview=%s", preview_text(response))
            queries = _parse_queries(response)

            if not queries:
                queries = [task]
                logger.info("Planner produced empty queries; fallback to task")

            logger.info("Planner end queries=%s", len(queries))
            logger.info("Planner queries=%s", " | ".join(preview_text(q, max_chars=80) for q in queries))
            return {"plan": queries}

        except LLMError as e:
            logger.exception("Planner LLM call failed at attempt=%s", attempt + 1)
            raise PlannerError(f"LLM call failed: {e}") from e
        except json.JSONDecodeError as e:
            logger.warning(
                "Planner JSON parse failed at attempt=%s/%s",
                attempt + 1,
                MAX_RETRIES,
            )
            if attempt == MAX_RETRIES - 1:
                raise PlannerError(
                    f"Failed to parse JSON response after {MAX_RETRIES} retries"
                ) from e
            continue

    raise PlannerError(f"Failed after {MAX_RETRIES} retries")


def _parse_queries(response: str) -> list[str]:
    """Parse the LLM response to extract queries.

    Args:
        response: The raw LLM response.

    Returns:
        A list of query strings.

    Raises:
        json.JSONDecodeError: If the response is not valid JSON.
    """
    data = json.loads(response)
    queries: list[str] = data.get("queries", [])
    return queries
