"""Entry point for local-deep-research CLI."""

from __future__ import annotations

import argparse
import asyncio

from src.graph import build_graph
from src.llm import call_llm
from src.nodes.planner import planner_node
from src.prompts.templates import format_summarizer_prompt
from src.tools.scrape import scrape
from src.tools.search import search


async def run_research(task: str) -> str:
    """Run the full research pipeline.

    Args:
        task: The research topic or question.

    Returns:
        The generated research report.
    """
    graph = build_graph()

    initial_state = {
        "task": task,
        "plan": [],
        "steps_completed": 0,
        "content": [],
        "current_search_query": "",
        "references": [],
        "scraped_urls": [],
        "is_sufficient": False,
        "report": "",
    }

    result = await graph.ainvoke(initial_state)
    report: str = result.get("report", "")
    return report


async def demo_search(query: str) -> None:
    """Run search demo.

    Args:
        query: Search query to execute.
    """
    print(f"Searching for: {query}")
    print("-" * 40)
    results = await search(query, num_results=5)
    if not results:
        print("No results found.")
        return
    for r in results:
        print(f"- {r.title}")
        print(f"  {r.url}")
        if r.snippet:
            snippet = r.snippet[:100] + "..." if len(r.snippet) > 100 else r.snippet
            print(f"  {snippet}")
        print()


async def demo_scrape(url: str) -> None:
    """Run scrape demo.

    Args:
        url: URL to scrape.
    """
    print(f"Scraping: {url}")
    print("-" * 40)
    result = await scrape(url)
    if result.success:
        print(f"URL: {result.url}")
        print(f"Length: {len(result.markdown)} chars")
        print("-" * 40)
        content = result.markdown[:1000]
        print(content)
        if len(result.markdown) > 1000:
            print("\n... [truncated]")
    else:
        print(f"Failed: {result.error_message}")


async def demo_plan(task: str) -> None:
    """Run planner demo.

    Args:
        task: Research task to plan.
    """
    print(f"Planning research for: {task}")
    print("-" * 40)
    state = {"task": task}
    result = await planner_node(state)
    print("Generated search queries:")
    for i, query in enumerate(result["plan"], 1):
        print(f"  {i}. {query}")


async def demo_summarize(text: str) -> None:
    """Run summarization demo.

    Args:
        text: Text to summarize.
    """
    print("Summarizing text...")
    print("-" * 40)
    prompt = format_summarizer_prompt(text)
    summary = await call_llm(prompt)
    print("Summary:")
    print(summary)


def main() -> None:
    """Run the Deep Research agent."""
    parser = argparse.ArgumentParser(
        description="Local Deep Research - Autonomous research agent"
    )
    parser.add_argument(
        "--demo",
        choices=["search", "scrape", "plan", "summarize"],
        help="Run in demo mode to test individual components",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path for the research report",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Research topic, query, URL, or text depending on mode",
    )

    args = parser.parse_args()

    if args.demo:
        if not args.input:
            print(f"Error: --demo {args.demo} requires input")
            return

        if args.demo == "search":
            asyncio.run(demo_search(args.input))
        elif args.demo == "scrape":
            asyncio.run(demo_scrape(args.input))
        elif args.demo == "plan":
            asyncio.run(demo_plan(args.input))
        elif args.demo == "summarize":
            asyncio.run(demo_summarize(args.input))
    else:
        # Full research mode
        if not args.input:
            print("Error: Please provide a research topic")
            return

        report = asyncio.run(run_research(args.input))

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"Report saved to: {args.output}")

        print(report)


if __name__ == "__main__":
    main()
