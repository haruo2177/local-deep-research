"""Prompt templates for the research workflow."""

from __future__ import annotations

PLANNER_PROMPT = """You are a research planner. Given a user query, generate a list of search queries.

User Query: {task}

Output a JSON object with a "queries" key containing a list of search queries.
"""

SUMMARIZER_PROMPT = """Summarize the following content concisely:

{content}
"""

REVIEWER_PROMPT = """Evaluate if the following information is sufficient to answer the query.

Query: {task}

Information gathered:
{content}

Is this sufficient? Answer with "yes" or "no" and explain why.
"""

WRITER_PROMPT = """Write a comprehensive research report based on the gathered information.

Query: {task}

Information:
{content}

References:
{references}

Write a well-structured report with citations.
"""
