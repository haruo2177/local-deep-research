"""LLM utilities for Ollama integration."""

from __future__ import annotations

from langchain_ollama import ChatOllama

from src.config import settings


class LLMError(Exception):
    """LLM invocation error."""


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
        response = await llm.ainvoke(prompt)
        return str(response.content)
    except TimeoutError as e:
        raise LLMError(f"LLM call timeout: {e}") from e
    except ConnectionError as e:
        raise LLMError(f"LLM connection error: {e}") from e
    except Exception as e:
        raise LLMError(f"LLM call failed: {e}") from e
