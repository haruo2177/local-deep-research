"""Web scraping tool using Crawl4AI."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


@dataclass
class ScrapeResult:
    """Result from scraping a URL."""

    url: str
    markdown: str
    success: bool
    error_message: str | None = None
    title: str | None = None


class ScrapeError(Exception):
    """Exception raised when scraping fails."""

    pass


def _validate_url(url: str) -> None:
    """Validate URL format.

    Args:
        url: The URL to validate.

    Raises:
        ValueError: If URL is invalid.
    """
    if not url or not url.strip():
        raise ValueError("url must not be empty")

    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        raise ValueError("url must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("url must have a valid domain")


async def scrape(
    url: str,
    *,
    timeout: float = 30.0,
    max_content_length: int = 50000,
) -> ScrapeResult:
    """Scrape a URL and return markdown content.

    Args:
        url: The URL to scrape.
        timeout: Request timeout in seconds.
        max_content_length: Maximum characters to return (truncates if exceeded).

    Returns:
        ScrapeResult object with markdown content.

    Raises:
        ValueError: If URL is invalid.
    """
    _validate_url(url)

    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig()

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await asyncio.wait_for(
                crawler.arun(url=url, config=run_config),
                timeout=timeout,
            )

            if not result.success:
                return ScrapeResult(
                    url=url,
                    markdown="",
                    success=False,
                    error_message=result.error_message or "Unknown error",
                )

            if hasattr(result.markdown, "raw_markdown"):
                markdown = result.markdown.raw_markdown
            else:
                markdown = str(result.markdown) if result.markdown else ""

            if len(markdown) > max_content_length:
                markdown = markdown[:max_content_length] + "\n\n[Content truncated]"

            return ScrapeResult(
                url=result.url or url,
                markdown=markdown,
                success=True,
            )

    except asyncio.TimeoutError:
        return ScrapeResult(
            url=url,
            markdown="",
            success=False,
            error_message=f"Scrape timeout after {timeout}s",
        )
    except Exception as e:
        return ScrapeResult(
            url=url,
            markdown="",
            success=False,
            error_message=str(e),
        )


async def scrape_multiple(
    urls: list[str],
    *,
    timeout: float = 30.0,
    max_content_length: int = 50000,
) -> list[ScrapeResult]:
    """Scrape multiple URLs sequentially.

    Processes URLs one at a time to manage memory.
    Failed URLs are returned with success=False.

    Args:
        urls: List of URLs to scrape.
        timeout: Timeout per URL.
        max_content_length: Maximum characters per result.

    Returns:
        List of ScrapeResult objects (one per URL).
    """
    if not urls:
        return []

    results = []
    for url in urls:
        result = await scrape(
            url,
            timeout=timeout,
            max_content_length=max_content_length,
        )
        results.append(result)

    return results
