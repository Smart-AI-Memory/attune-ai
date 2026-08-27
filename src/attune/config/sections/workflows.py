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
