"""Configuration management for Attune AI.

This package provides:
1. AttuneConfig (with EmpathyConfig backward-compatible alias)
2. XML enhancement configurations (new)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

# Import original config from parent module's config.py for backward compatibility
import importlib.util
import sys
from pathlib import Path

# Check if PyYAML is available
try:
    import yaml  # noqa: F401

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Load the original config.py module directly
config_py_path = Path(__file__).parent.parent / "config.py"
spec = importlib.util.spec_from_file_location("attune_config_legacy", config_py_path)
if spec and spec.loader:
    legacy_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_config)
    AttuneConfig = legacy_config.AttuneConfig
    EmpathyConfig = legacy_config.EmpathyConfig  # backward-compat alias
    load_config = legacy_config.load_config
    _validate_file_path = legacy_config._validate_file_path
else:
    # Fallback if import fails
    AttuneConfig = None
    EmpathyConfig = None
    load_config = None
    _validate_file_path = None

# Import XML enhancement configs
# Import agent configuration models
from attune.config.agent_config import (  # noqa: E402
    AgentOperationError,
    BookProductionConfig,
    MemDocsConfig,
    ModelTier,
    Provider,
    RedisConfig,
    UnifiedAgentConfig,
    WorkflowMode,
)
from attune.config.agent_config import (  # noqa: E402
    WorkflowConfig as AgentWorkflowConfig,
)
from attune.config.xml_config import (  # noqa: E402
    AdaptiveConfig,
    EmpathyXMLConfig,
    I18nConfig,
    MetricsConfig,
    OptimizationConfig,
    XMLConfig,
    get_config,
    set_config,
)

__all__ = [
    # Original config
    "AttuneConfig",
    "EmpathyConfig",
    "load_config",
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
