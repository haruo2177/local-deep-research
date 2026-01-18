"""LangGraph workflow definition."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from src.nodes.planner import planner_node
from src.nodes.researcher import researcher_node
from src.nodes.reviewer import reviewer_node, should_continue_research
from src.nodes.scraper import scraper_node
from src.nodes.writer import writer_node
from src.state import ResearchState


def build_graph() -> Any:
    """Build and return the research workflow graph.

    The graph implements the following workflow:
    START → Planner → Researcher → Scraper → Reviewer
                          ↑                      │
                          └── not sufficient ────┘
                                                 │
                                           sufficient
                                                 ↓
                                             Writer → END

    Returns:
        A compiled StateGraph ready for execution.
    """
    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("planner", planner_node)  # type: ignore[type-var]
    graph.add_node("researcher", researcher_node)  # type: ignore[type-var]
    graph.add_node("scraper", scraper_node)  # type: ignore[type-var]
    graph.add_node("reviewer", reviewer_node)  # type: ignore[type-var]
    graph.add_node("writer", writer_node)  # type: ignore[type-var]

    # Add edges
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "scraper")
    graph.add_edge("scraper", "reviewer")

    # Conditional edge from reviewer
    graph.add_conditional_edges(
        "reviewer",
        should_continue_research,
        {"researcher": "researcher", "writer": "writer"},
    )

    graph.add_edge("writer", END)

    return graph.compile()
