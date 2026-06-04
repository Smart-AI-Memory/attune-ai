---
type: warning
name: configuration-warning
feature: configuration
depth: warning
generated_at: 2026-06-04T23:45:26.711774+00:00
source_hash: b67c4428689dde6c18aca17808e3037eded03448162cc3406741340bbe33b804
status: generated
---

# Configuration cautions

## Risk areas

### Silent fallback in `get_attune_env()` masks missing variables

`get_attune_env()` checks `ATTUNE_` prefixed variables first, then silently falls back to the legacy `EMPATHY_` prefix. If you rename an environment variable from `EMPATHY_*` to `ATTUNE_*` in one environment but not another, the function returns the stale `EMPATHY_` value without any warning. You will not see an error — just behavior driven by an outdated variable.

**Mitigation:** After migrating variable names, explicitly verify that no `EMPATHY_` counterparts remain set in your environment. Search your shell configuration, CI secrets, and deployment manifests.

---

### `get_loader()` returns a shared global instance

`get_loader()` returns a single global `ConfigLoader` instance. Calling `ConfigLoader.apply_env_overrides()` or mutating the config through `set_value()` on that instance affects every caller in the same process. In tests, this means a configuration change in one test can leak into later tests.

**Mitigation:** In test code, construct a separate `ConfigLoader` instance directly rather than using `get_loader()`. Reset any shared state explicitly between tests.

---

### `load_unified_config()` path discovery can load an unexpected file

When you call `load_unified_config()` without a `path` argument, `ConfigLoader.discover_config_path()` searches the following locations in order:

- `./attune.config.json`
- `~/.attune/config.json`
- `~/.config/attune/config.json`

If a file exists at a higher-priority path that you did not intend to use — for example, a leftover `./attune.config.json` in the working directory — it silently takes precedence over your user-level config. Behavior differs between environments without any error.

**Mitigation:** Pass an explicit `path` argument to `load_unified_config()` in production code and CI scripts. Reserve path-discovery for interactive use only.

---

### `save_unified_config()` overwrites without a backup

`save_unified_config()` writes the `UnifiedConfig` to disk immediately. There is no built-in versioning, confirmation step, or rollback mechanism. Passing a partially constructed `UnifiedConfig` — for example, one where `validate_config()` returns `ValidationError` items — will overwrite a valid config file with invalid data.

**Mitigation:** Call `validate_config(config)` and confirm the returned list is empty before calling `save_unified_config()`. Consider writing to a temporary path first and renaming only on success.

---

### `iter_attune_env_prefix()` yields unexpected keys when the suffix is empty

`iter_attune_env_prefix(prefix, suffix='')` matches any environment variable of the form `ATTUNE_{prefix}*{suffix}`. With the default empty suffix, this is a prefix-only match, so an environment that contains loosely named variables (for example, `ATTUNE_MODEL_EXTRA_DEBUG`) can produce unexpected entries alongside the ones you intended to iterate.

**Mitigation:** Pass an explicit `suffix` when you need to narrow the match. Enumerate the yielded `(middle_part, value)` pairs in a log statement during development to confirm you are capturing exactly the variables you expect.

---

### `set_config()` replaces the process-wide `EmpathyXMLConfig` instance

`set_config()` overwrites the global `EmpathyXMLConfig` returned by every subsequent call to `get_config()`. Calling it mid-request or during concurrent operations leaves part of the call graph using the old config and part using the new one, with no coordination between them.

**Mitigation:** Call `set_config()` only during application startup, before any concurrent work begins. Treat the global config as immutable after that point.

---

## How to avoid problems

1. **Validate before saving.** Call `validate_config(config)` and check that it returns an empty list before persisting changes with `save_unified_config()`.

2. **Isolate global state in tests.** Avoid `get_loader()` and `get_config()` in test code. Instantiate `ConfigLoader` directly and pass config objects explicitly to keep tests independent.

3. **Prefer explicit paths in automation.** Supply a `path` argument to `load_unified_config()` and `save_unified_config()` in scripts and CI pipelines so the file being read or written is always unambiguous.

4. **Depend only on the public API.** Names starting with `_` — such as `_validate_file_path` — can change without notice. Use the exported names listed in `__all__` instead.
