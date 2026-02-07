"""Planner node - generates research plan from user query."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Any

from src.config import settings
from src.llm import LLMError, call_llm
from src.logging_utils import preview_text
from src.prompts.templates import format_planner_prompt

MAX_RETRIES = 3
MAX_QUERIES = 5
MAX_TERMS_PER_QUERY = 8
MIN_ASCII_TOKEN_LENGTH = 3
logger = logging.getLogger(__name__)

ASCII_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9:+#./_-]*")
LANG_CHUNK_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9:+#./_-]*"
    r"|[\u3040-\u30ff]{2,}"  # Hiragana/Katakana
    r"|[\u3400-\u4dbf\u4e00-\u9fff]{2,}"  # CJK Unified Ideographs
    r"|[\uac00-\ud7af]{2,}"  # Hangul
)
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "who",
    "why",
    "with",
}


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
            raw_queries = _parse_queries(response)
            queries = _sanitize_queries(task, raw_queries)

            if queries:
                logger.info("Planner end queries=%s", len(queries))
                logger.info(
                    "Planner queries=%s",
                    " | ".join(preview_text(q, max_chars=80) for q in queries),
                )
                return {"plan": queries}

            logger.warning(
                "Planner queries rejected by quality gate attempt=%s/%s raw_queries=%s",
                attempt + 1,
                MAX_RETRIES,
                len(raw_queries),
            )
            if attempt == MAX_RETRIES - 1:
                fallback_query = _normalize_query(task)
                logger.warning(
                    "Planner fallback to task due to quality gate retries exhausted"
                )
                return {"plan": [fallback_query]}

            continue

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
    raw_queries = data.get("queries", [])
    if not isinstance(raw_queries, list):
        return []
    queries = [query for query in raw_queries if isinstance(query, str)]
    return queries


def _sanitize_queries(task: str, queries: list[str]) -> list[str]:
    """Normalize and filter planner queries by quality rules."""
    task_keywords = _extract_task_keywords(task)
    task_has_hangul = _has_hangul(task)
    accepted: list[str] = []
    seen: set[str] = set()

    for index, raw_query in enumerate(queries, start=1):
        query = _normalize_query(raw_query)
        reason = _reject_reason(
            query=query,
            task_keywords=task_keywords,
            task_has_hangul=task_has_hangul,
        )
        if reason:
            logger.info(
                "Planner query rejected index=%s reason=%s query=%s",
                index,
                reason,
                preview_text(query),
            )
            continue

        dedupe_key = query.casefold()
        if dedupe_key in seen:
            logger.info("Planner query rejected index=%s reason=duplicate", index)
            continue
        seen.add(dedupe_key)

        accepted.append(query)
        logger.info("Planner query accepted index=%s query=%s", index, preview_text(query))
        if len(accepted) >= MAX_QUERIES:
            break

    return accepted


def _reject_reason(
    *,
    query: str,
    task_keywords: set[str],
    task_has_hangul: bool,
) -> str | None:
    """Return rejection reason string if query does not meet quality gate."""
    if not query:
        return "empty"
    if "\uFFFD" in query:
        return "replacement_character"
    if len(query.split()) > MAX_TERMS_PER_QUERY:
        return "too_many_terms"
    if _is_single_short_ascii_token(query):
        return "too_short_ascii_query"
    if _has_mixed_ascii_and_cjk_token(query):
        return "mixed_ascii_cjk_token"
    if not task_has_hangul and _has_hangul(query):
        return "hangul_not_in_task"
    if task_keywords and not _contains_any_keyword(query, task_keywords):
        return "missing_task_keyword"
    return None


def _normalize_query(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\u3000", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _extract_task_keywords(task: str) -> set[str]:
    normalized_task = _normalize_query(task)
    if not normalized_task:
        return set()

    keywords: set[str] = set()
    for token in LANG_CHUNK_PATTERN.findall(normalized_task):
        normalized_token = token.casefold()
        if ASCII_TOKEN_PATTERN.fullmatch(token):
            if (
                len(normalized_token) < MIN_ASCII_TOKEN_LENGTH
                or normalized_token in STOPWORDS
            ):
                continue
        keywords.add(normalized_token)

    # Full task string is included to support no-space CJK tasks.
    keywords.add(normalized_task.casefold())
    return keywords


def _contains_any_keyword(query: str, keywords: set[str]) -> bool:
    normalized_query = query.casefold()
    for keyword in keywords:
        if keyword and keyword in normalized_query:
            return True
    return False


def _has_hangul(text: str) -> bool:
    return bool(re.search(r"[\uac00-\ud7af]", text))


def _has_mixed_ascii_and_cjk_token(query: str) -> bool:
    for token in query.split():
        has_ascii = bool(re.search(r"[A-Za-z]", token))
        has_cjk = bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", token))
        if has_ascii and has_cjk:
            return True
    return False


def _is_single_short_ascii_token(query: str) -> bool:
    tokens = query.split()
    if len(tokens) != 1:
        return False
    token = tokens[0]
    return bool(ASCII_TOKEN_PATTERN.fullmatch(token) and len(token) < 4)
