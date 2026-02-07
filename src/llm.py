"""LLM utilities for Ollama integration."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable

from langchain_ollama import ChatOllama

from src.config import settings


class LLMError(Exception):
    """LLM invocation error."""


logger = logging.getLogger(__name__)
LLM_PROGRESS_LOG_INTERVAL_SECONDS = 30.0


def _connection_help_message(error: Exception) -> str | None:
    """Build a user-friendly help message for Ollama connectivity issues."""
    message = str(error).lower()
    error_name = type(error).__name__.lower()
    if (
        "all connection attempts failed" in message
        or "connection refused" in message
        or "connecterror" in error_name
    ):
        return (
            f"LLM connection error: could not reach Ollama at {settings.ollama_url}. "
            "Start Ollama (e.g. `docker compose up -d ollama`) and verify "
            "with `curl <OLLAMA_URL>/api/tags`."
        )
    return None


async def call_llm(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.7,
) -> str:
    """Call Ollama LLM and return text response.

    Args:
        prompt: The prompt to send to the LLM.
        model: The model to use. Defaults to settings.worker_model.
        temperature: The temperature for generation. Defaults to 0.7.

    Returns:
        The LLM response as a string.

    Raises:
        LLMError: If the LLM call fails due to timeout or connection error.
    """
    if model is None:
        model = settings.worker_model

    llm = ChatOllama(
        model=model,
        base_url=settings.ollama_url,
        temperature=temperature,
    )

    try:
        started_at = time.perf_counter()
        logger.info("LLM call start model=%s prompt_chars=%s", model, len(prompt))
        response = await _await_with_progress(
            llm.ainvoke(prompt),
            model=model,
            prompt_chars=len(prompt),
            interval_seconds=LLM_PROGRESS_LOG_INTERVAL_SECONDS,
        )
        text = str(response.content)
        elapsed = time.perf_counter() - started_at
        logger.info(
            "LLM call end model=%s response_chars=%s elapsed=%.2fs",
            model,
            len(text),
            elapsed,
        )
        return text
    except TimeoutError as e:
        logger.exception("LLM call timeout model=%s", model)
        raise LLMError(f"LLM call timeout: {e}") from e
    except ConnectionError as e:
        logger.exception("LLM connection error model=%s", model)
        help_message = _connection_help_message(e)
        if help_message:
            raise LLMError(help_message) from e
        raise LLMError(f"LLM connection error: {e}") from e
    except Exception as e:
        logger.exception("LLM call failed model=%s", model)
        help_message = _connection_help_message(e)
        if help_message:
            raise LLMError(help_message) from e
        raise LLMError(f"LLM call failed: {e}") from e


async def _await_with_progress(
    awaitable: Awaitable[object],
    *,
    model: str,
    prompt_chars: int,
    interval_seconds: float,
) -> object:
    """Await long-running LLM calls while periodically logging progress."""
    started_at = time.perf_counter()
    if isinstance(awaitable, (asyncio.Task, asyncio.Future)):
        task = awaitable
    else:
        task = asyncio.create_task(awaitable)
    try:
        while True:
            done, _ = await asyncio.wait(
                {task},
                timeout=interval_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if task in done:
                return await task
            if not task.done():
                elapsed = time.perf_counter() - started_at
                logger.info(
                    "LLM call in progress model=%s elapsed=%.0fs prompt_chars=%s",
                    model,
                    elapsed,
                    prompt_chars,
                )
    except asyncio.CancelledError:
        task.cancel()
        raise
