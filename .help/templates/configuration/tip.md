---
type: tip
name: configuration-tip
feature: configuration
depth: tip
generated_at: 2026-06-04T23:45:26.721393+00:00
source_hash: b67c4428689dde6c18aca17808e3037eded03448162cc3406741340bbe33b804
status: generated
---

# Tip: Use `load_unified_config()` as your entry point

Call `load_unified_config()` rather than constructing a `ConfigLoader` directly. It applies environment variable overrides automatically and searches the standard config paths (`./attune.config.json`, `~/.attune/config.json`, `~/.config/attune/config.json`) without you having to wire that logic yourself.

**Why:** `ConfigLoader.apply_env_overrides()` respects the `ATTUNE_` prefix and the `EMPATHY_` fallback — both of which you lose if you load a config file and skip that step.

**Tradeoff:** `load_unified_config()` always resolves the path through `ConfigLoader.discover_config_path()`. If you need to load from an explicit, non-standard path in a test or script, pass that path directly: `load_unified_config(path="my/custom/config.json")`. In that case you still get override resolution, but path discovery is bypassed.

**Reading environment variables directly?** Use `get_attune_env(name)` instead of `os.environ.get()`. It checks `ATTUNE_{name}` first and falls back to `EMPATHY_{name}`, which keeps your code consistent with how the loader itself reads the environment. To iterate a namespace of related variables, use `iter_attune_env_prefix(prefix)`.

**Tags:** `config`, `settings`
