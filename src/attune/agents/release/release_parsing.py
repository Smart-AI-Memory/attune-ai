"""Response parsing for Release Preparation Agent Team.

Multi-strategy parsing for LLM and tool output responses.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import re
from typing import Any


def _parse_response(text: str) -> dict[str, Any]:
    """Parse agent response using multiple strategies.

    Tries in order:
    1. XML-delimited (<analysis>...</analysis>)
    2. Markdown-fenced (```json...```)
    3. Raw JSON (starts with {)
    4. Regex metric extraction (last resort)

    Never returns None — always returns a dict with at least empty defaults.

    Args:
        text: Raw response text from LLM or tool output

    Returns:
        Parsed dict with findings

    """
    if not text or not text.strip():
        return {"parse_error": "empty response"}

    text = text.strip()

    # Strategy 1: XML delimiters
    xml_match = re.search(r"<analysis>([\s\S]*?)</analysis>", text)
    if xml_match:
        try:
            return json.loads(xml_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 2: Markdown-fenced JSON
    md_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if md_match:
        try:
            return json.loads(md_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Raw JSON
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Strategy 4: Regex metric extraction (last resort)
    result: dict[str, Any] = {}

    # Try to find score patterns
    score_match = re.search(r"(?:score|quality)[:\s]+(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if score_match:
        result["score"] = float(score_match.group(1))

    # Try to find coverage patterns
    cov_match = re.search(r"(?:coverage)[:\s]+(\d+(?:\.\d+)?)\s*%?", text, re.IGNORECASE)
    if cov_match:
        result["coverage_percent"] = float(cov_match.group(1))

    # Try to find issue count patterns
    issues_match = re.search(
        r"(\d+)\s+(?:critical|high)\s+(?:issue|finding|vuln)",
        text,
        re.IGNORECASE,
    )
    if issues_match:
        result["critical_issues"] = int(issues_match.group(1))

    if result:
        result["parse_method"] = "regex"
        return result

    return {"parse_error": "no parseable content", "raw_text": text[:500]}
