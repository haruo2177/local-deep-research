"""Logging helpers for compact intermediate progress output."""

from __future__ import annotations


def preview_text(text: str, *, max_chars: int = 220) -> str:
    """Return a single-line preview string suitable for logs."""
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars]}..."

