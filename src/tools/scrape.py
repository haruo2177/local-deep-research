"""Web scraping tool using Crawl4AI."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

logger = logging.getLogger(__name__)

ANSI_RESET = "\x1b[0m"
ANSI_CYAN = "\x1b[36m"
ANSI_GREEN = "\x1b[32m"
ANSI_YELLOW = "\x1b[33m"
ANSI_RED = "\x1b[31m"


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


def _colorize(message: str, color: str) -> str:
    """Wrap message with ANSI color for terminal output."""
    return f"{color}{message}{ANSI_RESET}"


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

    started_at = time.perf_counter()
    logger.info("%s", _colorize(f"[FETCH] start url={url}", ANSI_CYAN))

    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(verbose=False)

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await asyncio.wait_for(
                crawler.arun(url=url, config=run_config),
                timeout=timeout,
            )

            if not result.success:
                elapsed = time.perf_counter() - started_at
                error_message = result.error_message or "Unknown error"
                logger.warning(
                    "%s",
                    _colorize(
                        f"[COMPLETE] failed url={url} elapsed={elapsed:.2f}s error={error_message}",
                        ANSI_YELLOW,
                    ),
                )
                return ScrapeResult(
                    url=url,
                    markdown="",
                    success=False,
                    error_message=error_message,
                )

            if hasattr(result.markdown, "raw_markdown"):
                markdown = result.markdown.raw_markdown
            else:
                markdown = str(result.markdown) if result.markdown else ""

            if len(markdown) > max_content_length:
                markdown = markdown[:max_content_length] + "\n\n[Content truncated]"

            elapsed = time.perf_counter() - started_at
            logger.info(
                "%s",
                _colorize(
                    f"[COMPLETE] success url={result.url or url} elapsed={elapsed:.2f}s chars={len(markdown)}",
                    ANSI_GREEN,
                ),
            )
            return ScrapeResult(
                url=result.url or url,
                markdown=markdown,
                success=True,
            )

    except TimeoutError:
        elapsed = time.perf_counter() - started_at
        logger.warning(
            "%s",
            _colorize(
                f"[COMPLETE] timeout url={url} elapsed={elapsed:.2f}s timeout={timeout:.1f}s",
                ANSI_YELLOW,
            ),
        )
        return ScrapeResult(
            url=url,
            markdown="",
            success=False,
            error_message=f"Scrape timeout after {timeout}s",
        )
    except Exception as e:
        elapsed = time.perf_counter() - started_at
        logger.error(
            "%s",
            _colorize(
                f"[COMPLETE] error url={url} elapsed={elapsed:.2f}s error={e}",
                ANSI_RED,
            ),
        )
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
