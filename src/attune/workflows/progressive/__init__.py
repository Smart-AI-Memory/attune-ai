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

    # Configure escalation
    config = EscalationConfig(
        enabled=True,
        max_cost=10.00,
        auto_approve_under=5.00
    )

    # Create workflow
    workflow = ProgressiveTestGenWorkflow(config)
    result = workflow.execute(target_file="app.py")

    # View report
    print(result.generate_report())

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
from attune.workflows.progressive.test_gen import (
    ProgressiveTestGenWorkflow,
    calculate_coverage,
    execute_test_file,
)
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
    # Workflows
    "ProgressiveTestGenWorkflow",
    # Utilities
    "execute_test_file",
    "calculate_coverage",
]

from attune import __version__
