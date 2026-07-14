---
type: task
name: models-task
feature: models
depth: task
generated_at: 2026-07-14T15:58:54.871943+00:00
source_hash: 52589e077700e250b69e496efaa9634a271c4f91bd520b4c07b4915347a04668
status: generated
---

# LLM authentication, provider routing, and tier management

## Tasks

### See which model a task will use

**Goal:** resolve the tier and concrete model for a task type without
running anything.

**Steps:**

```python
from attune.models import (
    get_tier_for_task,
    get_tasks_for_tier,
    get_model,
    is_known_task,
)

task = "review_security"
print(is_known_task(task))            # True
tier = get_tier_for_task(task)        # ModelTier.CAPABLE
model = get_model("anthropic", tier.value)
print(f"{task} -> {tier.value} -> {model.id if model else 'unregistered'}")

# What else runs at this tier?
print(get_tasks_for_tier(tier))       # list[str] of task names
```

**Verify:** `get_tier_for_task` returns a `ModelTier`. An unknown task
string does not raise — it defaults to `ModelTier.CAPABLE`; use
`is_known_task` first if you need to distinguish.

### Configure your authentication strategy

**Goal:** choose subscription vs API and persist the choice.

**Steps:** run the interactive CLI, then confirm it:

```bash
attune auth setup            # interactive: pick subscription tier + default mode
attune auth status           # human-readable summary
attune auth status --json    # machine-readable, for scripts/CI
```

Or programmatically:

```python
from attune.models import get_auth_strategy, AuthMode

strategy = get_auth_strategy()                 # zero-config default if unset
mode = strategy.get_recommended_mode(1800)     # API on a PRO account; size-based only on MAX/ENTERPRISE
estimate = strategy.estimate_cost(1800, mode)  # mode, monetary_cost, quota_cost, tokens_used, fits_in_context
print(mode.value, estimate)
strategy.save()                                # persists to AUTH_STRATEGY_FILE
```

**Verify:** `attune auth status --json` reports the active mode and
tier. `get_recommended_mode` returns an `AuthMode` member whose
`.value` is `"subscription"` or `"api"` — never `"auto"` (`AUTO` is the
input that triggers resolution). Note `setup_completed` defaults to
`true`, so status reports it `true` even before you run setup.

### Get a per-file auth recommendation

**Goal:** ask which mode a specific file should use, given its size.

**Steps:**

```bash
attune auth recommend src/attune/models/registry.py
```

The command counts the file's lines of code and prints the recommended
mode plus a cost estimate. The Python equivalent pairs
`count_lines_of_code` with `get_recommended_mode`:

```python
from attune.models import count_lines_of_code, get_auth_strategy

loc = count_lines_of_code("src/attune/models/registry.py")
mode = get_auth_strategy().get_recommended_mode(loc)
print(loc, mode.value)
```

**Verify:** the CLI exits `0` and names a mode. `count_lines_of_code`
counts non-blank, non-comment lines, so its result is smaller than a
raw `wc -l`.

### Change the provider configuration

**Goal:** inspect or set the active provider.

**Steps:**

```bash
attune provider show         # print current provider + mode
attune provider set          # interactive provider selection
```

Programmatically:

```python
from attune.models import get_provider_config, set_provider_config, ProviderConfig

cfg = get_provider_config()                    # lazy-loaded global
print(cfg.mode, cfg.primary_provider)          # ProviderMode.SINGLE anthropic

cfg = ProviderConfig.auto_detect()             # detect ANTHROPIC_API_KEY
set_provider_config(cfg)                        # install as the global
```

**Verify:** `attune provider show` reflects the change.
`ProviderConfig.auto_detect()` returns a config whose
`available_providers` includes `"anthropic"` when `ANTHROPIC_API_KEY`
is set.

### Reset auth configuration

**Goal:** clear a misconfigured auth strategy.

**Steps:**

```bash
attune auth reset --confirm
```

**Verify:** the configuration file is removed; a subsequent
`attune auth status` shows the zero-config default and prompts you to
run `attune auth setup`.
