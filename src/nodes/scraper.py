"""Scraper node - fetches and summarizes web content."""

from __future__ import annotations

import logging
from typing import Any

from src.config import settings
from src.llm import call_llm
from src.logging_utils import preview_text
from src.prompts.templates import format_summarizer_prompt
from src.tools.scrape import scrape_multiple

MAX_CONTENT_FOR_SUMMARY = 10000
logger = logging.getLogger(__name__)


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
        logger.info("Scraper skip no new urls")
        return {"content": [], "scraped_urls": []}

    logger.info("Scraper start urls=%s", len(urls_to_scrape))
    scrape_results = await scrape_multiple(urls_to_scrape)

    summaries = []
    newly_scraped = []
    for result in scrape_results:
        newly_scraped.append(result.url)

        if not result.success or not result.markdown:
            logger.warning("Scraper failed url=%s error=%s", result.url, result.error_message)
            continue

        logger.info("Scraper summarizing url=%s", result.url)
        content_to_summarize = result.markdown
        if len(content_to_summarize) > MAX_CONTENT_FOR_SUMMARY:
            content_to_summarize = content_to_summarize[:MAX_CONTENT_FOR_SUMMARY]

        prompt = format_summarizer_prompt(content_to_summarize)
        summary = await call_llm(prompt, model=settings.worker_model)
        logger.info("Scraper summary preview=%s", preview_text(summary))

        summary_with_source = f"{summary}\n\nSource: {result.url}"
        summaries.append(summary_with_source)

    logger.info(
        "Scraper end attempted=%s summarized=%s",
        len(newly_scraped),
        len(summaries),
    )
    return {"content": summaries, "scraped_urls": newly_scraped}
