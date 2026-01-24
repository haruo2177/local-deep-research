"""Configuration management for local-deep-research."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _detect_device() -> str:
    """Detect the best available device for translation.

    Returns:
        "cuda" if GPU is available, otherwise "cpu".
    """
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


@dataclass
class Settings:
    """Application settings with environment variable support."""

    ollama_url: str = field(default="")
    searxng_url: str = field(default="")
    planner_model: str = field(default="")
    worker_model: str = field(default="")
    max_context_length: int = field(default=4096)
    max_iterations: int = field(default=5)
    # Translation settings
    enable_translation: bool = field(default=True)
    translation_device: str = field(default="auto")

    def __post_init__(self) -> None:
        """Load settings from environment variables."""
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8080")
        self.planner_model = os.getenv("PLANNER_MODEL", "deepseek-r1:7b")
        self.worker_model = os.getenv("WORKER_MODEL", "qwen2.5:3b")
        self.max_context_length = int(os.getenv("MAX_CONTEXT_LENGTH", "4096"))
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", "5"))
        # Translation settings
        self.enable_translation = (
            os.getenv("ENABLE_TRANSLATION", "true").lower() == "true"
        )
        device_setting = os.getenv("TRANSLATION_DEVICE", "auto")
        # Auto-detect GPU if "auto" is specified
        self.translation_device = (
            _detect_device() if device_setting == "auto" else device_setting
        )


# Global settings instance
settings = Settings()
