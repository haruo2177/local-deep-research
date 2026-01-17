"""Shared pytest fixtures for local-deep-research tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    pass


# ============================================================
# Configuration Fixtures
# ============================================================


@pytest.fixture
def mock_ollama_url() -> str:
    """Return the default Ollama URL for testing."""
    return "http://localhost:11434"


@pytest.fixture
def mock_searxng_url() -> str:
    """Return the default SearXNG URL for testing."""
    return "http://localhost:8080"


@pytest.fixture
def mock_config(mock_ollama_url: str, mock_searxng_url: str) -> dict[str, str]:
    """Return a mock configuration dictionary."""
    return {
        "ollama_url": mock_ollama_url,
        "searxng_url": mock_searxng_url,
        "planner_model": "deepseek-r1:7b",
        "worker_model": "qwen2.5:3b",
        "max_context_length": "4096",
    }


# ============================================================
# State Fixtures
# ============================================================


@pytest.fixture
def empty_research_state() -> dict[str, object]:
    """Return an empty research state for testing."""
    return {
        "task": "",
        "plan": [],
        "steps_completed": 0,
        "content": [],
        "current_search_query": "",
        "references": [],
        "is_sufficient": False,
    }


@pytest.fixture
def sample_research_state() -> dict[str, object]:
    """Return a sample research state with test data."""
    return {
        "task": "What is LangGraph?",
        "plan": [
            "Search for LangGraph documentation",
            "Find LangGraph tutorials",
            "Look for LangGraph examples",
        ],
        "steps_completed": 1,
        "content": [
            "LangGraph is a library for building stateful, multi-actor applications with LLMs."
        ],
        "current_search_query": "LangGraph tutorials",
        "references": ["https://docs.langchain.com/langgraph"],
        "is_sufficient": False,
    }


# ============================================================
# Mock LLM Fixtures
# ============================================================


@pytest.fixture
def mock_llm_response() -> MagicMock:
    """Return a mock LLM response object."""
    mock = MagicMock()
    mock.content = '{"queries": ["query1", "query2"]}'
    return mock


@pytest.fixture
def mock_llm() -> MagicMock:
    """Return a mock LLM client."""
    mock = MagicMock()
    mock.invoke = MagicMock(return_value=MagicMock(content="Mock response"))
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="Mock async response"))
    return mock


# ============================================================
# Search Fixtures
# ============================================================


@pytest.fixture
def sample_search_results() -> list[dict[str, str]]:
    """Return sample search results for testing."""
    return [
        {
            "title": "LangGraph Documentation",
            "url": "https://docs.langchain.com/langgraph",
            "snippet": "LangGraph is a library for building stateful applications.",
        },
        {
            "title": "LangGraph Tutorial",
            "url": "https://example.com/langgraph-tutorial",
            "snippet": "Learn how to use LangGraph step by step.",
        },
    ]


# ============================================================
# Scraping Fixtures
# ============================================================


@pytest.fixture
def sample_html_content() -> str:
    """Return sample HTML content for scraping tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Welcome to the Test Page</h1>
        <p>This is a paragraph with important information.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
    </body>
    </html>
    """
