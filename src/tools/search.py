"""SearXNG search tool."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import aiohttp

from src.config import Settings


@dataclass
class SearchResult:
    """A single search result from SearXNG."""

    title: str
    url: str
    snippet: str
    engine: str | None = None


class SearchError(Exception):
    """Exception raised when search fails."""

    pass


async def search(
    query: str,
    *,
    num_results: int = 10,
    timeout: float = 10.0,
) -> list[SearchResult]:
    """Search using SearXNG and return results.

    Args:
        query: The search query string.
        num_results: Maximum number of results to return.
        timeout: Request timeout in seconds.

    Returns:
        List of SearchResult objects.

    Raises:
        SearchError: If the search request fails.
        ValueError: If query is empty.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")

    settings = Settings()
    base_url = settings.searxng_url

    params = {
        "q": query.strip(),
        "format": "json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status >= 400:
                    raise SearchError(f"Search failed with status {response.status}")

                try:
                    data = await response.json()
                except Exception as e:
                    raise SearchError(f"Failed to parse response: {e}") from e

                results = []
                for item in data.get("results", [])[:num_results]:
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("content", ""),
                            engine=item.get("engine"),
                        )
                    )

                return results

    except asyncio.TimeoutError as e:
        raise SearchError(f"Search timeout after {timeout}s") from e
    except aiohttp.ClientConnectionError as e:
        raise SearchError(f"Connection error: {e}") from e
