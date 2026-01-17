"""Tests for configuration management."""

from __future__ import annotations

import pytest


class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_ollama_url(self) -> None:
        """Config should have a default Ollama URL."""
        from src.config import Settings

        settings = Settings()
        assert settings.ollama_url == "http://localhost:11434"

    def test_default_searxng_url(self) -> None:
        """Config should have a default SearXNG URL."""
        from src.config import Settings

        settings = Settings()
        assert settings.searxng_url == "http://localhost:8080"

    def test_default_planner_model(self) -> None:
        """Config should have a default planner model."""
        from src.config import Settings

        settings = Settings()
        assert settings.planner_model == "deepseek-r1:7b"

    def test_default_worker_model(self) -> None:
        """Config should have a default worker model."""
        from src.config import Settings

        settings = Settings()
        assert settings.worker_model == "qwen2.5:3b"


class TestConfigFromEnvironment:
    """Test configuration from environment variables."""

    def test_ollama_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Config should read OLLAMA_URL from environment."""
        monkeypatch.setenv("OLLAMA_URL", "http://custom:11434")

        from src.config import Settings

        settings = Settings()
        assert settings.ollama_url == "http://custom:11434"

    def test_searxng_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Config should read SEARXNG_URL from environment."""
        monkeypatch.setenv("SEARXNG_URL", "http://custom:8080")

        from src.config import Settings

        settings = Settings()
        assert settings.searxng_url == "http://custom:8080"


class TestConfigValidation:
    """Test configuration validation."""

    def test_max_context_length_positive(self) -> None:
        """Max context length must be positive."""
        from src.config import Settings

        settings = Settings()
        assert settings.max_context_length > 0

    def test_max_iterations_positive(self) -> None:
        """Max iterations must be positive."""
        from src.config import Settings

        settings = Settings()
        assert settings.max_iterations > 0
