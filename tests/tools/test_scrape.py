"""Tests for Crawl4AI scraping tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.scrape import ScrapeResult, scrape, scrape_multiple

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_crawl_result_success() -> MagicMock:
    """Return a mock successful CrawlResult."""
    result = MagicMock()
    result.success = True
    result.url = "https://example.com"
    result.error_message = None
    result.markdown = MagicMock()
    result.markdown.raw_markdown = "# Test Page\n\nThis is test content."
    return result


@pytest.fixture
def mock_crawl_result_failure() -> MagicMock:
    """Return a mock failed CrawlResult."""
    result = MagicMock()
    result.success = False
    result.url = "https://example.com/404"
    result.error_message = "Page not found"
    result.markdown = None
    return result


@pytest.fixture
def mock_crawler(mock_crawl_result_success: MagicMock) -> MagicMock:
    """Return a mock AsyncWebCrawler."""
    crawler = MagicMock()
    crawler.arun = AsyncMock(return_value=mock_crawl_result_success)
    crawler.__aenter__ = AsyncMock(return_value=crawler)
    crawler.__aexit__ = AsyncMock(return_value=None)
    return crawler


# ============================================================
# Test: ScrapeResult Dataclass
# ============================================================


class TestScrapeResultDataclass:
    """Test ScrapeResult dataclass."""

    def test_create_successful_result(self) -> None:
        """ScrapeResult should be creatable for success case."""
        result = ScrapeResult(
            url="https://example.com",
            markdown="# Content",
            success=True,
        )
        assert result.url == "https://example.com"
        assert result.markdown == "# Content"
        assert result.success is True
        assert result.error_message is None

    def test_create_failed_result(self) -> None:
        """ScrapeResult should be creatable for failure case."""
        result = ScrapeResult(
            url="https://example.com",
            markdown="",
            success=False,
            error_message="Connection failed",
        )
        assert result.success is False
        assert result.error_message == "Connection failed"


# ============================================================
# Test: Input Validation
# ============================================================


class TestScrapeInputValidation:
    """Test scrape function input validation."""

    @pytest.mark.asyncio
    async def test_empty_url_raises_value_error(self) -> None:
        """Empty URL should raise ValueError."""
        with pytest.raises(ValueError, match="url"):
            await scrape("")

    @pytest.mark.asyncio
    async def test_invalid_url_raises_value_error(self) -> None:
        """Invalid URL format should raise ValueError."""
        with pytest.raises(ValueError, match="url"):
            await scrape("not-a-url")

    @pytest.mark.asyncio
    async def test_url_without_scheme_raises_value_error(self) -> None:
        """URL without http/https should raise ValueError."""
        with pytest.raises(ValueError, match="url"):
            await scrape("example.com/page")


# ============================================================
# Test: Successful Scraping
# ============================================================


class TestScrapeSuccess:
    """Test successful scraping scenarios."""

    @pytest.mark.asyncio
    async def test_scrape_returns_markdown(
        self,
        mock_crawler: MagicMock,
    ) -> None:
        """Scrape should return ScrapeResult with markdown content."""
        with patch("src.tools.scrape.AsyncWebCrawler", return_value=mock_crawler):
            result = await scrape("https://example.com")

            assert isinstance(result, ScrapeResult)
            assert result.success is True
            assert "# Test Page" in result.markdown
            assert result.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_scrape_truncates_long_content(
        self,
        mock_crawler: MagicMock,
        mock_crawl_result_success: MagicMock,
    ) -> None:
        """Scrape should truncate content exceeding max_content_length."""
        mock_crawl_result_success.markdown.raw_markdown = "A" * 1000

        with patch("src.tools.scrape.AsyncWebCrawler", return_value=mock_crawler):
            result = await scrape("https://example.com", max_content_length=100)

            # 100 chars + "\n\n[Content truncated]" (21 chars) = 121 chars
            assert len(result.markdown) <= 125


# ============================================================
# Test: Error Handling
# ============================================================


class TestScrapeErrorHandling:
    """Test scrape error handling."""

    @pytest.mark.asyncio
    async def test_failed_scrape_returns_unsuccessful_result(
        self,
        mock_crawler: MagicMock,
        mock_crawl_result_failure: MagicMock,
    ) -> None:
        """Failed scrape should return ScrapeResult with success=False."""
        mock_crawler.arun = AsyncMock(return_value=mock_crawl_result_failure)

        with patch("src.tools.scrape.AsyncWebCrawler", return_value=mock_crawler):
            result = await scrape("https://example.com/404")

            assert result.success is False
            assert result.error_message == "Page not found"
            assert result.markdown == ""

    @pytest.mark.asyncio
    async def test_timeout_returns_unsuccessful_result(
        self,
        mock_crawler: MagicMock,
    ) -> None:
        """Timeout should return ScrapeResult with success=False."""
        mock_crawler.arun = AsyncMock(side_effect=TimeoutError())

        with patch("src.tools.scrape.AsyncWebCrawler", return_value=mock_crawler):
            result = await scrape("https://example.com", timeout=1.0)

            assert result.success is False
            assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_exception_returns_unsuccessful_result(
        self,
        mock_crawler: MagicMock,
    ) -> None:
        """Unexpected exception should return ScrapeResult with success=False."""
        mock_crawler.arun = AsyncMock(side_effect=Exception("Unexpected error"))

        with patch("src.tools.scrape.AsyncWebCrawler", return_value=mock_crawler):
            result = await scrape("https://example.com")

            assert result.success is False
            assert "Unexpected error" in result.error_message


# ============================================================
# Test: Multiple URL Scraping
# ============================================================


class TestScrapeMultiple:
    """Test scrape_multiple function."""

    @pytest.mark.asyncio
    async def test_empty_urls_returns_empty_list(self) -> None:
        """Empty URL list should return empty result list."""
        results = await scrape_multiple([])
        assert results == []

    @pytest.mark.asyncio
    async def test_multiple_urls_processed(
        self,
        mock_crawler: MagicMock,
        mock_crawl_result_success: MagicMock,
    ) -> None:
        """Multiple URLs should be processed."""
        with patch("src.tools.scrape.AsyncWebCrawler", return_value=mock_crawler):
            results = await scrape_multiple(
                [
                    "https://example.com/1",
                    "https://example.com/2",
                ]
            )

            assert len(results) == 2
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_partial_failure_continues_processing(
        self,
        mock_crawler: MagicMock,
        mock_crawl_result_success: MagicMock,
        mock_crawl_result_failure: MagicMock,
    ) -> None:
        """Partial failures should not stop processing other URLs."""
        mock_crawler.arun = AsyncMock(
            side_effect=[mock_crawl_result_failure, mock_crawl_result_success]
        )

        with patch("src.tools.scrape.AsyncWebCrawler", return_value=mock_crawler):
            results = await scrape_multiple(
                [
                    "https://example.com/fail",
                    "https://example.com/success",
                ]
            )

            assert len(results) == 2
            assert results[0].success is False
            assert results[1].success is True
