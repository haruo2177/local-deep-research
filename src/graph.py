"""LangGraph workflow definition."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.nodes.planner import planner_node
from src.nodes.researcher import researcher_node
from src.nodes.reviewer import reviewer_node, should_continue_research
from src.nodes.scraper import scraper_node
from src.nodes.translator import translator_input_node, translator_output_node
from src.nodes.writer import writer_node
from src.state import ResearchState

logger = logging.getLogger(__name__)


NodeFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def _with_timing(node_name: str, node_fn: NodeFn) -> NodeFn:
    """Wrap a node function and append timing events into state updates."""

    async def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        started_at = time.perf_counter()
        result = await node_fn(state)
        elapsed = time.perf_counter() - started_at

        update = dict(result)
        events = list(update.get("node_timing_events", []))
        events.append({"node": node_name, "elapsed_seconds": elapsed})
        update["node_timing_events"] = events

        logger.info("Flow timing node=%s elapsed=%.2fs", node_name, elapsed)
        return update

    return wrapped


def build_graph() -> Any:
    """Build and return the research workflow graph.

    The graph implements the following workflow (with translation):
    START → Planner → TranslatorInput → Researcher → Scraper → Reviewer
                            ↑                                      │
                            └────────── not sufficient ────────────┘
                                                                   │
                                                             sufficient
                                                                   ↓
                                              Writer → TranslatorOutput → END

    Returns:
        A compiled StateGraph ready for execution.
    """
    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("planner", _with_timing("planner", planner_node))  # type: ignore[type-var]
    graph.add_node("translator_input", _with_timing("translator_input", translator_input_node))  # type: ignore[type-var]
    graph.add_node("researcher", _with_timing("researcher", researcher_node))  # type: ignore[type-var]
    graph.add_node("scraper", _with_timing("scraper", scraper_node))  # type: ignore[type-var]
    graph.add_node("reviewer", _with_timing("reviewer", reviewer_node))  # type: ignore[type-var]
    graph.add_node("writer", _with_timing("writer", writer_node))  # type: ignore[type-var]
    graph.add_node("translator_output", _with_timing("translator_output", translator_output_node))  # type: ignore[type-var]

    # Add edges
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "translator_input")
    graph.add_edge("translator_input", "researcher")
    graph.add_edge("researcher", "scraper")
    graph.add_edge("scraper", "reviewer")

    # Conditional edge from reviewer
    graph.add_conditional_edges(
        "reviewer",
        should_continue_research,
        {"researcher": "researcher", "writer": "writer"},
    )

    graph.add_edge("writer", "translator_output")
    graph.add_edge("translator_output", END)

    return graph.compile()
