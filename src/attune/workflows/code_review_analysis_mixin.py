"""Code review analysis mixin — static and LLM-enriched analysis stages.

Extracted from code_review.py for maintainability (keeps each file
under the 1 000-line guideline).

Contains:
    Module-level helpers:
        _has_return_type_hint, _gather_file_snippets,
        _format_findings_for_prompt, _parse_deep_enrichment, _recount_by_key

    CodeReviewAnalysisMixin:
        _perf_check        — CHEAP static regex scan for perf anti-patterns
        _perf_check_deep   — CAPABLE LLM validation of perf findings
        _health_monitor    — CHEAP framework health snapshot (no LLM)
        _quality_check     — CHEAP static regex scan for quality issues
        _quality_check_deep— CAPABLE LLM validation of quality findings

Expected host attributes (provided by BaseWorkflow / its mixins):
    _call_llm : async method  (from LLMMixin)
    logger    : logging.Logger (set by BaseWorkflow.__init__)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Quality check thresholds
MAX_FILE_LINES = 500
CHARS_PER_TOKEN_ESTIMATE = 4


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


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
        parts.append(f"[{i}] {ftype} ({severity}) at {fpath}:{line_num}\n" f"    {desc}")
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
        logger.warning(f"Could not parse deep enrichment response: {e}")
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


# ---------------------------------------------------------------------------
# Mixin class
# ---------------------------------------------------------------------------


class CodeReviewAnalysisMixin:
    """Analysis stages for CodeReviewWorkflow.

    Provides five stages that run as part of the code-review pipeline:

    * ``_perf_check`` / ``_perf_check_deep`` — performance anti-pattern detection
    * ``_health_monitor`` — framework health snapshot
    * ``_quality_check`` / ``_quality_check_deep`` — code quality detection

    Expected host attributes:
        _call_llm : async (tier, system, user, *, max_tokens, stage_name?) -> (str, int, int)
        logger    : logging.Logger
    """

    # -- Performance stages --------------------------------------------------

    async def _perf_check(self, input_data: dict, tier: Any) -> tuple[dict, int, int]:
        """Scan reviewed files for performance anti-patterns.

        Reuses PERF_PATTERNS from the perf-audit workflow to provide
        performance baselines alongside every code review.

        Args:
            input_data: Must contain ``files_changed`` list of file paths.
            tier: Model tier (unused — pure static analysis).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        from .perf_audit import PERF_PATTERNS

        files_changed: list[str] = input_data.get("files_changed", [])
        findings: list[dict] = []

        for file_str in files_changed:
            file_path = Path(file_str)
            if not file_path.exists() or not file_path.is_file():
                continue
            if file_path.suffix != ".py":
                continue

            try:
                content = file_path.read_text(errors="ignore")
            except OSError as e:
                logger.debug(f"Cannot read {file_path} for perf check: {e}")
                continue

            for pattern_name, pattern_info in PERF_PATTERNS.items():
                for pattern in pattern_info["patterns"]:
                    for match in re.finditer(pattern, content, re.MULTILINE):
                        line_num = content[: match.start()].count("\n") + 1
                        findings.append(
                            {
                                "type": pattern_name,
                                "file": str(file_path),
                                "line": line_num,
                                "description": pattern_info["description"],
                                "impact": pattern_info["impact"],
                                "match": match.group()[:80],
                            }
                        )

        by_impact: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for f in findings:
            by_impact[f.get("impact", "low")] = by_impact.get(f.get("impact", "low"), 0) + 1

        input_tokens = len(str(files_changed)) // CHARS_PER_TOKEN_ESTIMATE
        output_tokens = len(str(findings)) // CHARS_PER_TOKEN_ESTIMATE

        return (
            {
                "perf_findings": findings,
                "perf_finding_count": len(findings),
                "perf_by_impact": by_impact,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _perf_check_deep(
        self,
        input_data: dict,
        tier: Any,
    ) -> tuple[dict, int, int]:
        """LLM-enriched validation of performance findings.

        Sends static perf_check findings to a CAPABLE-tier model to:
        - Filter false positives (e.g., test fixtures, intentional patterns)
        - Adjust severity based on context
        - Add actionable fix suggestions

        Only runs when perf_finding_count > 0 (gated by should_skip_stage).

        Args:
            input_data: Must contain ``perf_findings`` from _perf_check.
            tier: Model tier (CAPABLE).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        findings = input_data.get("perf_findings", [])
        if not findings:
            return ({**input_data}, 0, 0)

        # Gather code snippets for context
        snippets = _gather_file_snippets(findings)

        # Format findings for the prompt
        findings_text = _format_findings_for_prompt(findings, snippets)

        system = (
            "You are a performance analysis expert. You will receive a list of "
            "performance anti-pattern findings from static analysis, along with "
            "code snippets for context.\n\n"
            "For each finding, determine:\n"
            "1. Is it a TRUE positive or FALSE positive? (e.g., test fixtures, "
            "intentional patterns, or patterns that don't apply in context)\n"
            "2. What is the correct severity? (high/medium/low)\n"
            "3. What is a specific, actionable fix suggestion?\n\n"
            "Respond in JSON format:\n"
            '{"findings": [\n'
            '  {"index": 0, "validated": true, "false_positive": false, '
            '"severity": "medium", "suggestion": "Use generator expression instead"},\n'
            '  {"index": 1, "validated": true, "false_positive": true, '
            '"severity": "low", "suggestion": "Test fixture, safe to ignore"}\n'
            "]}\n\n"
            "IMPORTANT: Only mark as false_positive if you are highly confident. "
            "When uncertain, keep validated=true and false_positive=false."
        )

        user_message = f"Analyze these {len(findings)} performance findings:\n\n" f"{findings_text}"

        response, in_tokens, out_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=2048,
            stage_name="perf_check_deep",
        )

        # Parse and merge enrichment back into findings
        enriched = _parse_deep_enrichment(response, findings)
        by_impact = _recount_by_key(enriched, "impact")
        validated_count = sum(1 for f in enriched if not f.get("false_positive", False))

        return (
            {
                "perf_findings": enriched,
                "perf_finding_count": validated_count,
                "perf_by_impact": by_impact,
                "perf_deep_ran": True,
                **{
                    k: v
                    for k, v in input_data.items()
                    if k not in ("perf_findings", "perf_finding_count", "perf_by_impact")
                },
            },
            in_tokens,
            out_tokens,
        )

    # -- Health monitoring ---------------------------------------------------

    async def _health_monitor(self, input_data: dict, tier: Any) -> tuple[dict, int, int]:
        """Collect framework health metrics snapshot.

        Pulls data from existing singletons (CacheMonitor, CostTracker,
        UsageTracker) to provide proactive monitoring alongside every review.
        Each source is independently wrapped so a missing dependency never
        blocks the stage.

        Args:
            input_data: Current workflow data (passed through).
            tier: Model tier (unused — no LLM calls).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        health_snapshot: dict[str, Any] = {}

        # Cache metrics
        try:
            from attune.cache_monitor import CacheMonitor

            monitor = CacheMonitor.get_instance()
            all_stats = monitor.get_all_stats()
            health_snapshot["cache_stats"] = (
                {
                    name: stats.to_dict() if hasattr(stats, "to_dict") else str(stats)
                    for name, stats in all_stats.items()
                }
                if all_stats
                else {}
            )
        except ImportError:
            logger.debug("CacheMonitor not available for health snapshot")
            health_snapshot["cache_stats"] = {}

        # Cost metrics (today)
        try:
            from attune.cost_tracker import get_tracker

            tracker = get_tracker()
            health_snapshot["cost_today"] = tracker.get_today()
        except ImportError:
            logger.debug("CostTracker not available for health snapshot")
            health_snapshot["cost_today"] = {}

        # Usage telemetry (last 7 days)
        try:
            from attune.telemetry import UsageTracker

            usage = UsageTracker.get_instance()
            health_snapshot["usage_stats_7d"] = usage.get_stats(days=7)
        except ImportError:
            logger.debug("UsageTracker not available for health snapshot")
            health_snapshot["usage_stats_7d"] = {}

        input_tokens = 0
        output_tokens = len(str(health_snapshot)) // CHARS_PER_TOKEN_ESTIMATE

        return (
            {
                "health_snapshot": health_snapshot,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    # -- Quality stages ------------------------------------------------------

    async def _quality_check(self, input_data: dict, tier: Any) -> tuple[dict, int, int]:
        """Static code quality checks on reviewed files.

        Lightweight regex/line-based checks (no AST parsing):
        - Bare ``except:`` or ``except Exception:`` without ``# noqa``
        - TODO/FIXME comment counts
        - Files exceeding 500 lines (complexity warning)
        - Public functions missing return type hints

        Args:
            input_data: Must contain ``files_changed`` list of file paths.
            tier: Model tier (unused — pure static analysis).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        files_changed: list[str] = input_data.get("files_changed", [])
        findings: list[dict] = []

        bare_except_re = re.compile(r"^\s*except\s*(?:Exception)?\s*:", re.MULTILINE)
        noqa_re = re.compile(r"#\s*noqa")
        todo_re = re.compile(r"#\s*(TODO|FIXME)\b", re.IGNORECASE)
        public_func_re = re.compile(r"^def\s+([a-zA-Z][a-zA-Z0-9_]*)\s*\(", re.MULTILINE)

        for file_str in files_changed:
            file_path = Path(file_str)
            if not file_path.exists() or not file_path.is_file():
                continue
            if file_path.suffix != ".py":
                continue

            try:
                content = file_path.read_text(errors="ignore")
            except OSError as e:
                logger.debug(f"Cannot read {file_path} for quality check: {e}")
                continue

            lines = content.splitlines()

            # Check file length
            if len(lines) > MAX_FILE_LINES:
                findings.append(
                    {
                        "type": "long_file",
                        "file": str(file_path),
                        "line": None,
                        "description": f"File has {len(lines)} lines (>{MAX_FILE_LINES}), consider splitting",
                        "severity": "medium",
                    }
                )

            # Check for bare except
            for match in bare_except_re.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                line_text = lines[line_num - 1] if line_num <= len(lines) else ""
                if not noqa_re.search(line_text):
                    findings.append(
                        {
                            "type": "bare_except",
                            "file": str(file_path),
                            "line": line_num,
                            "description": "Bare except or broad except Exception without # noqa",
                            "severity": "high",
                        }
                    )

            # Count TODOs/FIXMEs
            todo_count = len(todo_re.findall(content))
            if todo_count > 0:
                findings.append(
                    {
                        "type": "todo_fixme",
                        "file": str(file_path),
                        "line": None,
                        "description": f"{todo_count} TODO/FIXME comment(s) found",
                        "severity": "low",
                    }
                )

            # Check public functions for return type hints
            for match in public_func_re.finditer(content):
                func_name = match.group(1)
                if func_name.startswith("_"):
                    continue  # Skip private functions
                if not _has_return_type_hint(content, match.start()):
                    line_num = content[: match.start()].count("\n") + 1
                    findings.append(
                        {
                            "type": "missing_type_hint",
                            "file": str(file_path),
                            "line": line_num,
                            "description": f"Public function '{func_name}' missing return type hint",
                            "severity": "medium",
                        }
                    )

        by_severity: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.get("severity", "low")
            by_severity[sev] = by_severity.get(sev, 0) + 1

        input_tokens = len(str(files_changed)) // CHARS_PER_TOKEN_ESTIMATE
        output_tokens = len(str(findings)) // CHARS_PER_TOKEN_ESTIMATE

        return (
            {
                "quality_findings": findings,
                "quality_finding_count": len(findings),
                "quality_by_severity": by_severity,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _quality_check_deep(
        self,
        input_data: dict,
        tier: Any,
    ) -> tuple[dict, int, int]:
        """LLM-enriched validation of quality findings.

        Sends static quality_check findings to a CAPABLE-tier model to:
        - Filter false positives (e.g., intentional broad catches with # INTENTIONAL:)
        - Distinguish informational TODOs from blocking issues
        - Add specific fix suggestions with code examples

        Only runs when quality_finding_count > 0 (gated by should_skip_stage).

        Args:
            input_data: Must contain ``quality_findings`` from _quality_check.
            tier: Model tier (CAPABLE).

        Returns:
            Tuple of (result_dict, input_tokens, output_tokens).
        """
        findings = input_data.get("quality_findings", [])
        if not findings:
            return ({**input_data}, 0, 0)

        # Gather code snippets for context
        snippets = _gather_file_snippets(findings)

        # Format findings for the prompt
        findings_text = _format_findings_for_prompt(findings, snippets)

        system = (
            "You are a code quality expert. You will receive a list of "
            "quality findings from static analysis, along with code snippets.\n\n"
            "For each finding, determine:\n"
            "1. Is it a TRUE positive or FALSE positive? Consider:\n"
            "   - `except Exception` with `# noqa: BLE001` or `# INTENTIONAL:` "
            "is acceptable\n"
            "   - TODO/FIXME in test files may be lower priority\n"
            "   - Long files may be justified (e.g., test files)\n"
            "2. What is the correct severity? (high/medium/low)\n"
            "3. What is a specific, actionable fix suggestion?\n\n"
            "Respond in JSON format:\n"
            '{"findings": [\n'
            '  {"index": 0, "validated": true, "false_positive": false, '
            '"severity": "high", "suggestion": "Add specific exception types"},\n'
            '  {"index": 1, "validated": true, "false_positive": true, '
            '"severity": "low", "suggestion": "Intentional broad catch with '
            '# INTENTIONAL: comment"}\n'
            "]}\n\n"
            "IMPORTANT: Only mark as false_positive if you are highly confident. "
            "When uncertain, keep validated=true and false_positive=false."
        )

        user_message = f"Analyze these {len(findings)} quality findings:\n\n" f"{findings_text}"

        response, in_tokens, out_tokens = await self._call_llm(
            tier,
            system,
            user_message,
            max_tokens=2048,
            stage_name="quality_check_deep",
        )

        # Parse and merge enrichment back into findings
        enriched = _parse_deep_enrichment(response, findings)
        by_severity = _recount_by_key(enriched, "severity")
        validated_count = sum(1 for f in enriched if not f.get("false_positive", False))

        return (
            {
                "quality_findings": enriched,
                "quality_finding_count": validated_count,
                "quality_by_severity": by_severity,
                "quality_deep_ran": True,
                **{
                    k: v
                    for k, v in input_data.items()
                    if k
                    not in (
                        "quality_findings",
                        "quality_finding_count",
                        "quality_by_severity",
                    )
                },
            },
            in_tokens,
            out_tokens,
        )
