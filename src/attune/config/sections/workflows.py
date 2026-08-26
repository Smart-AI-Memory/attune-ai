"""Workflow execution configuration section.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass


@dataclass
class WorkflowsConfig:
    """Workflow execution configuration.

    Controls default workflow behavior, execution settings,
    and result caching.

    Attributes:
        default_workflow: Default workflow to run when none specified.
        parallel_execution: Enable parallel execution of workflow steps.
        timeout_seconds: Maximum time for workflow execution.
        cache_results: Cache workflow results for reuse.

    """

    default_workflow: str = "code-review"
    parallel_execution: bool = False
    timeout_seconds: int = 300
    cache_results: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "default_workflow": self.default_workflow,
            "parallel_execution": self.parallel_execution,
            "timeout_seconds": self.timeout_seconds,
            "cache_results": self.cache_results,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowsConfig":
        """Create from dictionary."""
        return cls(
            default_workflow=data.get("default_workflow", "code-review"),
            parallel_execution=data.get("parallel_execution", False),
            timeout_seconds=data.get("timeout_seconds", 300),
            cache_results=data.get("cache_results", True),
        )


# REMOVE IN v16.0.0 — deprecated alias for the pre-rename name.
# Renamed to `WorkflowsConfig` so it matches its module and config key,
# as its six sibling sections already do (AnalysisConfig, AuthConfig,
# EnvironmentConfig, PersistenceConfig, RoutingConfig, TelemetryConfig).
# Spec models-workflows-layering D2/D5.
#
# Served via module __getattr__ (PEP 562) so the warning fires on ACCESS.
# A plain module-level alias would be silent, and a user would learn of
# the rename only when v16.0.0 broke them.
def __getattr__(name: str) -> object:
    """Serve the deprecated `WorkflowConfig` name. REMOVE IN v16.0.0."""
    if name != "WorkflowConfig":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import warnings

    warnings.warn(
        "attune.config.sections.workflows.WorkflowConfig is deprecated and "
        "will be removed in v16.0.0. Use WorkflowsConfig instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return WorkflowsConfig
