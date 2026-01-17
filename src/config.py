"""Configuration management for local-deep-research."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings with environment variable support."""

    ollama_url: str = field(default="")
    searxng_url: str = field(default="")
    planner_model: str = field(default="")
    worker_model: str = field(default="")
    max_context_length: int = field(default=4096)
    max_iterations: int = field(default=5)

    def __post_init__(self) -> None:
        """Load settings from environment variables."""
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8080")
        self.planner_model = os.getenv("PLANNER_MODEL", "deepseek-r1:7b")
        self.worker_model = os.getenv("WORKER_MODEL", "qwen2.5:3b")
        self.max_context_length = int(os.getenv("MAX_CONTEXT_LENGTH", "4096"))
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", "5"))


# Global settings instance
settings = Settings()
