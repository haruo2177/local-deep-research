"""Reviewer node - evaluates information sufficiency."""

from __future__ import annotations

from typing import Any


async def reviewer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate if gathered information is sufficient."""
    raise NotImplementedError("Reviewer node not yet implemented")
