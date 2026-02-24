"""Default verification strategies per workflow.

Maps workflow names to their default verification strategy when
the user has configured ``strategy: "auto"`` (the default).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

# Workflow name -> default strategy name
DEFAULT_VERIFICATION_STRATEGIES: dict[str, str] = {
    # Code quality workflows -> lint
    "code-review": "lint-check",
    "bug-predict": "lint-check",
    "perf-audit": "lint-check",
    "security-audit": "lint-check",
    # Generation / refactor workflows -> run tests
    "test-gen": "run-tests",
    "test-gen-parallel": "run-tests",
    "refactor-plan": "run-tests",
    "simplify-code": "run-tests",
    # Release workflows -> build
    "release-prep": "build",
    "secure-release": "build",
    # Documentation workflows -> none (no meaningful verification)
    "doc-gen": "none",
    "doc-orchestrator": "none",
    "seo-optimization": "none",
    # Research workflows -> none
    "research-synthesis": "none",
}


def get_default_strategy(workflow_name: str) -> str:
    """Get the default verification strategy for a workflow.

    Args:
        workflow_name: The workflow slug (e.g. "code-review").

    Returns:
        Strategy name string. Returns "none" if no default is mapped.

    """
    return DEFAULT_VERIFICATION_STRATEGIES.get(workflow_name, "none")


__all__ = ["DEFAULT_VERIFICATION_STRATEGIES", "get_default_strategy"]
