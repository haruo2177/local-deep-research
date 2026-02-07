"""Entry point for local-deep-research CLI."""

from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import aiohttp

from src.logging_utils import preview_text

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANAGED_SERVICES = ("ollama", "searxng")
COMPOSE_BASE_FILE = "docker-compose.yaml"
COMPOSE_GPU_FILE = "docker-compose.gpu.yaml"
HEALTH_CHECK_RETRIES = 15
HEALTH_CHECK_RETRY_DELAY = 1.0
DEFAULT_FLOW_ORDER = (
    "planner",
    "translator_input",
    "researcher",
    "scraper",
    "reviewer",
    "writer",
    "translator_output",
)


class DependencyError(Exception):
    """Raised when required local services are unavailable."""


def _get_settings():
    """Lazily load global settings to avoid expensive imports at process startup."""
    from src.config import settings

    return settings


def build_graph():
    """Compatibility wrapper for lazy import."""
    from src.graph import build_graph as _build_graph

    return _build_graph()


async def call_llm(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.7,
) -> str:
    """Compatibility wrapper for lazy import."""
    from src.llm import call_llm as _call_llm

    return await _call_llm(prompt, model=model, temperature=temperature)


async def planner_node(state: dict[str, object]) -> dict[str, object]:
    """Compatibility wrapper for lazy import."""
    from src.nodes.planner import planner_node as _planner_node

    return await _planner_node(state)


async def search(
    query: str,
    *,
    num_results: int = 10,
    timeout: float = 10.0,
):
    """Compatibility wrapper for lazy import."""
    from src.tools.search import search as _search

    return await _search(query, num_results=num_results, timeout=timeout)


async def scrape(url: str):
    """Compatibility wrapper for lazy import."""
    from src.tools.scrape import scrape as _scrape

    return await _scrape(url)


def _is_nvidia_runtime_error(message: str) -> bool:
    """Return True when docker compose failed because NVIDIA runtime is unavailable."""
    normalized = message.lower()
    return (
        'could not select device driver "nvidia"' in normalized
        and "capabilities: [[gpu]]" in normalized
    )


def _run_compose(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run docker compose command in project root."""
    command = ["docker", "compose", *args]
    try:
        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise DependencyError(
            "`docker` command was not found. Please install Docker and Docker Compose."
        ) from e
    except subprocess.CalledProcessError as e:
        details = (e.stderr or e.stdout or "").strip()
        if details:
            raise DependencyError(
                f"Failed to run `{' '.join(command)}`: {details}"
            ) from e
        raise DependencyError(f"Failed to run `{' '.join(command)}`.") from e


def start_required_services() -> None:
    """Start required services."""
    logger.info("Starting services: %s", ", ".join(MANAGED_SERVICES))
    gpu_args = [
        "-f",
        COMPOSE_BASE_FILE,
        "-f",
        COMPOSE_GPU_FILE,
        "up",
        "-d",
        *MANAGED_SERVICES,
    ]
    cpu_args = ["-f", COMPOSE_BASE_FILE, "up", "-d", *MANAGED_SERVICES]
    try:
        _run_compose(gpu_args)
        logger.info(
            "Services started with GPU configuration: %s",
            ", ".join(MANAGED_SERVICES),
        )
    except DependencyError as e:
        if not _is_nvidia_runtime_error(str(e)):
            raise
        logger.warning(
            "NVIDIA GPU runtime is unavailable. Falling back to CPU configuration."
        )
        _run_compose(cpu_args)
        logger.info(
            "Services started with CPU fallback: %s",
            ", ".join(MANAGED_SERVICES),
        )


def stop_required_services() -> None:
    """Stop required services."""
    logger.info("Stopping services: %s", ", ".join(MANAGED_SERVICES))
    _run_compose(["-f", COMPOSE_BASE_FILE, "stop", *MANAGED_SERVICES])
    logger.info("Services stopped: %s", ", ".join(MANAGED_SERVICES))


def configure_logging() -> None:
    """Configure root logger with timestamped output once."""
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def _check_service(
    *,
    service_name: str,
    url: str,
    hint: str,
    timeout: float = 3.0,
) -> None:
    """Check service availability via HTTP GET."""
    logger.info("Health check start service=%s url=%s", service_name, url)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status >= 400:
                    raise DependencyError(
                        f"{service_name} returned HTTP {response.status} at {url}. {hint}"
                    )
        logger.info("Health check ok service=%s", service_name)
    except TimeoutError as e:
        raise DependencyError(
            f"{service_name} timed out at {url}. {hint}"
        ) from e
    except aiohttp.ClientConnectionError as e:
        raise DependencyError(
            f"{service_name} connection error at {url}. {hint}"
        ) from e
    except aiohttp.ClientError as e:
        raise DependencyError(f"{service_name} check failed at {url}: {e}") from e


async def _check_service_with_retries(
    *,
    service_name: str,
    url: str,
    hint: str,
    timeout: float = 3.0,
    retries: int = HEALTH_CHECK_RETRIES,
    retry_delay: float = HEALTH_CHECK_RETRY_DELAY,
) -> None:
    """Check service availability with retries for startup race conditions."""
    last_error: DependencyError | None = None
    for attempt in range(1, retries + 1):
        try:
            await _check_service(
                service_name=service_name,
                url=url,
                hint=hint,
                timeout=timeout,
            )
            return
        except DependencyError as e:
            last_error = e
            if attempt == retries:
                break
            logger.info(
                "Health check retry service=%s attempt=%s/%s wait=%.1fs",
                service_name,
                attempt,
                retries,
                retry_delay,
            )
            await asyncio.sleep(retry_delay)

    if last_error is not None:
        raise last_error


def _required_ollama_models() -> list[str]:
    """Return required Ollama model names in stable order without duplicates."""
    settings = _get_settings()
    ordered_models = [
        settings.planner_model,
        settings.worker_model,
        settings.writer_model,
    ]
    required: list[str] = []
    seen: set[str] = set()
    for model in ordered_models:
        if model and model not in seen:
            seen.add(model)
            required.append(model)
    return required


async def _fetch_ollama_model_names(
    *,
    ollama_base: str,
    timeout: float = 5.0,
) -> set[str]:
    """Fetch available Ollama model names from /api/tags."""
    url = f"{ollama_base.rstrip('/')}/api/tags"
    logger.info("Checking Ollama models at %s", url)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status >= 400:
                    raise DependencyError(
                        "Failed to fetch Ollama models "
                        f"(HTTP {response.status}) at {url}."
                    )
                payload = await response.json()
    except TimeoutError as e:
        raise DependencyError(f"Ollama model list request timed out at {url}.") from e
    except aiohttp.ClientConnectionError as e:
        raise DependencyError(
            f"Ollama model list connection error at {url}."
        ) from e
    except aiohttp.ClientError as e:
        raise DependencyError(f"Ollama model list check failed at {url}: {e}") from e

    models = payload.get("models", [])
    names: set[str] = set()
    for model in models:
        if isinstance(model, dict):
            name = model.get("name")
            if isinstance(name, str) and name:
                names.add(name)
    logger.info("Detected %s Ollama models", len(names))
    return names


async def _check_required_ollama_models(*, ollama_base: str) -> None:
    """Verify required Ollama models are available locally."""
    required = _required_ollama_models()
    available = await _fetch_ollama_model_names(ollama_base=ollama_base)
    missing = [model for model in required if model not in available]
    if not missing:
        return

    pull_commands = [f"docker exec ollama ollama pull {model}" for model in missing]
    copy_paste_command = (
        f"docker compose -f {COMPOSE_BASE_FILE} up -d ollama && "
        + " && ".join(pull_commands)
    )
    logger.warning("Missing Ollama models: %s", ", ".join(missing))
    raise DependencyError(
        "Missing Ollama models: "
        f"{', '.join(missing)}.\n"
        "Copy and run this command, then retry:\n"
        f"{copy_paste_command}"
    )


async def validate_runtime_dependencies() -> None:
    """Validate required local services before running full research."""
    settings = _get_settings()
    ollama_base = settings.ollama_url.rstrip("/")
    searxng_base = settings.searxng_url.rstrip("/")
    logger.info("Validating runtime dependencies")

    await _check_service_with_retries(
        service_name="Ollama",
        url=f"{ollama_base}/api/tags",
        hint="Ensure Docker is running and Ollama container is healthy.",
    )
    await _check_service_with_retries(
        service_name="SearXNG",
        url=f"{searxng_base}/healthz",
        hint="Ensure Docker is running and SearXNG container is healthy.",
    )
    await _check_required_ollama_models(ollama_base=ollama_base)
    logger.info("Runtime dependencies are ready")


async def run_research(task: str) -> str:
    """Run the full research pipeline.

    Args:
        task: The research topic or question.

    Returns:
        The generated research report.
    """
    configure_logging()
    start_time = time.perf_counter()
    logger.info("Research start task=%s", task)
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
        "source_language": "",
        "original_task": "",
        "empty_cycles": 0,
        "empty_cycle_streak": 0,
        "node_timing_events": [],
    }

    result = await graph.ainvoke(initial_state)
    report: str = result.get("report", "")
    steps = result.get("steps_completed", 0)
    source_language = result.get("source_language", "")
    current_task = result.get("task", "")
    original_task = result.get("original_task", "")
    elapsed = time.perf_counter() - start_time
    logger.info(
        "Research context source_language=%s original_task=%s current_task=%s",
        source_language,
        preview_text(str(original_task), max_chars=120),
        preview_text(str(current_task), max_chars=120),
    )
    logger.info("Research final report preview=%s", preview_text(report))
    _log_flow_timing_summary(result.get("node_timing_events", []))
    logger.info("Research end task=%s steps=%s elapsed=%.2fs", task, steps, elapsed)
    return report


def _log_flow_timing_summary(events: list[dict[str, object]]) -> None:
    """Log per-flow timing summary aggregated across the whole run."""
    if not events:
        logger.info("Flow timings summary: no events captured")
        return

    total_by_node: dict[str, float] = defaultdict(float)
    calls_by_node: dict[str, int] = defaultdict(int)

    for event in events:
        node = event.get("node", "unknown")
        elapsed = float(event.get("elapsed_seconds", 0.0))
        total_by_node[node] += elapsed
        calls_by_node[node] += 1

    logger.info("Flow timings summary start")
    logged_nodes: set[str] = set()
    for node in DEFAULT_FLOW_ORDER:
        if node not in total_by_node:
            continue
        total = total_by_node[node]
        calls = calls_by_node[node]
        avg = total / calls if calls else 0.0
        logger.info(
            "Flow timing summary node=%s total=%.2fs calls=%s avg=%.2fs",
            node,
            total,
            calls,
            avg,
        )
        logged_nodes.add(node)

    for node in sorted(total_by_node):
        if node in logged_nodes:
            continue
        total = total_by_node[node]
        calls = calls_by_node[node]
        avg = total / calls if calls else 0.0
        logger.info(
            "Flow timing summary node=%s total=%.2fs calls=%s avg=%.2fs",
            node,
            total,
            calls,
            avg,
        )

    total_runtime = sum(total_by_node.values())
    logger.info("Flow timings summary end total_node_time=%.2fs", total_runtime)


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
    from src.prompts.templates import format_summarizer_prompt

    prompt = format_summarizer_prompt(text)
    summary = await call_llm(prompt)
    print("Summary:")
    print(summary)


def demo_translate(text: str) -> None:
    """Run translation demo.

    Args:
        text: Text to translate.
    """
    from src.tools.translate import (
        detect_language,
        normalize_language_code,
        translate_from_english,
        translate_to_english,
    )

    settings = _get_settings()
    print(f"Device: {settings.translation_device}")
    print("-" * 40)

    # Detect language
    source_lang = detect_language(text)
    normalized = normalize_language_code(source_lang)
    print(f"Input: {text}")
    print(f"Detected language: {source_lang} (normalized: {normalized})")
    print("-" * 40)

    if normalized == "en":
        # English to Japanese demo
        print("Translating English -> Japanese...")
        result = translate_from_english(text, "ja")
        print(f"Result: {result.translated_text}")
    else:
        # Non-English to English
        print(f"Translating {source_lang} -> English...")
        result = translate_to_english(text, source_lang)
        print(f"Result: {result.translated_text}")

        # Then back to original
        print(f"\nTranslating English -> {source_lang}...")
        back = translate_from_english(result.translated_text, normalized)
        print(f"Result: {back.translated_text}")


def main() -> None:
    """Run the Deep Research agent."""
    configure_logging()
    parser = argparse.ArgumentParser(
        description="Local Deep Research - Autonomous research agent"
    )
    parser.add_argument(
        "--demo",
        choices=["search", "scrape", "plan", "summarize", "translate"],
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
        elif args.demo == "translate":
            demo_translate(args.input)
    else:
        # Full research mode
        if not args.input:
            print("Error: Please provide a research topic")
            return

        services_started = False
        try:
            start_required_services()
            services_started = True
            asyncio.run(validate_runtime_dependencies())
            logger.info("Running full research pipeline")
            report = asyncio.run(run_research(args.input))
        except DependencyError as e:
            print(f"Error: {e}")
            return
        except Exception:
            logger.exception("Unexpected error during research execution")
            raise
        finally:
            if services_started:
                try:
                    stop_required_services()
                except DependencyError as e:
                    print(f"Warning: Failed to stop services: {e}")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"Report saved to: {args.output}")

        print(report)


if __name__ == "__main__":
    main()
