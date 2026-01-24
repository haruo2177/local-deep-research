"""Translator nodes for input/output language handling."""

from __future__ import annotations

from typing import Any

from src.config import settings
from src.tools.translate import (
    TranslationError,
    detect_language,
    normalize_language_code,
    translate_from_english,
    translate_to_english,
)


class TranslatorError(Exception):
    """Translator node error."""

    pass


async def translator_input_node(state: dict[str, Any]) -> dict[str, Any]:
    """Detect language and translate task to English if needed.

    Args:
        state: The current research state containing the task.

    Returns:
        A dict with source_language, original_task, and potentially updated task.
    """
    task = state.get("task", "")
    original_task = task

    if not settings.enable_translation:
        return {
            "source_language": "en",
            "original_task": original_task,
        }

    # Detect language
    try:
        source_language = detect_language(task)
    except Exception:
        # Default to English if detection fails
        source_language = "en"

    # Normalize language code (e.g., zh-cn -> zh)
    normalized_lang = normalize_language_code(source_language)

    # If source is English, no translation needed
    if normalized_lang == "en":
        return {
            "source_language": source_language,
            "original_task": original_task,
            "task": task,
        }

    # Translate to English
    try:
        result = translate_to_english(task, source_language)
        translated_task = result.translated_text
    except TranslationError:
        # Keep original task if translation fails
        translated_task = task

    return {
        "source_language": source_language,
        "original_task": original_task,
        "task": translated_task,
    }


async def translator_output_node(state: dict[str, Any]) -> dict[str, Any]:
    """Translate report back to source language if needed.

    Args:
        state: The current research state containing report and source_language.

    Returns:
        A dict with potentially translated report.
    """
    if not settings.enable_translation:
        return {}

    source_language = state.get("source_language", "en")
    report = state.get("report", "")

    # Normalize language code
    normalized_lang = normalize_language_code(source_language)

    # If source is English or report is empty, no translation needed
    if normalized_lang == "en" or not report:
        return {}

    # Translate report to source language
    try:
        result = translate_from_english(report, source_language)
        return {"report": result.translated_text}
    except TranslationError:
        # Keep English report if translation fails
        return {}
