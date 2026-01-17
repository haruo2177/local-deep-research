"""Tests for the Scraper node."""

from __future__ import annotations

from unittest.mock import patch

from src.tools.scrape import ScrapeResult


class TestScraperNode:
    """Tests for the scraper_node function."""

    async def test_scraper_fetches_urls(self) -> None:
        """scraper_node should fetch content from URLs."""
        from src.nodes.scraper import scraper_node

        with (
            patch("src.nodes.scraper.scrape_multiple") as mock_scrape,
            patch("src.nodes.scraper.call_llm") as mock_llm,
        ):
            mock_scrape.return_value = [
                ScrapeResult(
                    url="https://example.com/1",
                    markdown="Content from page 1",
                    success=True,
                )
            ]
            mock_llm.return_value = "Summary of content"
            state = {
                "references": ["https://example.com/1"],
                "current_search_query": "test query",
            }

            await scraper_node(state)

            mock_scrape.assert_called_once()

    async def test_scraper_summarizes_content(self) -> None:
        """scraper_node should summarize each piece of content."""
        from src.nodes.scraper import scraper_node

        with (
            patch("src.nodes.scraper.scrape_multiple") as mock_scrape,
            patch("src.nodes.scraper.call_llm") as mock_llm,
        ):
            mock_scrape.return_value = [
                ScrapeResult(
                    url="https://example.com/1",
                    markdown="Content 1",
                    success=True,
                ),
                ScrapeResult(
                    url="https://example.com/2",
                    markdown="Content 2",
                    success=True,
                ),
            ]
            mock_llm.side_effect = ["Summary 1", "Summary 2"]
            state = {
                "references": ["https://example.com/1", "https://example.com/2"],
                "current_search_query": "test query",
            }

            result = await scraper_node(state)

            assert mock_llm.call_count == 2
            assert len(result["content"]) == 2

    async def test_scraper_uses_worker_model(self) -> None:
        """scraper_node should use worker_model for summarization."""
        from src.config import settings
        from src.nodes.scraper import scraper_node

        with (
            patch("src.nodes.scraper.scrape_multiple") as mock_scrape,
            patch("src.nodes.scraper.call_llm") as mock_llm,
        ):
            mock_scrape.return_value = [
                ScrapeResult(
                    url="https://example.com/1",
                    markdown="Content",
                    success=True,
                )
            ]
            mock_llm.return_value = "Summary"
            state = {
                "references": ["https://example.com/1"],
                "current_search_query": "test",
            }

            await scraper_node(state)

            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs["model"] == settings.worker_model

    async def test_scraper_handles_scrape_failure(self) -> None:
        """scraper_node should skip failed scrapes."""
        from src.nodes.scraper import scraper_node

        with (
            patch("src.nodes.scraper.scrape_multiple") as mock_scrape,
            patch("src.nodes.scraper.call_llm") as mock_llm,
        ):
            mock_scrape.return_value = [
                ScrapeResult(
                    url="https://example.com/1",
                    markdown="",
                    success=False,
                    error_message="Connection failed",
                ),
                ScrapeResult(
                    url="https://example.com/2",
                    markdown="Valid content",
                    success=True,
                ),
            ]
            mock_llm.return_value = "Summary"
            state = {
                "references": ["https://example.com/1", "https://example.com/2"],
                "current_search_query": "test",
            }

            result = await scraper_node(state)

            assert mock_llm.call_count == 1
            assert len(result["content"]) == 1

    async def test_scraper_truncates_long_content(self) -> None:
        """scraper_node should truncate long content before summarizing."""
        from src.nodes.scraper import MAX_CONTENT_FOR_SUMMARY, scraper_node

        with (
            patch("src.nodes.scraper.scrape_multiple") as mock_scrape,
            patch("src.nodes.scraper.call_llm") as mock_llm,
        ):
            long_content = "A" * (MAX_CONTENT_FOR_SUMMARY + 1000)
            mock_scrape.return_value = [
                ScrapeResult(
                    url="https://example.com/1",
                    markdown=long_content,
                    success=True,
                )
            ]
            mock_llm.return_value = "Summary"
            state = {
                "references": ["https://example.com/1"],
                "current_search_query": "test",
            }

            await scraper_node(state)

            call_args = mock_llm.call_args[0][0]
            assert len(call_args) <= MAX_CONTENT_FOR_SUMMARY + 500

    async def test_scraper_returns_content_list(self) -> None:
        """scraper_node should return content as a list."""
        from src.nodes.scraper import scraper_node

        with (
            patch("src.nodes.scraper.scrape_multiple") as mock_scrape,
            patch("src.nodes.scraper.call_llm") as mock_llm,
        ):
            mock_scrape.return_value = [
                ScrapeResult(
                    url="https://example.com/1",
                    markdown="Content",
                    success=True,
                )
            ]
            mock_llm.return_value = "Summary"
            state = {
                "references": ["https://example.com/1"],
                "current_search_query": "test",
            }

            result = await scraper_node(state)

            assert "content" in result
            assert isinstance(result["content"], list)

    async def test_scraper_handles_empty_urls(self) -> None:
        """scraper_node should handle empty URL list."""
        from src.nodes.scraper import scraper_node

        with patch("src.nodes.scraper.scrape_multiple") as mock_scrape:
            mock_scrape.return_value = []
            state = {
                "references": [],
                "current_search_query": "test",
            }

            result = await scraper_node(state)

            assert result["content"] == []

    async def test_scraper_includes_source_in_summary(self) -> None:
        """scraper_node should include source URL in summary."""
        from src.nodes.scraper import scraper_node

        with (
            patch("src.nodes.scraper.scrape_multiple") as mock_scrape,
            patch("src.nodes.scraper.call_llm") as mock_llm,
        ):
            mock_scrape.return_value = [
                ScrapeResult(
                    url="https://example.com/test-page",
                    markdown="Content",
                    success=True,
                )
            ]
            mock_llm.return_value = "This is a summary of the content"
            state = {
                "references": ["https://example.com/test-page"],
                "current_search_query": "test",
            }

            result = await scraper_node(state)

            assert "https://example.com/test-page" in result["content"][0]
