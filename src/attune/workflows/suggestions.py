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

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .data_classes import NextAction

logger = logging.getLogger(__name__)

# Maximum suggestions to return per workflow completion
MAX_SUGGESTIONS = 3

# State file for cross-session suggestion persistence
_SUGGESTION_STATE_FILE = ".attune/suggestion_state.json"

# How many hours before a dismissed suggestion can reappear
_DISMISS_HOURS = 24


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
            ),
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
            ),
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
            ),
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
            ),
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
            ),
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
            ),
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
            ),
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
            ),
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
            ),
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
            ),
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
            ),
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
            ),
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
# SIGNAL SOURCE 2: PROJECT INDEX
# ============================================================================


def _suggestions_from_project_index(workflow_name: str) -> list[NextAction]:
    """Generate suggestions from project index health signals.

    Analyzes cached project index for coverage gaps, stale tests,
    and files needing attention. Returns suggestions independent
    of the specific workflow that just ran.

    Args:
        workflow_name: Name of the completed workflow (to avoid
            suggesting the same workflow that just ran)

    Returns:
        List of NextAction based on project health signals

    """
    suggestions: list[NextAction] = []
    index_path = Path(".attune/project_index.json")

    if not index_path.exists():
        return suggestions

    try:
        with open(index_path) as f:
            index_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.debug("Could not load project index: %s", e)
        return suggestions

    summary = index_data.get("summary", {})
    if not summary:
        return suggestions

    # Low test coverage -> suggest test generation
    coverage_avg = summary.get("test_coverage_avg", 100.0)
    files_without_tests = summary.get("files_without_tests", 0)
    if coverage_avg < 80 and workflow_name != "test-gen":
        suggestions.append(
            NextAction(
                workflow_name="test-gen",
                description=(
                    f"Project coverage is {coverage_avg:.0f}% with "
                    f"{files_without_tests} untested file(s) — "
                    f"generate tests for the critical gaps?"
                ),
                reasoning="Project index shows coverage below 80% threshold.",
                priority="medium",
                confidence=min(0.5 + (80 - coverage_avg) * 0.01, 0.85),
            ),
        )

    # Stale tests -> suggest test generation
    stale_count = summary.get("stale_file_count", 0)
    if stale_count > 0 and workflow_name != "test-gen":
        suggestions.append(
            NextAction(
                workflow_name="test-gen",
                description=(
                    f"{stale_count} file(s) have stale tests — "
                    f"regenerate to catch recent changes?"
                ),
                reasoning="Code changed but tests haven't been updated.",
                priority="medium",
                confidence=min(0.5 + stale_count * 0.05, 0.8),
            ),
        )

    # Critical untested files -> suggest security audit
    critical_untested = summary.get("critical_untested_files", [])
    if len(critical_untested) > 0 and workflow_name != "security-audit":
        suggestions.append(
            NextAction(
                workflow_name="security-audit",
                description=(
                    f"{len(critical_untested)} high-impact file(s) have "
                    f"no tests — audit for security risks?"
                ),
                reasoning="High-impact files without test coverage pose security risk.",
                priority="high",
                confidence=min(0.6 + len(critical_untested) * 0.05, 0.85),
            ),
        )

    # Files needing attention -> suggest code review
    attention_count = summary.get("files_needing_attention", 0)
    if attention_count > 3 and workflow_name != "code-review":
        suggestions.append(
            NextAction(
                workflow_name="code-review",
                description=(
                    f"{attention_count} file(s) need attention — run a code review to triage?"
                ),
                reasoning="Project index flagged multiple files for review.",
                priority="medium",
                confidence=min(0.5 + attention_count * 0.03, 0.75),
            ),
        )

    return suggestions


# ============================================================================
# SIGNAL SOURCE 3: WORKFLOW HISTORY
# ============================================================================


def _suggestions_from_history(workflow_name: str) -> list[NextAction]:
    """Generate suggestions from workflow run history patterns.

    Analyzes past successful workflow sequences to suggest what
    users typically run next. Only suggests workflows that have
    historically followed the current one.

    Args:
        workflow_name: Name of the completed workflow

    Returns:
        List of NextAction based on historical patterns

    """
    suggestions: list[NextAction] = []

    try:
        from .history_utils import _get_history_store

        store = _get_history_store()
        if store is None:
            return suggestions

        # Get recent successful runs (last 50)
        recent_runs = store.query_runs(success_only=True, limit=50)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: History is optional — don't crash if unavailable
        logger.debug("Workflow history unavailable for suggestions")
        return suggestions

    if len(recent_runs) < 3:
        return suggestions

    # Build follow-up frequency map: what workflow runs after workflow_name?
    follow_ups: dict[str, int] = {}
    sorted_runs = sorted(recent_runs, key=lambda r: r.get("started_at", ""))

    for i in range(len(sorted_runs) - 1):
        current_wf = sorted_runs[i].get("workflow_name", "")
        next_wf = sorted_runs[i + 1].get("workflow_name", "")

        if current_wf == workflow_name and next_wf != workflow_name:
            follow_ups[next_wf] = follow_ups.get(next_wf, 0) + 1

    if not follow_ups:
        return suggestions

    # Only suggest patterns seen at least twice
    total_sequences = sum(follow_ups.values())
    for next_wf, count in sorted(follow_ups.items(), key=lambda x: -x[1]):
        if count < 2:
            continue

        frequency = count / total_sequences
        suggestions.append(
            NextAction(
                workflow_name=next_wf,
                description=(
                    f"You've run /{next_wf} after /{workflow_name} "
                    f"{count} times — run it again?"
                ),
                reasoning=(
                    f"Historical pattern: {frequency:.0%} of the time "
                    f"you follow {workflow_name} with {next_wf}."
                ),
                priority="low",
                confidence=min(0.4 + frequency * 0.4, 0.75),
            ),
        )

    return suggestions


# ============================================================================
# SIGNAL SOURCE 4: SUGGESTION PERSISTENCE
# ============================================================================


def _load_suggestion_state() -> dict[str, Any]:
    """Load suggestion state from disk.

    Returns:
        State dict with 'dismissed' mapping of workflow_name to ISO timestamp

    """
    state_path = Path(_SUGGESTION_STATE_FILE)
    if not state_path.exists():
        return {"dismissed": {}}

    try:
        with open(state_path) as f:
            data: dict[str, Any] = json.load(f)
            return data
    except (OSError, json.JSONDecodeError):
        return {"dismissed": {}}


def _save_suggestion_state(state: dict[str, Any]) -> None:
    """Save suggestion state to disk.

    Args:
        state: State dict to persist

    """
    state_path = Path(_SUGGESTION_STATE_FILE)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
    except OSError as e:
        logger.debug("Could not save suggestion state: %s", e)


def _filter_recently_shown(suggestions: list[NextAction]) -> list[NextAction]:
    """Filter out suggestions that were recently shown.

    Removes suggestions for workflow names that were dismissed or
    shown within the last _DISMISS_HOURS hours.

    Args:
        suggestions: Unfiltered suggestion list

    Returns:
        Filtered list with recently-shown suggestions removed

    """
    state = _load_suggestion_state()
    dismissed = state.get("dismissed", {})

    if not dismissed:
        return suggestions

    now = datetime.now()
    filtered: list[NextAction] = []

    for s in suggestions:
        dismiss_time_str = dismissed.get(s.workflow_name)
        if dismiss_time_str:
            try:
                dismiss_time = datetime.fromisoformat(dismiss_time_str)
                hours_ago = (now - dismiss_time).total_seconds() / 3600
                if hours_ago < _DISMISS_HOURS:
                    continue  # Skip — too recent
            except (ValueError, TypeError):
                pass  # Bad timestamp, don't filter

        filtered.append(s)

    return filtered


def record_suggestions_shown(suggestions: list[NextAction]) -> None:
    """Record that suggestions were shown to avoid repeats.

    Marks each suggested workflow_name with a timestamp so
    _filter_recently_shown can suppress it for _DISMISS_HOURS.

    Args:
        suggestions: List of suggestions that were displayed

    """
    if not suggestions:
        return

    state = _load_suggestion_state()
    now_str = datetime.now().isoformat()

    for s in suggestions:
        state.setdefault("dismissed", {})[s.workflow_name] = now_str

    _save_suggestion_state(state)


# ============================================================================
# SUGGESTION ENGINE
# ============================================================================


def generate_suggestions(
    workflow_name: str,
    result: Any,
) -> list[NextAction]:
    """Generate contextual next-step suggestions after workflow completion.

    Combines three signal sources with deduplication and persistence
    filtering to produce prioritized, evidence-based suggestions:
    1. Workflow transition registry (keyword analysis of results)
    2. Project index signals (coverage, staleness, attention)
    3. Workflow history patterns (common follow-up sequences)

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

    # Source 2: Project index signals
    try:
        suggestions.extend(_suggestions_from_project_index(workflow_name))
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Project index is optional
        logger.debug("Project index suggestions failed for %s", workflow_name)

    # Source 3: Workflow history patterns
    try:
        suggestions.extend(_suggestions_from_history(workflow_name))
    except Exception:  # noqa: BLE001
        # INTENTIONAL: History is optional
        logger.debug("History suggestions failed for %s", workflow_name)

    # Deduplicate by workflow_name (keep highest confidence)
    seen: dict[str, NextAction] = {}
    for s in suggestions:
        existing = seen.get(s.workflow_name)
        if existing is None or s.confidence > existing.confidence:
            seen[s.workflow_name] = s
    suggestions = list(seen.values())

    # Filter out recently-shown suggestions
    suggestions = _filter_recently_shown(suggestions)

    # Sort: high priority first, then by confidence descending
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(
        key=lambda s: (priority_order.get(s.priority, 1), -s.confidence),
    )

    final = suggestions[:MAX_SUGGESTIONS]

    # Record that these suggestions were shown
    record_suggestions_shown(final)

    return final


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
            },
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
            ),
        )

    if result.error_type == "config":
        suggestions.append(
            NextAction(
                workflow_name="dependency-check",
                description="Check project configuration and dependencies.",
                reasoning="Configuration error suggests setup issue.",
                priority="high",
                confidence=0.75,
            ),
        )

    return suggestions[:MAX_SUGGESTIONS]
