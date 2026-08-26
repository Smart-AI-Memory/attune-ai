"""Configuration section dataclasses for Attune AI.

This package contains the individual configuration section dataclasses
that compose the UnifiedConfig.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.config.sections.analysis import AnalysisConfig
from attune.config.sections.auth import AuthConfig
from attune.config.sections.environment import EnvironmentConfig
from attune.config.sections.persistence import PersistenceConfig
from attune.config.sections.routing import RoutingConfig
from attune.config.sections.telemetry import TelemetryConfig
from attune.config.sections.workflows import WorkflowsConfig

__all__ = [
    "AnalysisConfig",
    "AuthConfig",
    "EnvironmentConfig",
    "PersistenceConfig",
    "RoutingConfig",
    "TelemetryConfig",
    "WorkflowConfig",  # REMOVE IN v16.0.0 — deprecated alias
    "WorkflowsConfig",
]


def __getattr__(name: str) -> object:
    """Serve the deprecated `WorkflowConfig` name. REMOVE IN v16.0.0."""
    if name != "WorkflowConfig":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import warnings

    warnings.warn(
        "attune.config.sections.WorkflowConfig is deprecated and will be "
        "removed in v16.0.0. Use WorkflowsConfig instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return WorkflowsConfig
