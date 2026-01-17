"""Prompt templates for the research workflow."""

from __future__ import annotations

PLANNER_PROMPT = """You are a research planner. Given a user query, generate a list of search queries to gather comprehensive information.

User Query: {task}

IMPORTANT: Your response must be ONLY a valid JSON object, no other text.
The JSON must have this exact format:
{{"queries": ["query1", "query2", ...]}}

Generate 3-5 specific search queries that will help answer the user's question.
"""

SUMMARIZER_PROMPT = """Summarize the following content concisely in {max_length} words or less.
Focus on the key facts and information relevant to research.

Content:
{content}
"""

REVIEWER_PROMPT = """Evaluate if the following information is sufficient to answer the query.

Query: {task}

Information gathered:
{content}

Respond with a JSON object:
{{"sufficient": true or false, "reason": "brief explanation"}}
"""

WRITER_PROMPT = """Write a comprehensive research report based on the gathered information.

Query: {task}

Information:
{content}

References:
{references}

Write a well-structured report in Markdown format with:
1. A clear introduction
2. Main findings organized by topic
3. A conclusion
4. Properly cited references
"""


def format_planner_prompt(task: str) -> str:
    """Format the planner prompt with the given task.

    Args:
        task: The user's research question or topic.

    Returns:
        The formatted prompt string.

    Raises:
        ValueError: If task is empty or whitespace-only.
    """
    if not task or not task.strip():
        raise ValueError("task cannot be empty")
    return PLANNER_PROMPT.format(task=task)


def format_summarizer_prompt(content: str, max_length: int = 500) -> str:
    """Format the summarizer prompt with the given content.

    Args:
        content: The content to summarize.
        max_length: Maximum length of the summary in words.

    Returns:
        The formatted prompt string.
    """
    return SUMMARIZER_PROMPT.format(content=content, max_length=max_length)


def format_reviewer_prompt(task: str, content: list[str]) -> str:
    """Format the reviewer prompt with task and gathered content.

    Args:
        task: The original research question.
        content: List of summaries gathered during research.

    Returns:
        The formatted prompt string.
    """
    content_text = "\n\n".join(content)
    return REVIEWER_PROMPT.format(task=task, content=content_text)


def format_writer_prompt(
    task: str, content: list[str], references: list[str]
) -> str:
    """Format the writer prompt for final report generation.

    Args:
        task: The original research question.
        content: List of summaries gathered during research.
        references: List of source URLs.

    Returns:
        The formatted prompt string.
    """
    content_text = "\n\n".join(content)
    if references:
        references_text = "\n".join(f"- {url}" for url in references)
    else:
        references_text = "(No references available)"
    return WRITER_PROMPT.format(
        task=task, content=content_text, references=references_text
    )
