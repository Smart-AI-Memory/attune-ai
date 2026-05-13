"""BaseWorkflow wrapper that exposes the engine to ``attune workflow run``.

The wrapper is thin: it parses CLI/workflow-runner kwargs,
instantiates default sources (``PatternScanSource`` by default),
runs the engine, and packages the result as a ``WorkflowResult``
so the existing CLI dispatch is happy.

Phase 2A ships this with the deterministic pattern scanner.
LLM-driven adapters wrapping ``BugPredictionWorkflow``,
``SecurityAuditWorkflow``, etc. are Phase 2B work.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attune.models import ModelTier
from attune.workflows.base import BaseWorkflow
from attune.workflows.data_classes import CostReport, WorkflowResult, WorkflowStage

from .budget import BudgetTracker
from .sources import PatternScanSource
from .workflow import DiscoverySweepEngine, FindingSource, SweepResult

logger = logging.getLogger(__name__)


def _default_sources() -> list[FindingSource]:
    """Phase 2A default — just the deterministic pattern scanner."""
    return [PatternScanSource()]


class DiscoverySweepWorkflow(BaseWorkflow):
    """``attune workflow run discovery-sweep`` entry point.

    Inherits from ``BaseWorkflow`` so the workflow registry,
    workflow-runner dispatch, and CLI surface all see a familiar
    shape. Internally delegates to ``DiscoverySweepEngine``.

    Args (via ``execute(**kwargs)``):
        path (str): Required. Directory or file to sweep.
        output_dir (str): Optional. Override the default
            ``.claude/discovery-queue/``.
        subworkflow_budget_usd (float): Optional. Override the
            ``ATTUNE_DISCOVERY_SUBWORKFLOW_BUDGET_USD`` cap.
        sweep_budget_usd (float): Optional. Override the
            ``ATTUNE_DISCOVERY_SWEEP_BUDGET_USD`` cap.
        sources (list[FindingSource]): Optional. Inject custom
            adapters in place of the Phase 2A defaults — useful
            for tests and for early adopters wiring their own
            adapters before Phase 2B lands.
    """

    name = "discovery-sweep"
    description = (
        "Read-only discovery sweep — runs N FindingSource adapters "
        "on a bounded path, filters findings through verification "
        "rules grounded in CLAUDE.md lessons, and produces a "
        "curated queue tagged by resolution complexity."
    )
    stages = ["sweep"]

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Run the sweep and package the result for the CLI."""
        path_arg = kwargs.get("path", "")
        if not path_arg:
            return self._error_result("path argument is required")

        try:
            scope = Path(path_arg).resolve()
        except (OSError, RuntimeError) as exc:
            return self._error_result(f"invalid path: {exc}")

        sources = kwargs.get("sources") or _default_sources()
        if not sources:
            return self._error_result(
                "discovery-sweep requires at least one source; " "default is PatternScanSource"
            )

        budget = BudgetTracker.from_env(
            subworkflow_cap_usd=kwargs.get("subworkflow_budget_usd"),
            sweep_cap_usd=kwargs.get("sweep_budget_usd"),
        )

        output_dir = kwargs.get("output_dir")
        engine = DiscoverySweepEngine(
            sources=sources,
            budget=budget,
            output_dir=output_dir,
        )

        started_at = datetime.now(timezone.utc)
        try:
            sweep_result: SweepResult = engine.run(scope=scope)
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: any orchestrator-level crash must surface
            # as a WorkflowResult failure so the CLI doesn't silently
            # swallow it.
            logger.exception("discovery-sweep engine failed")
            return self._error_result(f"sweep failed: {type(exc).__name__}: {exc}")
        completed_at = datetime.now(timezone.utc)

        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        summary = _format_summary(sweep_result)

        return WorkflowResult(
            success=True,
            stages=[
                WorkflowStage(
                    name="sweep",
                    tier=ModelTier.CHEAP,
                    description="discovery sweep",
                    cost=sweep_result.total_spend_usd,
                    duration_ms=duration_ms,
                    result=summary,
                )
            ],
            final_output=summary,
            cost_report=CostReport(
                total_cost=sweep_result.total_spend_usd,
                baseline_cost=sweep_result.total_spend_usd,
                savings=0.0,
                savings_percent=0.0,
            ),
            started_at=started_at.replace(tzinfo=None),
            completed_at=completed_at.replace(tzinfo=None),
            total_duration_ms=duration_ms,
            provider="discovery-sweep",
            metadata={
                "sweep_id": sweep_result.sweep_id,
                "scope": sweep_result.scope,
                "accept_count": sweep_result.accept_count,
                "reject_count": sweep_result.reject_count,
                "unsure_count": sweep_result.unsure_count,
                "queue_path": sweep_result.queue_path,
                "rejected_path": sweep_result.rejected_path,
                "questions_path": sweep_result.questions_path,
                "total_spend_usd": sweep_result.total_spend_usd,
                "sub_workflow_spend": sweep_result.sub_workflow_spend,
                "sub_workflow_errors": sweep_result.sub_workflow_errors,
                "budget_halted": sweep_result.budget_halted,
                "sweep_result": asdict(sweep_result),
            },
            summary=summary,
        )


def _format_summary(result: SweepResult) -> str:
    """Render a CLI-friendly summary line for the WorkflowResult."""
    parts = [
        f"sweep {result.sweep_id}",
        f"scope={result.scope}",
        f"accept={result.accept_count}",
        f"reject={result.reject_count}",
        f"unsure={result.unsure_count}",
        f"spend=${result.total_spend_usd:.2f}",
    ]
    if result.budget_halted:
        parts.append("budget_halted=true")
    if result.sub_workflow_errors:
        parts.append(f"errors={len(result.sub_workflow_errors)}")
    if result.queue_path:
        parts.append(f"queue={result.queue_path}")
    return " | ".join(parts)


__all__ = ["DiscoverySweepWorkflow"]
