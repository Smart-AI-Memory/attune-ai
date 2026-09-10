"""Software Development Plugin for Attune AI Framework.

Registers software development workflows as a bundled plugin loaded
directly by the core registry.

Requires attune-ai core for BasePlugin, BaseWorkflow, and PluginMetadata.

Copyright 2025 Smart AI Memory, LLC
Licensed under Apache-2.0
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

from attune.plugins import BasePlugin, PluginMetadata

if TYPE_CHECKING:
    from attune.workflows.base import BaseWorkflow

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Map of workflow IDs to (module_path, class_name) for lazy importing.
# Each workflow is imported on demand so missing optional deps don't
# prevent the plugin from loading.
# ---------------------------------------------------------------------------

_WORKFLOW_MAP: dict[str, tuple[str, str]] = {
    "code-review": ("attune.workflows.code_review", "CodeReviewWorkflow"),
    "bug-predict": ("attune.workflows.bug_predict", "BugPredictionWorkflow"),
    "security-audit": ("attune.workflows.security_audit", "SecurityAuditWorkflow"),
    "perf-audit": ("attune.workflows.perf_audit", "PerformanceAuditWorkflow"),
    "test-gen": ("attune.workflows.test_gen", "TestGenerationWorkflow"),
    "refactor-plan": ("attune.workflows.refactor_plan", "RefactorPlanWorkflow"),
    "dependency-check": ("attune.workflows.dependency_check", "DependencyCheckWorkflow"),
}


class SoftwarePlugin(BasePlugin):
    """Software Development Domain Plugin.

    Provides workflows for code review, bug prediction, security audit,
    performance audit, test generation, refactoring, and dependency
    checking.
    """

    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="Attune Software Development",
            version="1.0.0",
            domain="software",
            description=(
                "Software development workflows for code analysis and "
                "anticipatory issue detection. Includes code review, bug "
                "prediction, security audit, performance audit, test "
                "generation, refactoring, and dependency checking."
            ),
            author="Smart AI Memory, LLC",
            license="Apache-2.0",
            requires_core_version="2.4.0",
            dependencies=[],
        )

    def register_workflows(self) -> dict[str, type[BaseWorkflow]]:
        """Register software development workflows.

        Each workflow is imported lazily so a missing optional dependency
        (e.g. ``anthropic``) only disables that one workflow instead of
        the entire plugin.
        """
        workflows: dict[str, type[BaseWorkflow]] = {}

        for wf_id, (module_path, class_name) in _WORKFLOW_MAP.items():
            try:
                mod = importlib.import_module(module_path)
                wf_class = getattr(mod, class_name)
                workflows[wf_id] = wf_class
            except (ImportError, AttributeError) as e:
                logger.warning("Workflow %s not available: %s", wf_id, e)

        logger.info("Software plugin registered %d workflows", len(workflows))
        return workflows

    def register_patterns(self) -> dict:
        """Register software development patterns.

        These patterns enable cross-domain learning (Level 5 Systems Empathy).
        """
        return {
            "domain": "software",
            "patterns": {
                "testing_bottleneck": {
                    "description": (
                        "Manual testing burden grows faster than team size. "
                        "Alert: When test count > 25 or test time > 15min, "
                        "recommend automation framework."
                    ),
                    "indicators": [
                        "test_count_growth_rate",
                        "manual_test_time",
                        "wizard_count",
                    ],
                    "threshold": "test_time > 900 seconds",
                    "recommendation": "Implement test automation framework",
                },
                "security_drift": {
                    "description": (
                        "Security practices degrade over time without active "
                        "monitoring. Alert: When new code bypasses security "
                        "patterns established in existing code."
                    ),
                    "indicators": [
                        "input_validation_coverage",
                        "authentication_consistency",
                        "data_sanitization_patterns",
                    ],
                },
            },
        }
