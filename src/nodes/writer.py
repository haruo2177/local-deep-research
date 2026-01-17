"""Writer node - generates final research report."""

from __future__ import annotations

from typing import Any

from src.config import settings
from src.llm import LLMError, call_llm
from src.prompts.templates import format_writer_prompt


class WriterError(Exception):
    """Writer node error."""


async def writer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate the final research report.

    Args:
        state: The current research state with task, content, and references.

    Returns:
        A dict with report (str).

    Raises:
        WriterError: If LLM call fails.
    """
    task = state.get("task", "")
    content = state.get("content", [])
    references = state.get("references", [])

    prompt = format_writer_prompt(task, content, references)

    try:
        report = await call_llm(prompt, model=settings.planner_model)
    except LLMError as e:
        raise WriterError(f"LLM call failed: {e}") from e

    return {"report": report}
