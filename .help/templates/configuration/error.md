---
type: error
name: configuration-error
feature: configuration
depth: error
generated_at: 2026-06-04T23:45:26.705556+00:00
source_hash: b67c4428689dde6c18aca17808e3037eded03448162cc3406741340bbe33b804
status: generated
---

# Configuration errors

Configuration errors in Attune fall into three categories: missing or unresolvable config files, invalid or unrecognized field values, and environment variable mismatches.

## Common error signatures

| Symptom | Likely cause |
|---|---|
| `FileNotFoundError` from `ConfigLoader.load()` | None of the search paths (`./attune.config.json`, `~/.attune/config.json`, `~/.config/attune/config.json`) contain a readable file and no path was passed explicitly. |
| `ValidationError` returned by `validate_config()` | A `UnifiedConfig` field contains a value that fails `ConfigValidator.validate_section()` — for example, an unrecognized `WorkflowMode` or an empty required field in `AuthConfig`. |
| `AgentOperationError` wrapping another exception | `UnifiedAgentConfig` caught an exception during an agent operation and re-raised it with operation context. Inspect `cause` for the original error. |
| `KeyError` or `AttributeError` from `UnifiedConfig.get_value()` | The key passed does not appear in `get_all_keys()` — often a typo or a key from an older config schema. |
| `EmpathyXMLConfig.load_from_file()` raises `FileNotFoundError` or `JSONDecodeError` | `.attune/config.json` is absent, empty, or not valid JSON. |
| Environment variable silently ignored | The variable was set with the legacy `EMPATHY_` prefix but the code now reads `ATTUNE_` first via `get_attune_env()`. The `EMPATHY_` value is used only as a fallback. |

## Where errors originate

- **`ConfigLoader.load()`** — Attempts to read from the discovered or default config path. Fails with a filesystem error if the file is missing or unreadable. Call `ConfigLoader.discover_config_path()` beforehand to confirm which path the loader resolves to.
- **`load_unified_config(path)`** — Wraps `ConfigLoader.load()`; passing `None` triggers automatic path discovery against `CONFIG_SEARCH_PATHS`. If discovery returns nothing, the loader falls back to `ConfigLoader.get_default_config_path()`.
- **`validate_config(config)`** — Returns a list of `ValidationError` objects rather than raising. An empty return value means the config is valid. A non-empty list means one or more sections failed `ConfigValidator.validate_section()`.
- **`get_attune_env(name)`** — Checks `ATTUNE_{name}` first, then `EMPATHY_{name}`. Returns `None` (not an exception) when neither is set, so callers that do not check the return value may propagate `None` silently.
- **`EmpathyXMLConfig.load_from_file()`** — Reads `.attune/config.json` by default. Any parse failure raises immediately and is not caught internally.

## How to diagnose

1. **Check which config file was loaded.** Call `ConfigLoader.discover_config_path()` to see which path the loader resolved, or `ConfigLoader.get_default_config_path()` to see the fallback. If `discover_config_path()` returns `None`, no file matched any of the `CONFIG_SEARCH_PATHS` entries.

2. **Run `validate_config()` explicitly and inspect the list.** `validate_config()` returns `list[ValidationError]`, not an exception — iterate the result and print each `ValidationError` to identify which section and field failed. A return value of `[]` means validation passed.

3. **Check the `AgentOperationError.cause` attribute.** When you catch an `AgentOperationError`, the wrapped `cause` exception holds the original traceback. Log or print `cause` before handling the outer error to avoid losing the root cause.

4. **Audit environment variable names.** Use `iter_attune_env_prefix(prefix)` to list all `ATTUNE_{prefix}*` variables currently set. If you expect a value and `get_attune_env(name)` returns `None`, confirm the variable is spelled with the `ATTUNE_` prefix, not only `EMPATHY_`.

5. **Validate the JSON config file independently.** If `EmpathyXMLConfig.load_from_file()` fails, open `.attune/config.json` in a JSON linter before re-running. An empty file or a trailing comma produces a `JSONDecodeError` that is otherwise reported without the offending line number.

## Source files

- `src/attune/config/**`

**Tags:** `config`, `settings`
