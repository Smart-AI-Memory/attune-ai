---
description: Configuration Architecture: System architecture overview with components, data flow, and design decisions. Understand the framework internals.
---

# Configuration Architecture

This document explains the configuration schema separation in the Attune AI.

## Overview

The framework uses **two distinct configuration classes** for different concerns:

| Config Class | Location | Purpose |
|-------------|----------|---------|
| `AttuneConfig` | `src/attune/config.py` | Core empathy-level settings |
| `WorkflowConfig` | `src/attune/workflows/config.py` | Model routing and workflow settings |

## AttuneConfig

Handles core Attune AI settings that control the five-level empathy system.

### Fields

```python
@dataclass
class AttuneConfig:
    # Core settings
    user_id: str = "default_user"
    target_level: int = 3                    # Empathy level 1-5
    confidence_threshold: float = 0.75

    # Trust settings
    trust_building_rate: float = 0.05
    trust_erosion_rate: float = 0.10

    # Persistence settings
    persistence_enabled: bool = True
    persistence_backend: str = "sqlite"      # "sqlite", "json", "none"
    persistence_path: str = "./empathy_data"

    # State management
    state_persistence: bool = True
    state_path: str = "./empathy_state"

    # Metrics settings
    metrics_enabled: bool = True
    metrics_path: str = "./metrics.db"

    # Logging settings
    log_level: str = "INFO"
    log_file: str | None = None
    structured_logging: bool = True

    # Pattern library settings
    pattern_library_enabled: bool = True
    pattern_sharing: bool = True
    pattern_confidence_threshold: float = 0.3

    # Advanced settings
    async_enabled: bool = True
    feedback_loop_monitoring: bool = True
    leverage_point_analysis: bool = True

    # Custom metadata
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Loading

```python
from attune.config import AttuneConfig, load_config

# Direct instantiation
config = AttuneConfig(user_id="alice", target_level=4)

# From file (auto-detects .yml or .json)
config = AttuneConfig.from_file("empathy.config.yml")

# With environment variable overrides
config = load_config(use_env=True)
```

### Unknown Fields

As of v3.3.3, `AttuneConfig.from_yaml()` and `from_json()` **gracefully ignore unknown fields**. This allows config files to contain settings for other components (like `provider`, `model_preferences`) without breaking `AttuneConfig` loading.

## WorkflowConfig

Handles model routing and workflow-specific settings.

### Fields

```python
@dataclass
class WorkflowConfig:
    # Default provider for all workflows
    default_provider: str = "anthropic"

    # Per-workflow provider overrides
    workflow_providers: dict[str, str] = field(default_factory=dict)

    # Custom model mappings (provider -> tier -> model)
    custom_models: dict[str, dict[str, str]] = field(default_factory=dict)

    # Model pricing overrides
    pricing_overrides: dict[str, dict[str, float]] = field(default_factory=dict)

    # XML prompt configuration
    xml_prompt_defaults: dict[str, Any] = field(default_factory=dict)
    workflow_xml_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
```

### Loading

```python
from attune.workflows.config import WorkflowConfig

# Load from default locations
config = WorkflowConfig.load()

# Load from specific path
config = WorkflowConfig.load(".empathy/workflows.yaml")
```

## Config File Structure

The `empathy.config.yml` file can contain settings for **both** config classes:

```yaml
# empathy.config.yml

# ===== WorkflowConfig fields =====
provider: anthropic
model_preferences:
  cheap: claude-3-5-haiku-20241022
  capable: claude-sonnet-4-5-20250514
  premium: claude-opus-4-5-20251101

workflows:
  max_cost_per_run: 5.00
  xml_enhanced: true

# ===== AttuneConfig fields =====
user_id: default_user
target_level: 3
confidence_threshold: 0.75
persistence_enabled: true

# ===== Other component settings =====
memory:
  enabled: true
  redis_url: redis://localhost:6379

telemetry:
  enabled: true
  storage: jsonl
```

## Best Practices

1. **Use the right config class** for each context:
   - Building an EmpathyOS instance → `AttuneConfig`
   - Running workflows → `WorkflowConfig`

2. **Environment variables** follow different prefixes:
   - `ATTUNE_*` → AttuneConfig (e.g., `ATTUNE_USER_ID`)
   - `ATTUNE_WORKFLOW_*` → WorkflowConfig (e.g., `ATTUNE_WORKFLOW_PROVIDER`)

3. **Don't duplicate fields** between config classes. Each class owns its domain.

## Migration Notes

If you encounter `TypeError: AttuneConfig.__init__() got an unexpected keyword argument`:

1. Ensure you're using v3.3.3+ which filters unknown fields
2. Or manually filter the config data before passing to the constructor
3. Consider using the appropriate config class for your use case

## WorkflowConfig Naming Collision

**Important:** There are two classes named `WorkflowConfig` in the codebase:

| Class | Location | Purpose |
|-------|----------|---------|
| `WorkflowConfig` | `src/attune/workflows/config.py` | Model routing settings (provider, tiers) |
| `WorkflowConfig` | `attune_llm/config/unified.py` | Agent workflow execution settings |

These are **completely different classes** with different fields:

```python
# attune.workflows.config.WorkflowConfig (dataclass)
# Used for: Model routing and provider selection
WorkflowConfig(
    default_provider="anthropic",
    workflow_providers={"code_review": "openai"},
    custom_models={...}
)

# attune_llm.config.unified.WorkflowConfig (Pydantic)
# Used for: Agent workflow execution configuration
WorkflowConfig(
    name="my_workflow",
    mode="sequential",
    max_iterations=10,
    timeout_seconds=300
)
```

**Recommendation:** When importing, use explicit module paths:
```python
from attune.workflows.config import WorkflowConfig as ModelRoutingConfig
from attune.config.agent_config import WorkflowConfig as AgentWorkflowConfig
```

## Related Files

- `src/attune/config.py` - AttuneConfig implementation
- `src/attune/workflows/config.py` - WorkflowConfig (model routing)
- `attune_llm/config/unified.py` - WorkflowConfig (agent workflows)
- `src/attune/models/registry.py` - Model registry (source of model IDs)
- `empathy.config.yml` - Main configuration file
