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
    WorkflowMode,
)
from attune.config.agent_config import (
    WorkflowConfig as AgentWorkflowConfig,
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
