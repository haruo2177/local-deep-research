"""Writer node - generates final research report."""

from __future__ import annotations

import logging
from typing import Any

from src.config import settings
from src.llm import LLMError, call_llm
from src.logging_utils import preview_text
from src.prompts.templates import format_writer_prompt


class WriterError(Exception):
    """Writer node error."""


logger = logging.getLogger(__name__)


async def writer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate the final research report.

    Args:
        state: The current research state with task, content, and references.

    Returns:
        A dict with report (str).

    Raises:
        WriterError: If LLM call fails.
    """
    task = state.get("original_task") or state.get("task", "")
    content = state.get("content", [])
    references = state.get("references", [])
    logger.info(
        "Writer start task=%s content_items=%s references=%s",
        task,
        len(content),
        len(references),
    )

    prompt = format_writer_prompt(task, content, references)

    try:
        report = await call_llm(prompt, model=settings.writer_model)
    except LLMError as e:
        logger.exception("Writer LLM call failed")
        raise WriterError(f"LLM call failed: {e}") from e

    logger.info("Writer end report_chars=%s", len(report))
    logger.info("Writer report preview=%s", preview_text(report))
    return {"report": report}
