"""Helper functions for code review analysis.

Module-level utility functions used by CodeReviewAnalysisMixin
for static analysis, file snippet gathering, and LLM response parsing.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Quality check thresholds
MAX_FILE_LINES = 500
CHARS_PER_TOKEN_ESTIMATE = 4


def _has_return_type_hint(content: str, func_start: int) -> bool:
    """Check if a function definition has a return type hint.

    Uses parenthesis depth tracking to find the closing paren,
    then checks for ``->`` between ``)`` and the body colon.

    Args:
        content: Full file content string.
        func_start: Character offset of the ``def`` keyword.

    Returns:
        True if the function has a ``-> ...`` return type annotation.

    """
    open_paren = content.find("(", func_start)
    if open_paren == -1:
        return True  # Can't determine, assume OK
    depth = 1
    pos = open_paren + 1
    while pos < len(content) and depth > 0:
        if content[pos] == "(":
            depth += 1
        elif content[pos] == ")":
            depth -= 1
        pos += 1
    if depth != 0:
        return True  # Malformed, assume OK
    colon_pos = content.find(":", pos)
    if colon_pos == -1:
        return True
    return "->" in content[pos:colon_pos]


def _gather_file_snippets(
    findings: list[dict],
    context_lines: int = 3,
) -> dict[str, dict[int, str]]:
    """Read source files and extract snippet context around each finding.

    Args:
        findings: List of finding dicts with ``file`` and ``line`` keys.
        context_lines: Number of lines to include above/below the finding.

    Returns:
        Dict mapping file path to {line_num: snippet_text}.

    """
    snippets: dict[str, dict[int, str]] = {}
    file_cache: dict[str, list[str]] = {}
    for finding in findings:
        fpath = finding.get("file", "")
        line_num = finding.get("line")
        if not fpath or not line_num:
            continue
        if fpath not in file_cache:
            try:
                file_cache[fpath] = Path(fpath).read_text(errors="ignore").splitlines()
                snippets[fpath] = {}
            except OSError:
                continue
        file_lines = file_cache[fpath]
        start = max(0, line_num - 1 - context_lines)
        end = min(len(file_lines), line_num + context_lines)
        snippet = "\n".join(f"  {i + 1}: {file_lines[i]}" for i in range(start, end))
        snippets[fpath][line_num] = snippet
    return snippets


def _format_findings_for_prompt(
    findings: list[dict],
    snippets: dict[str, dict[int, str]],
) -> str:
    """Format findings and their code snippets into a prompt string.

    Args:
        findings: List of finding dicts.
        snippets: Output from ``_gather_file_snippets()``.

    Returns:
        Formatted string for inclusion in an LLM prompt.

    """
    parts: list[str] = []
    for i, finding in enumerate(findings):
        fpath = finding.get("file", "?")
        line_num = finding.get("line", "?")
        desc = finding.get("description", "")
        ftype = finding.get("type", "unknown")
        severity = finding.get("severity", finding.get("impact", "unknown"))
        parts.append(f"[{i}] {ftype} ({severity}) at {fpath}:{line_num}\n    {desc}")
        snippet = snippets.get(fpath, {}).get(line_num)
        if snippet:
            parts.append(f"    Code context:\n{snippet}")
        parts.append("")
    return "\n".join(parts)


def _parse_deep_enrichment(
    response: str,
    original_findings: list[dict],
) -> list[dict]:
    """Parse LLM JSON response and merge enrichment into findings.

    Gracefully handles malformed responses by keeping original findings
    unchanged when parsing fails.

    Args:
        response: Raw LLM response (expected JSON with ``findings`` key).
        original_findings: Original finding dicts from CHEAP stage.

    Returns:
        List of enriched finding dicts with added keys:
        ``validated``, ``false_positive``, ``suggestion``.

    """
    import json as _json

    enriched = [dict(f) for f in original_findings]  # shallow copy each

    try:
        # Try to extract JSON from response
        text = response.strip()
        # Handle markdown code blocks
        if "```" in text:
            start = text.find("```")
            end = text.rfind("```")
            if start != end:
                inner = text[start:end]
                # Remove opening fence line
                inner = inner.split("\n", 1)[1] if "\n" in inner else inner
                text = inner.strip()

        data = _json.loads(text)
        llm_findings = data.get("findings", [])

        for item in llm_findings:
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(enriched):
                enriched[idx]["validated"] = item.get("validated", True)
                enriched[idx]["false_positive"] = item.get("false_positive", False)
                if "suggestion" in item:
                    enriched[idx]["suggestion"] = item["suggestion"]
                if "severity" in item:
                    # Allow severity adjustment but preserve original key name
                    sev_key = "severity" if "severity" in enriched[idx] else "impact"
                    enriched[idx][sev_key] = item["severity"]
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("Could not parse deep enrichment response: %s", e)
        # Return originals with validated=True (assume valid if can't parse)
        for f in enriched:
            f["validated"] = True
            f["false_positive"] = False

    return enriched


def _recount_by_key(findings: list[dict], key: str) -> dict[str, int]:
    """Recount findings by a grouping key, excluding false positives.

    Args:
        findings: List of finding dicts (may include ``false_positive`` flag).
        key: Key to group by (``"severity"`` or ``"impact"``).

    Returns:
        Dict mapping key values to counts, e.g. ``{"high": 2, "medium": 1, "low": 0}``.

    """
    counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        if f.get("false_positive", False):
            continue
        val = f.get(key, "low")
        counts[val] = counts.get(val, 0) + 1
    return counts
