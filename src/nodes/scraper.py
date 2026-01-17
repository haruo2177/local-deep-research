"""Scraper node - fetches and summarizes web content."""

from __future__ import annotations

from typing import Any

from src.config import settings
from src.llm import call_llm
from src.prompts.templates import format_summarizer_prompt
from src.tools.scrape import scrape_multiple

MAX_CONTENT_FOR_SUMMARY = 10000


async def scraper_node(state: dict[str, Any]) -> dict[str, Any]:
    """Scrape URLs and summarize content.

    Args:
        state: The current research state containing references.

    Returns:
        A dict with content (list of summaries with source URLs).
    """
    references = state.get("references", [])

    if not references:
        return {"content": []}

    scrape_results = await scrape_multiple(references)

    summaries = []
    for result in scrape_results:
        if not result.success or not result.markdown:
            continue

        content_to_summarize = result.markdown
        if len(content_to_summarize) > MAX_CONTENT_FOR_SUMMARY:
            content_to_summarize = content_to_summarize[:MAX_CONTENT_FOR_SUMMARY]

        prompt = format_summarizer_prompt(content_to_summarize)
        summary = await call_llm(prompt, model=settings.worker_model)

        summary_with_source = f"{summary}\n\nSource: {result.url}"
        summaries.append(summary_with_source)

    return {"content": summaries}
