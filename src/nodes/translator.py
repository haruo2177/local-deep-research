"""Translator nodes for input/output language handling."""

from __future__ import annotations

import logging
from typing import Any

from src.config import settings
from src.logging_utils import preview_text
from src.tools.translate import (
    TranslationError,
    detect_language,
    normalize_language_code,
    translate_from_english,
)


class TranslatorError(Exception):
    """Translator node error."""

    pass


logger = logging.getLogger(__name__)


async def translator_input_node(state: dict[str, Any]) -> dict[str, Any]:
    """Detect language and translate task to English if needed.

    Args:
        state: The current research state containing the task.

    Returns:
        A dict with source_language, original_task, and potentially updated task.
    """
    task = state.get("task", "")
    original_task = task
    logger.info("Translator input start")
    logger.info("Translator input task preview=%s", preview_text(task))

    if not settings.enable_translation:
        logger.info("Translator input skip translation disabled")
        return {
            "source_language": "en",
            "original_task": original_task,
            "task": task,
        }

    # Detect language
    try:
        source_language = detect_language(task)
    except Exception:
        # Default to English if detection fails
        source_language = "en"

    # Normalize language code (e.g., zh-cn -> zh)
    normalized_lang = normalize_language_code(source_language)

    if normalized_lang == "en":
        logger.info("Translator input detected English; no translation")
    else:
        logger.info(
            "Translator input detected source=%s; keeping original task to avoid query drift",
            source_language,
        )
    return {
        "source_language": source_language,
        "original_task": original_task,
        "task": task,
    }


async def translator_output_node(state: dict[str, Any]) -> dict[str, Any]:
    """Translate report back to source language if needed.

    Args:
        state: The current research state containing report and source_language.

    Returns:
        A dict with potentially translated report.
    """
    if not settings.enable_translation:
        logger.info("Translator output skip translation disabled")
        return {}

    source_language = state.get("source_language", "en")
    report = state.get("report", "")
    logger.info("Translator output source report preview=%s", preview_text(report))

    # Normalize language code
    normalized_lang = normalize_language_code(source_language)

    # If source is English or report is empty, no translation needed
    if normalized_lang == "en" or not report:
        logger.info("Translator output no translation needed source=%s", source_language)
        return {}

    # Translate report to source language only when report is English.
    try:
        report_language = normalize_language_code(detect_language(report))
    except Exception:
        report_language = "en"
    logger.info("Translator output detected report_language=%s", report_language)
    if report_language != "en":
        logger.info("Translator output skip translation because report is not English")
        return {}

    # Translate report to source language
    try:
        result = translate_from_english(report, source_language)
        logger.info("Translator output translated en -> %s", source_language)
        logger.info(
            "Translator output translated preview=%s",
            preview_text(result.translated_text),
        )
        return {"report": result.translated_text}
    except TranslationError:
        # Keep English report if translation fails
        logger.warning("Translator output failed; keeping English report")
        return {}
