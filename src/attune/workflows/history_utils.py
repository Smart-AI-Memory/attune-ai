"""Module-level workflow history utility functions.

Provides functions for saving and querying workflow execution history.
Uses SQLite-based storage by default with JSON fallback.

Extracted from base.py for maintainability.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path

from .data_classes import WorkflowResult

logger = logging.getLogger(__name__)

# Default path for workflow run history
WORKFLOW_HISTORY_FILE = ".attune/workflow_runs.json"

# Global singleton for workflow history store (lazy-initialized)
_history_store: Any = None  # WorkflowHistoryStore | None


def _get_history_store():
    """Get or create workflow history store singleton.

    Returns SQLite-based history store. Falls back to None if initialization fails.
    """
    global _history_store

    if _history_store is None:
        try:
            from .history import WorkflowHistoryStore

            _history_store = WorkflowHistoryStore()
            logger.debug("Workflow history store initialized (SQLite)")
        except (ImportError, OSError, PermissionError) as e:
            # File system errors or missing dependencies
            logger.warning(f"Failed to initialize SQLite history store: {e}")
            _history_store = False  # Mark as failed to avoid repeated attempts

    # Return store or None if initialization failed
    return _history_store if _history_store is not False else None


def _load_workflow_history(history_file: str = WORKFLOW_HISTORY_FILE) -> list[dict]:
    """Load workflow run history from disk (legacy JSON support).

    DEPRECATED: Use WorkflowHistoryStore for new code.
    This function is maintained for backward compatibility.

    Args:
        history_file: Path to JSON history file

    Returns:
        List of workflow run dictionaries

    """
    import warnings

    warnings.warn(
        "_load_workflow_history is deprecated. Use WorkflowHistoryStore instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    path = Path(history_file)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
            return list(data) if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_workflow_run(
    workflow_name: str,
    provider: str,
    result: WorkflowResult,
    history_file: str = WORKFLOW_HISTORY_FILE,
    max_history: int = 100,
) -> None:
    """Save a workflow run to history.

    Uses SQLite-based storage by default. Falls back to JSON if SQLite unavailable.

    Args:
        workflow_name: Name of the workflow
        provider: Provider used (anthropic, openai, google)
        result: WorkflowResult object
        history_file: Legacy JSON path (ignored if SQLite available)
        max_history: Legacy max history limit (ignored if SQLite available)

    """
    # Try SQLite first (new approach)
    store = _get_history_store()
    if store is not None:
        try:
            run_id = str(uuid.uuid4())
            store.record_run(run_id, workflow_name, provider, result)
            logger.debug(f"Workflow run saved to SQLite: {run_id}")
            return
        except (OSError, PermissionError, ValueError) as e:
            # SQLite failed, fall back to JSON
            logger.warning(f"Failed to save to SQLite, falling back to JSON: {e}")

    # Fallback: Legacy JSON storage
    logger.debug("Using legacy JSON storage for workflow history")
    path = Path(history_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    history = []
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
                history = list(data) if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            pass

    # Create run record
    run: dict = {
        "workflow": workflow_name,
        "provider": provider,
        "success": result.success,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat(),
        "duration_ms": result.total_duration_ms,
        "cost": result.cost_report.total_cost,
        "baseline_cost": result.cost_report.baseline_cost,
        "savings": result.cost_report.savings,
        "savings_percent": result.cost_report.savings_percent,
        "stages": [
            {
                "name": s.name,
                "tier": s.tier.value,
                "skipped": s.skipped,
                "cost": s.cost,
                "duration_ms": s.duration_ms,
            }
            for s in result.stages
        ],
        "error": result.error,
    }

    # Extract XML-parsed fields from final_output if present
    if isinstance(result.final_output, dict):
        if result.final_output.get("xml_parsed"):
            run["xml_parsed"] = True
            run["summary"] = result.final_output.get("summary")
            run["findings"] = result.final_output.get("findings", [])
            run["checklist"] = result.final_output.get("checklist", [])

    # Add to history and trim
    history.append(run)
    history = history[-max_history:]

    validated_path = _validate_file_path(str(path))
    with open(validated_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_workflow_stats(history_file: str = WORKFLOW_HISTORY_FILE) -> dict:
    """Get workflow statistics.

    Uses SQLite-based storage by default. Falls back to JSON if unavailable.

    Args:
        history_file: Legacy JSON path (used only if SQLite unavailable)

    Returns:
        Dictionary with workflow stats including:
        - total_runs: Total workflow runs
        - successful_runs: Number of successful runs
        - by_workflow: Per-workflow stats
        - by_provider: Per-provider stats
        - by_tier: Cost breakdown by tier
        - recent_runs: Last 10 runs
        - total_cost: Total cost across all runs
        - total_savings: Total cost savings
        - avg_savings_percent: Average savings percentage

    """
    # Try SQLite first (new approach)
    store = _get_history_store()
    if store is not None:
        try:
            return store.get_stats()
        except (OSError, PermissionError, ValueError) as e:
            # SQLite failed, fall back to JSON
            logger.warning(f"Failed to get stats from SQLite, falling back to JSON: {e}")

    # Fallback: Legacy JSON storage
    logger.debug("Using legacy JSON storage for workflow stats")
    history = []
    path = Path(history_file)
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
                history = list(data) if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            pass

    if not history:
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "by_workflow": {},
            "by_provider": {},
            "by_tier": {"cheap": 0, "capable": 0, "premium": 0},
            "recent_runs": [],
            "total_cost": 0.0,
            "total_savings": 0.0,
            "avg_savings_percent": 0.0,
        }

    # Aggregate stats
    by_workflow: dict[str, dict] = {}
    by_provider: dict[str, dict] = {}
    by_tier: dict[str, float] = {"cheap": 0.0, "capable": 0.0, "premium": 0.0}
    total_cost = 0.0
    total_savings = 0.0
    successful_runs = 0

    for run in history:
        wf_name = run.get("workflow", "unknown")
        provider = run.get("provider", "unknown")
        cost = run.get("cost", 0.0)
        savings = run.get("savings", 0.0)

        # By workflow
        if wf_name not in by_workflow:
            by_workflow[wf_name] = {"runs": 0, "cost": 0.0, "savings": 0.0, "success": 0}
        by_workflow[wf_name]["runs"] += 1
        by_workflow[wf_name]["cost"] += cost
        by_workflow[wf_name]["savings"] += savings
        if run.get("success"):
            by_workflow[wf_name]["success"] += 1

        # By provider
        if provider not in by_provider:
            by_provider[provider] = {"runs": 0, "cost": 0.0}
        by_provider[provider]["runs"] += 1
        by_provider[provider]["cost"] += cost

        # By tier (from stages)
        for stage in run.get("stages", []):
            if not stage.get("skipped"):
                tier = stage.get("tier", "capable")
                by_tier[tier] = by_tier.get(tier, 0.0) + stage.get("cost", 0.0)

        total_cost += cost
        total_savings += savings
        if run.get("success"):
            successful_runs += 1

    # Calculate average savings percent
    avg_savings_percent = 0.0
    if history:
        savings_percents = [r.get("savings_percent", 0) for r in history if r.get("success")]
        if savings_percents:
            avg_savings_percent = sum(savings_percents) / len(savings_percents)

    return {
        "total_runs": len(history),
        "successful_runs": successful_runs,
        "by_workflow": by_workflow,
        "by_provider": by_provider,
        "by_tier": by_tier,
        "recent_runs": history[-10:][::-1],  # Last 10, most recent first
        "total_cost": total_cost,
        "total_savings": total_savings,
        "avg_savings_percent": avg_savings_percent,
    }
