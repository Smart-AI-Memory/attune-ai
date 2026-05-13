"""Budget tracker for the discovery-sweep workflow.

Two ceilings: a per-sub-workflow cap (default $10) and a total
sweep cap (default $40). Crossing the total cap raises
``SweepBudgetExceeded`` and the orchestrator halts further
sub-workflow invocation.

Defaults can be overridden via environment variables:
- ATTUNE_DISCOVERY_SUBWORKFLOW_BUDGET_USD
- ATTUNE_DISCOVERY_SWEEP_BUDGET_USD

Or per-instance via constructor args.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_SUBWORKFLOW_BUDGET_USD = 10.0
DEFAULT_SWEEP_BUDGET_USD = 40.0


class SweepBudgetExceeded(RuntimeError):
    """Raised when the sweep-level budget cap is hit."""


@dataclass
class BudgetReport:
    """Per-sub-workflow spend record."""

    sub_workflow: str
    spend_usd: float
    capped: bool = False


@dataclass
class BudgetTracker:
    """Tracks per-sub-workflow + total spend across a sweep."""

    subworkflow_cap_usd: float = DEFAULT_SUBWORKFLOW_BUDGET_USD
    sweep_cap_usd: float = DEFAULT_SWEEP_BUDGET_USD
    spend_by_subworkflow: dict[str, float] = field(default_factory=dict)
    reports: list[BudgetReport] = field(default_factory=list)

    @classmethod
    def from_env(
        cls,
        *,
        subworkflow_cap_usd: float | None = None,
        sweep_cap_usd: float | None = None,
    ) -> BudgetTracker:
        """Construct a tracker, honoring env-var overrides.

        Explicit kwargs override env vars, which override defaults.
        """

        def _resolve(value: float | None, env_var: str, default: float) -> float:
            if value is not None:
                return value
            raw = os.environ.get(env_var)
            if raw is None:
                return default
            try:
                parsed = float(raw)
            except ValueError:
                return default
            return parsed

        return cls(
            subworkflow_cap_usd=_resolve(
                subworkflow_cap_usd,
                "ATTUNE_DISCOVERY_SUBWORKFLOW_BUDGET_USD",
                DEFAULT_SUBWORKFLOW_BUDGET_USD,
            ),
            sweep_cap_usd=_resolve(
                sweep_cap_usd,
                "ATTUNE_DISCOVERY_SWEEP_BUDGET_USD",
                DEFAULT_SWEEP_BUDGET_USD,
            ),
        )

    @property
    def total_spend_usd(self) -> float:
        return sum(self.spend_by_subworkflow.values())

    @property
    def remaining_sweep_usd(self) -> float:
        return max(0.0, self.sweep_cap_usd - self.total_spend_usd)

    def budget_for(self, sub_workflow: str) -> float:
        """Return the budget a sub-workflow can spend right now.

        The smaller of the per-sub-workflow cap and the remaining
        sweep budget.
        """
        return min(self.subworkflow_cap_usd, self.remaining_sweep_usd)

    def can_run(self, sub_workflow: str) -> bool:
        """Whether at least a token amount of budget remains."""
        return self.remaining_sweep_usd > 0.01

    def record(self, sub_workflow: str, spend_usd: float) -> BudgetReport:
        """Record a sub-workflow's actual spend.

        Raises ``SweepBudgetExceeded`` if recording this spend
        crosses the sweep ceiling. The record is still saved
        before the raise so the audit log captures the overrun.
        """
        capped = spend_usd >= self.subworkflow_cap_usd
        self.spend_by_subworkflow[sub_workflow] = (
            self.spend_by_subworkflow.get(sub_workflow, 0.0) + spend_usd
        )
        report = BudgetReport(sub_workflow=sub_workflow, spend_usd=spend_usd, capped=capped)
        self.reports.append(report)

        if self.total_spend_usd > self.sweep_cap_usd:
            raise SweepBudgetExceeded(
                f"sweep budget {self.sweep_cap_usd:.2f} exceeded "
                f"(now ${self.total_spend_usd:.2f}); halting further "
                f"sub-workflow invocation"
            )
        return report


__all__ = [
    "DEFAULT_SUBWORKFLOW_BUDGET_USD",
    "DEFAULT_SWEEP_BUDGET_USD",
    "BudgetReport",
    "BudgetTracker",
    "SweepBudgetExceeded",
]
