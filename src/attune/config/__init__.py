"""Configuration management for Attune AI.

This package provides:
1. AttuneConfig (with EmpathyConfig backward-compatible alias)
2. XML enhancement configurations (new)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

# Agent configuration models
from attune.config.agent_config import (
    AgentOperationError,
    BookProductionConfig,
    MemDocsConfig,
    ModelTier,
    Provider,
    RedisConfig,
    UnifiedAgentConfig,
)

# Original config module (formerly the sibling config.py, loaded via
# spec_from_file_location under a synthetic name; now a real submodule
# so AttuneConfig keeps a stable __module__ for isinstance and pickling)
from attune.config.legacy import (
    YAML_AVAILABLE,
    AttuneConfig,
    EmpathyConfig,
    load_config,
    resolve_show_cost,
)

# XML enhancement configs
from attune.config.xml_config import (
    AdaptiveConfig,
    EmpathyXMLConfig,
    I18nConfig,
    MetricsConfig,
    OptimizationConfig,
    XMLConfig,
    get_config,
    set_config,
)
from attune.security.path_validation import _validate_file_path

__all__ = [
    # Original config
    "AttuneConfig",
    "EmpathyConfig",
    "load_config",
    "resolve_show_cost",
    "YAML_AVAILABLE",
    "_validate_file_path",
    # XML enhancement configs
    "XMLConfig",
    "OptimizationConfig",
    "AdaptiveConfig",
    "I18nConfig",
    "MetricsConfig",
    "EmpathyXMLConfig",
    "get_config",
    "set_config",
    # Agent configuration models
    "AgentOperationError",
    "BookProductionConfig",
    "MemDocsConfig",
    "ModelTier",
    "Provider",
    "RedisConfig",
    "UnifiedAgentConfig",
    "AgentWorkflowConfig",
    "WorkflowMode",
]


# --- Deprecated re-exports -------------------------------------------------
# REMOVE IN v16.0.0
#
# ``AgentWorkflowConfig`` is ``config.agent_config.WorkflowConfig``, a
# field-for-field pydantic twin of ``agent_factory.base.WorkflowConfig``
# with no consumer in this tree (spec models-workflows-layering, D4 —
# chair ruled DELETE; D6 moved the timing to the next major so a
# six-month-old public export is not removed without notice).
# ``WorkflowMode`` is that class's only remaining reason to exist and
# goes with it.
#
# Served through module ``__getattr__`` (PEP 562) so the warning fires on
# ACCESS, not on ``import attune.config`` — an eager import would warn
# every consumer of this package for a symbol they never touch.
_DEPRECATED_EXPORTS = {
    "AgentWorkflowConfig": ("WorkflowConfig", "attune.agent_factory.base.WorkflowConfig"),
    "WorkflowMode": ("WorkflowMode", None),
}


def __getattr__(name: str) -> object:
    """Serve deprecated re-exports with a warning. REMOVE IN v16.0.0."""
    entry = _DEPRECATED_EXPORTS.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import warnings

    from attune.config import agent_config as _agent_config

    attr, replacement = entry
    hint = f" Use {replacement} instead." if replacement else ""
    msg = f"attune.config.{name} is deprecated and will be removed in v16.0.0.{hint}"
    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    return getattr(_agent_config, attr)
