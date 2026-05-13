"""Discovery-sweep workflow package.

Orchestrated read-only discovery sweep: runs N sub-workflows on
a bounded path, filters findings through a verification rule
engine grounded in CLAUDE.md lessons, and produces a curated
queue tagged by resolution complexity.

See ``.claude/plans/discovery-sweep.md`` for the spec.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .budget import (
    DEFAULT_SUBWORKFLOW_BUDGET_USD,
    DEFAULT_SWEEP_BUDGET_USD,
    BudgetTracker,
    SweepBudgetExceeded,
)
from .cli_workflow import DiscoverySweepWorkflow
from .complexity import ComplexityClassifier, default_triggers
from .schema import (
    Finding,
    ResolutionComplexity,
    Severity,
    VerificationStatus,
)
from .serialization import (
    read_jsonl,
    write_jsonl,
    write_questions_markdown,
)
from .sources import PatternScanSource
from .verification import VerificationEngine
from .workflow import (
    DEFAULT_OUTPUT_DIR,
    DiscoverySweepEngine,
    FindingSource,
    SweepResult,
    split_findings_by_complexity,
)

__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_SUBWORKFLOW_BUDGET_USD",
    "DEFAULT_SWEEP_BUDGET_USD",
    "BudgetTracker",
    "ComplexityClassifier",
    "DiscoverySweepEngine",
    "DiscoverySweepWorkflow",
    "Finding",
    "FindingSource",
    "PatternScanSource",
    "ResolutionComplexity",
    "Severity",
    "SweepBudgetExceeded",
    "SweepResult",
    "VerificationEngine",
    "VerificationStatus",
    "default_triggers",
    "read_jsonl",
    "split_findings_by_complexity",
    "write_jsonl",
    "write_questions_markdown",
]
