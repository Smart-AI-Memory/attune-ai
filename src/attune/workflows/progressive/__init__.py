"""Progressive tier escalation system for cost-efficient, quality-driven workflows.

This module implements automatic model tier escalation (cheap → capable → premium)
based on failure analysis and quality metrics. Key features:

- Multi-signal failure detection (syntax, execution, coverage, confidence)
- Composite Quality Score (CQS) for objective quality measurement
- LLM-guided retry logic with stagnation detection
- Meta-orchestration with dynamic agent team creation
- Cost management with budget controls and approval prompts
- Comprehensive observability and reporting

Usage:
    from attune.workflows.progressive import (
        ProgressiveWorkflow,
        EscalationConfig,
        Tier,
        FailureAnalysis
    )

    # Subclass ProgressiveWorkflow to build a tier-escalating
    # workflow. See ParallelTestGenerationWorkflow (invoked via
    # ``attune workflow run test-gen-parallel``) for the canonical
    # test-generation path — the previous ``ProgressiveTestGenWorkflow``
    # was deprecated in v5.3.0 and removed in v6.3.0 along with
    # the ``execute_test_file`` and ``calculate_coverage`` helpers
    # that only it used.

Version: 4.1.0
Author: Attune AI Team
"""

from attune.workflows.progressive.core import (
    EscalationConfig,
    FailureAnalysis,
    ProgressiveWorkflowResult,
    Tier,
    TierResult,
)
from attune.workflows.progressive.orchestrator import MetaOrchestrator
from attune.workflows.progressive.telemetry import ProgressiveTelemetry
from attune.workflows.progressive.workflow import (
    BudgetExceededError,
    ProgressiveWorkflow,
    UserCancelledError,
)

__all__ = [
    # Enums
    "Tier",
    # Core data structures
    "FailureAnalysis",
    "TierResult",
    "ProgressiveWorkflowResult",
    "EscalationConfig",
    # Base classes
    "ProgressiveWorkflow",
    "MetaOrchestrator",
    # Telemetry
    "ProgressiveTelemetry",
    # Exceptions
    "BudgetExceededError",
    "UserCancelledError",
]

from attune import __version__
