"""Project-Aware Guidance: Suggestion Engine.

Generates contextual next-step suggestions after workflow completion
based on workflow results, project index signals, and workflow
transition mappings.

Three signal sources:
1. Workflow transition registry (static mappings with conditions)
2. Project index signals (coverage, staleness, attention flags)
3. Workflow history patterns (what workflows succeed together)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

from .data_classes import NextAction

logger = logging.getLogger(__name__)

# Maximum suggestions to return per workflow completion
MAX_SUGGESTIONS = 3


def _extract_output_text(final_output: Any) -> str:
    """Extract searchable text from workflow final_output.

    Args:
        final_output: Raw workflow output (str, dict, or other)

    Returns:
        Lowercased text representation for keyword matching
    """
    if isinstance(final_output, str):
        return final_output.lower()
    if isinstance(final_output, dict):
        return str(final_output).lower()
    return str(final_output).lower() if final_output else ""


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count how many keywords appear in text.

    Args:
        text: Text to search (should be lowercased)
        keywords: Keywords to look for

    Returns:
        Number of keywords found
    """
    return sum(1 for kw in keywords if kw in text)


# ============================================================================
# WORKFLOW TRANSITION REGISTRY
# ============================================================================

# Each entry maps a source workflow to a list of possible next workflows.
# Conditions are evaluated against the WorkflowResult to determine
# which suggestions are relevant.


def _transitions_for_code_review(result: Any) -> list[NextAction]:
    """Generate suggestions after code-review workflow.

    Args:
        result: WorkflowResult from code-review

    Returns:
        List of relevant NextAction suggestions
    """
    suggestions: list[NextAction] = []
    output_text = _extract_output_text(result.final_output)

    # Security findings -> security audit
    security_keywords = ["security", "vulnerability", "injection", "xss", "path traversal"]
    security_hits = _count_keyword_hits(output_text, security_keywords)
    if security_hits > 0:
        suggestions.append(
            NextAction(
                workflow_name="security-audit",
                description=(
                    f"Review found {security_hits} security-related "
                    f"finding(s) — want a deeper security audit?"
                ),
                reasoning="Code review surfaced security keywords suggesting deeper analysis.",
                priority="high",
                confidence=min(0.5 + security_hits * 0.15, 0.95),
            )
        )

    # Performance findings -> perf audit
    perf_keywords = ["performance", "slow", "n+1", "complexity", "bottleneck", "optimize"]
    perf_hits = _count_keyword_hits(output_text, perf_keywords)
    if perf_hits > 0:
        suggestions.append(
            NextAction(
                workflow_name="perf-audit",
                description=(
                    f"Review flagged {perf_hits} performance concern(s) "
                    f"— want a focused performance audit?"
                ),
                reasoning="Code review surfaced performance-related findings.",
                priority="medium",
                confidence=min(0.5 + perf_hits * 0.15, 0.9),
            )
        )

    # Any findings -> test generation
    if result.success and output_text:
        suggestions.append(
            NextAction(
                workflow_name="test-gen",
                description="Generate tests for the modules highlighted in the review.",
                reasoning="Code review identified areas that would benefit from test coverage.",
                priority="medium",
                confidence=0.7,
            )
        )

    return suggestions


def _transitions_for_security_audit(result: Any) -> list[NextAction]:
    """Generate suggestions after security-audit workflow.

    Args:
        result: WorkflowResult from security-audit

    Returns:
        List of relevant NextAction suggestions
    """
    suggestions: list[NextAction] = []
    output_text = _extract_output_text(result.final_output)

    # High severity -> dependency check
    high_keywords = ["critical", "high severity", "high risk", "vulnerability"]
    high_hits = _count_keyword_hits(output_text, high_keywords)
    if high_hits > 0:
        suggestions.append(
            NextAction(
                workflow_name="dependency-check",
                description=(
                    "Security audit found high-severity issues — "
                    "check dependencies for known vulnerabilities too?"
                ),
                reasoning="High-severity security findings often correlate with dependency risks.",
                priority="high",
                confidence=0.85,
            )
        )

    # Any security findings -> release prep
    if result.success:
        suggestions.append(
            NextAction(
                workflow_name="release-prep",
                description="Run release readiness check to verify security posture before shipping.",
                reasoning="Security audit completed — validate overall release readiness.",
                priority="medium",
                confidence=0.7,
            )
        )

    return suggestions


def _transitions_for_test_gen(result: Any) -> list[NextAction]:
    """Generate suggestions after test-gen workflow.

    Args:
        result: WorkflowResult from test-gen

    Returns:
        List of relevant NextAction suggestions
    """
    suggestions: list[NextAction] = []

    if result.success:
        suggestions.append(
            NextAction(
                workflow_name="code-review",
                description="Review the generated tests for quality and completeness.",
                reasoning="Generated tests benefit from a quality pass before committing.",
                priority="medium",
                confidence=0.75,
            )
        )

    return suggestions


def _transitions_for_bug_predict(result: Any) -> list[NextAction]:
    """Generate suggestions after bug-predict workflow.

    Args:
        result: WorkflowResult from bug-predict

    Returns:
        List of relevant NextAction suggestions
    """
    suggestions: list[NextAction] = []
    output_text = _extract_output_text(result.final_output)

    # High-risk files -> test generation
    risk_keywords = ["high risk", "high probability", "likely bug", "critical"]
    risk_hits = _count_keyword_hits(output_text, risk_keywords)
    if risk_hits > 0:
        suggestions.append(
            NextAction(
                workflow_name="test-gen",
                description=(
                    f"Bug prediction flagged {risk_hits} high-risk area(s) "
                    f"— generate tests to catch regressions?"
                ),
                reasoning="High-risk code areas benefit most from targeted test coverage.",
                priority="high",
                confidence=0.85,
            )
        )

    # Complexity findings -> refactor plan
    complexity_keywords = ["complex", "tangled", "deeply nested", "high complexity"]
    if _count_keyword_hits(output_text, complexity_keywords) > 0:
        suggestions.append(
            NextAction(
                workflow_name="refactor-plan",
                description="Bug prediction found complexity hotspots — plan a refactor?",
                reasoning="Complex code correlates with bug density.",
                priority="medium",
                confidence=0.7,
            )
        )

    return suggestions


def _transitions_for_perf_audit(result: Any) -> list[NextAction]:
    """Generate suggestions after perf-audit workflow.

    Args:
        result: WorkflowResult from perf-audit

    Returns:
        List of relevant NextAction suggestions
    """
    suggestions: list[NextAction] = []
    output_text = _extract_output_text(result.final_output)

    # Optimization opportunities -> simplify code
    if result.success and output_text:
        suggestions.append(
            NextAction(
                workflow_name="simplify-code",
                description="Simplify code in the modules flagged for performance issues.",
                reasoning="Simpler code is often faster code — reduce unnecessary complexity.",
                priority="medium",
                confidence=0.7,
            )
        )

    return suggestions


def _transitions_for_refactor_plan(result: Any) -> list[NextAction]:
    """Generate suggestions after refactor-plan workflow.

    Args:
        result: WorkflowResult from refactor-plan

    Returns:
        List of relevant NextAction suggestions
    """
    suggestions: list[NextAction] = []

    if result.success:
        suggestions.append(
            NextAction(
                workflow_name="test-gen",
                description="Generate tests before refactoring to ensure behavior is preserved.",
                reasoning="Test-first refactoring prevents regressions.",
                priority="high",
                confidence=0.9,
            )
        )

    return suggestions


def _transitions_for_simplify_code(result: Any) -> list[NextAction]:
    """Generate suggestions after simplify-code workflow.

    Args:
        result: WorkflowResult from simplify-code

    Returns:
        List of relevant NextAction suggestions
    """
    suggestions: list[NextAction] = []

    if result.success:
        suggestions.append(
            NextAction(
                workflow_name="code-review",
                description="Review simplified code to verify correctness was preserved.",
                reasoning="Simplification changes should be validated before committing.",
                priority="medium",
                confidence=0.8,
            )
        )

    return suggestions


def _transitions_for_dependency_check(result: Any) -> list[NextAction]:
    """Generate suggestions after dependency-check workflow.

    Args:
        result: WorkflowResult from dependency-check

    Returns:
        List of relevant NextAction suggestions
    """
    suggestions: list[NextAction] = []
    output_text = _extract_output_text(result.final_output)

    outdated_keywords = ["outdated", "update available", "upgrade", "deprecated"]
    if _count_keyword_hits(output_text, outdated_keywords) > 0:
        suggestions.append(
            NextAction(
                workflow_name="test-gen",
                description="Dependencies have updates — generate tests before upgrading.",
                reasoning="Test coverage reduces risk when updating dependencies.",
                priority="medium",
                confidence=0.75,
            )
        )

    return suggestions


# Registry mapping workflow names to their transition functions
_TRANSITION_REGISTRY: dict[str, Any] = {
    "code-review": _transitions_for_code_review,
    "security-audit": _transitions_for_security_audit,
    "test-gen": _transitions_for_test_gen,
    "bug-predict": _transitions_for_bug_predict,
    "perf-audit": _transitions_for_perf_audit,
    "refactor-plan": _transitions_for_refactor_plan,
    "simplify-code": _transitions_for_simplify_code,
    "dependency-check": _transitions_for_dependency_check,
}


# ============================================================================
# SUGGESTION ENGINE
# ============================================================================


def generate_suggestions(
    workflow_name: str,
    result: Any,
) -> list[NextAction]:
    """Generate contextual next-step suggestions after workflow completion.

    Combines workflow transition mappings with result analysis to produce
    prioritized, evidence-based suggestions.

    Args:
        workflow_name: Name of the completed workflow
        result: WorkflowResult from the completed workflow

    Returns:
        List of NextAction suggestions, sorted by priority then confidence,
        limited to MAX_SUGGESTIONS
    """
    if not result.success:
        # On failure, suggest retry or related diagnostic workflow
        return _suggestions_for_failure(workflow_name, result)

    suggestions: list[NextAction] = []

    # Source 1: Workflow transition registry
    transition_fn = _TRANSITION_REGISTRY.get(workflow_name)
    if transition_fn:
        try:
            suggestions.extend(transition_fn(result))
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Suggestion generation is optional — never crash workflow
            logger.debug("Suggestion transition failed for %s", workflow_name)

    # Deduplicate by workflow_name (keep highest confidence)
    seen: dict[str, NextAction] = {}
    for s in suggestions:
        existing = seen.get(s.workflow_name)
        if existing is None or s.confidence > existing.confidence:
            seen[s.workflow_name] = s
    suggestions = list(seen.values())

    # Sort: high priority first, then by confidence descending
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(
        key=lambda s: (priority_order.get(s.priority, 1), -s.confidence),
    )

    return suggestions[:MAX_SUGGESTIONS]


def format_suggestions_markdown(suggestions: list[NextAction]) -> str:
    """Format suggestions as markdown for Claude Code skill output.

    Produces a "What's Next" section that skills can append to
    workflow results. Designed to be presented via AskUserQuestion.

    Args:
        suggestions: List of NextAction from generate_suggestions()

    Returns:
        Markdown-formatted suggestions text, or empty string if none
    """
    if not suggestions:
        return ""

    lines = ["", "## What's Next", ""]

    priority_icons = {"high": "!", "medium": "-", "low": " "}

    for i, s in enumerate(suggestions, 1):
        icon = priority_icons.get(s.priority, "-")
        lines.append(f"{i}. **`/{s.workflow_name}`** {icon} {s.description}")
        lines.append(f"   *{s.reasoning}*")
        lines.append("")

    return "\n".join(lines)


def suggestions_to_options(suggestions: list[NextAction]) -> list[dict[str, str]]:
    """Convert suggestions to AskUserQuestion option format.

    Returns a list of option dicts ready for the AskUserQuestion
    tool's options parameter.

    Args:
        suggestions: List of NextAction from generate_suggestions()

    Returns:
        List of option dicts with 'label' and 'description' keys
    """
    options = []
    for s in suggestions:
        options.append(
            {
                "label": f"/{s.workflow_name}",
                "description": s.description,
            }
        )
    return options


def _suggestions_for_failure(
    workflow_name: str,
    result: Any,
) -> list[NextAction]:
    """Generate suggestions when a workflow fails.

    Args:
        workflow_name: Name of the failed workflow
        result: WorkflowResult with error information

    Returns:
        List of NextAction suggestions for recovery
    """
    suggestions: list[NextAction] = []

    if result.transient:
        suggestions.append(
            NextAction(
                workflow_name=workflow_name,
                description=f"Retry {workflow_name} — the error appears transient.",
                reasoning=f"Error classified as {result.error_type} (transient).",
                priority="high",
                confidence=0.8,
            )
        )

    if result.error_type == "config":
        suggestions.append(
            NextAction(
                workflow_name="dependency-check",
                description="Check project configuration and dependencies.",
                reasoning="Configuration error suggests setup issue.",
                priority="high",
                confidence=0.75,
            )
        )

    return suggestions[:MAX_SUGGESTIONS]
