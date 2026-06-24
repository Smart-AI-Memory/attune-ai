---
name: configuration
source: content/features/configuration.md
tags:
- config
- settings
type: task
---

# Layered configuration — the unified config tree, agent config, and the XML/empathy config layer

## Tasks

### Load and validate the unified config

**Goal:** get a typed `UnifiedConfig` and check it.

**Steps:**

```python
from attune.config.loader import load_unified_config
from attune.config.validation import validate_config

cfg = load_unified_config()
for err in validate_config(cfg):
    print(err)
```

**Verify:** `load_unified_config()` returns a `UnifiedConfig`;
`validate_config(cfg)` returns a `list[ValidationError]` (empty when the
config is valid).

### Read or write a nested value by key path

**Goal:** access a deeply nested field without walking sections.

**Steps:**

```python
from attune.config.loader import load_unified_config

cfg = load_unified_config()
keys = cfg.get_all_keys()          # every settable key path
value = cfg.get_value("routing.default_tier")
cfg.set_value("routing.default_tier", "capable")
```

**Verify:** `get_all_keys()` lists the key paths; `get_value` /
`set_value` read and write by dotted path.

### Override config from the environment

**Goal:** change a value without editing the file.

**Steps:** set an `ATTUNE_`-prefixed variable (the loader applies it
over the file value). `get_attune_env` also accepts the legacy
`EMPATHY_` prefix as a fallback.

```python
from attune.config.env_compat import get_attune_env

# reads ATTUNE_LOG_LEVEL, then EMPATHY_LOG_LEVEL, then the default
level = get_attune_env("LOG_LEVEL", default="INFO")
```

**Verify:** `get_attune_env(name, default)` returns the `ATTUNE_`-
prefixed value if set, else the `EMPATHY_`-prefixed value, else the
default.

### Load the legacy dataclass

**Goal:** interoperate with code that still uses `AttuneConfig`.

**Steps:**

```python
from attune.config import load_config

cfg = load_config()                # -> AttuneConfig (== EmpathyConfig)
```

**Verify:** `load_config(filepath=None, use_env=True)` returns an
`AttuneConfig`; it is the legacy dataclass, distinct from `UnifiedConfig`.
