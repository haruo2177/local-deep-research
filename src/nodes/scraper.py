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
        A dict with content (list of summaries with source URLs) and scraped_urls.
    """
    references = state.get("references", [])
    scraped_urls = set(state.get("scraped_urls", []))

    # Filter out already scraped URLs
    urls_to_scrape = [url for url in references if url not in scraped_urls]

    if not urls_to_scrape:
        return {"content": [], "scraped_urls": []}

    scrape_results = await scrape_multiple(urls_to_scrape)

    summaries = []
    newly_scraped = []
    for result in scrape_results:
        newly_scraped.append(result.url)

        if not result.success or not result.markdown:
            continue

        content_to_summarize = result.markdown
        if len(content_to_summarize) > MAX_CONTENT_FOR_SUMMARY:
            content_to_summarize = content_to_summarize[:MAX_CONTENT_FOR_SUMMARY]

        prompt = format_summarizer_prompt(content_to_summarize)
        summary = await call_llm(prompt, model=settings.worker_model)

        summary_with_source = f"{summary}\n\nSource: {result.url}"
        summaries.append(summary_with_source)

    return {"content": summaries, "scraped_urls": newly_scraped}
