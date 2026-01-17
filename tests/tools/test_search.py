"""Tests for SearXNG search tool."""

from __future__ import annotations

import asyncio

import aiohttp
import pytest
from aioresponses import aioresponses

from src.tools.search import SearchError, SearchResult, search

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_search_response() -> dict:
    """Return a mock SearXNG JSON response."""
    return {
        "query": "test",
        "number_of_results": 2,
        "results": [
            {
                "title": "Test Result 1",
                "url": "https://example.com/1",
                "content": "First result snippet",
                "engine": "google",
            },
            {
                "title": "Test Result 2",
                "url": "https://example.com/2",
                "content": "Second result snippet",
                "engine": "bing",
            },
        ],
        "suggestions": [],
        "infoboxes": [],
    }


@pytest.fixture
def empty_search_response() -> dict:
    """Return a mock empty SearXNG response."""
    return {
        "query": "no results query",
        "number_of_results": 0,
        "results": [],
        "suggestions": [],
        "infoboxes": [],
    }


# ============================================================
# Test: SearchResult Dataclass
# ============================================================


class TestSearchResultDataclass:
    """Test SearchResult dataclass."""

    def test_create_search_result_with_required_fields(self) -> None:
        """SearchResult should be creatable with required fields."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Description",
        )
        assert result.title == "Test"
        assert result.url == "https://example.com"
        assert result.snippet == "Description"
        assert result.engine is None

    def test_create_search_result_with_engine(self) -> None:
        """SearchResult should accept optional engine field."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Description",
            engine="google",
        )
        assert result.engine == "google"


# ============================================================
# Test: Input Validation
# ============================================================


class TestSearchInputValidation:
    """Test search function input validation."""

    @pytest.mark.asyncio
    async def test_empty_query_raises_value_error(self) -> None:
        """Empty query should raise ValueError."""
        with pytest.raises(ValueError, match="query"):
            await search("")

    @pytest.mark.asyncio
    async def test_whitespace_query_raises_value_error(self) -> None:
        """Whitespace-only query should raise ValueError."""
        with pytest.raises(ValueError, match="query"):
            await search("   ")


# ============================================================
# Test: Successful Search
# ============================================================


class TestSearchSuccess:
    """Test successful search scenarios."""

    @pytest.mark.asyncio
    async def test_search_returns_results(
        self,
        mock_search_response: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Search should return list of SearchResult objects."""
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")

        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8080/search?q=test&format=json",
                payload=mock_search_response,
            )

            results = await search("test")

            assert len(results) == 2
            assert isinstance(results[0], SearchResult)
            assert results[0].title == "Test Result 1"
            assert results[0].url == "https://example.com/1"
            assert results[0].snippet == "First result snippet"

    @pytest.mark.asyncio
    async def test_search_returns_empty_list_for_no_results(
        self,
        empty_search_response: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Search should return empty list when no results found."""
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")

        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8080/search?q=no+results&format=json",
                payload=empty_search_response,
            )

            results = await search("no results")

            assert results == []

    @pytest.mark.asyncio
    async def test_search_respects_num_results(
        self,
        mock_search_response: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Search should limit results to num_results."""
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")

        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8080/search?q=test&format=json",
                payload=mock_search_response,
            )

            results = await search("test", num_results=1)

            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_maps_content_to_snippet(
        self,
        mock_search_response: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Search should map 'content' field to 'snippet'."""
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")

        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8080/search?q=test&format=json",
                payload=mock_search_response,
            )

            results = await search("test")

            assert results[0].snippet == "First result snippet"
            assert results[0].engine == "google"


# ============================================================
# Test: Error Handling
# ============================================================


class TestSearchErrorHandling:
    """Test search error handling."""

    @pytest.mark.asyncio
    async def test_http_error_raises_search_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """HTTP 4xx/5xx should raise SearchError."""
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")

        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8080/search?q=test&format=json",
                status=500,
            )

            with pytest.raises(SearchError):
                await search("test")

    @pytest.mark.asyncio
    async def test_timeout_raises_search_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Connection timeout should raise SearchError."""
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")

        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8080/search?q=test&format=json",
                exception=asyncio.TimeoutError(),
            )

            with pytest.raises(SearchError, match="[Tt]imeout"):
                await search("test", timeout=1.0)

    @pytest.mark.asyncio
    async def test_invalid_json_raises_search_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Invalid JSON response should raise SearchError."""
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")

        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8080/search?q=test&format=json",
                body="not json",
                content_type="text/html",
            )

            with pytest.raises(SearchError):
                await search("test")

    @pytest.mark.asyncio
    async def test_connection_error_raises_search_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Connection error should raise SearchError."""
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")

        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8080/search?q=test&format=json",
                exception=aiohttp.ClientConnectionError("Connection refused"),
            )

            with pytest.raises(SearchError):
                await search("test")


# ============================================================
# Test: Configuration
# ============================================================


class TestSearchConfiguration:
    """Test search function uses configuration correctly."""

    @pytest.mark.asyncio
    async def test_uses_searxng_url_from_settings(
        self,
        mock_search_response: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Search should use SEARXNG_URL from settings."""
        monkeypatch.setenv("SEARXNG_URL", "http://custom:9999")

        with aioresponses() as mocked:
            mocked.get(
                "http://custom:9999/search?q=test&format=json",
                payload=mock_search_response,
            )

            results = await search("test")
            assert len(results) > 0
