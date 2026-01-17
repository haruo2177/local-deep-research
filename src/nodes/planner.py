"""Planner node - generates research plan from user query."""

from __future__ import annotations

import json
from typing import Any

from src.config import settings
from src.llm import LLMError, call_llm
from src.prompts.templates import format_planner_prompt

MAX_RETRIES = 3


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

    prompt = format_planner_prompt(task)

    for attempt in range(MAX_RETRIES):
        try:
            response = await call_llm(prompt, model=settings.planner_model)
            queries = _parse_queries(response)

            if not queries:
                queries = [task]

            return {"plan": queries}

        except LLMError as e:
            raise PlannerError(f"LLM call failed: {e}") from e
        except json.JSONDecodeError as e:
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
