---
type: error
name: ops-dashboard-error
feature: ops-dashboard
depth: error
generated_at: 2026-05-16T06:19:45.800719+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Ops Dashboard errors

## Common error signatures

These failures occur when starting, configuring, or running the `attune ops` dashboard server.

| Symptom | Likely cause |
|---|---|
| `ImportError` on `attune ops` startup | `create_app()` triggers a lazy FastAPI import that fails — FastAPI is not installed or the import path is broken |
| `OSError` or `FileNotFoundError` at boot | `build_config()` cannot resolve `project_root` or `attune_home`; the computed `runs_dir`, `memory_dir`, or `sessions_dir` path does not exist and cannot be created |
| `400` / `403` response from the dashboard | `TrustedHostMiddleware.dispatch()` rejected a request whose `Host` header is not in `Config.trusted_hosts` |
| Dashboard exits immediately with a non-zero code | `cmd_ops()` failed to bind to `Config.host`:`Config.port` (default `127.0.0.1:8765`), or an unhandled exception escaped the blocking server loop |
| `KeyError` or `ValueError` reading features | `list_features()` could not parse `.help/features.yaml` under `project_root` — the file is missing, malformed, or contains an unrecognised field |
| Empty scope on first workflow paint | `workflow_default_scope()` returned `''` — no feature with a renderable scope exists under `project_root` |

## Where errors originate

- **`build_config()`** — constructs the `Config` dataclass from CLI arguments and environment defaults. Failures here mean the dashboard never reaches the bind step.
- **`create_app()`** — performs the lazy FastAPI import and wires middleware (including `TrustedHostMiddleware`). An `ImportError` here means no server starts.
- **`cmd_ops()`** — the blocking entrypoint called by `attune ops`. Any uncaught exception propagates as a non-zero exit code.
- **`main()`** — the `python -m attune.ops` entrypoint; delegates to `cmd_ops()` and returns its exit code.
- **`list_features()` / `first_feature()`** — read `.help/features.yaml`; failures affect the scope picker but may also prevent the dashboard UI from rendering correctly.

## How to diagnose

1. **Locate the raise site.** Run `attune ops` in a terminal where you can see the full traceback. The file path and line number in the last frame identify whether the failure is in config building, server startup, or middleware.

2. **Check path resolution.** Most `OSError` failures trace back to a bad `project_root` or missing `attune_home`. Confirm that:
   - `ATTUNE_HOME` (if set) points to a writable directory.
   - `project_root` contains a `.help/features.yaml` file if the scope picker is used.
   - `Config.runs_dir` (`<attune_home>/ops/runs`) is writable on first write.

3. **Verify host and port configuration.** If the server exits immediately without a traceback, another process may already hold `127.0.0.1:8765`. Pass `--host` and `--port` overrides to `build_config()`, or check with `lsof -i :8765`.

4. **Check `trusted_hosts` when you get 400/403 responses.** `TrustedHostMiddleware` rejects any request whose `Host` header is absent from `Config.trusted_hosts`. Add the host you are accessing the dashboard from to the `trusted_hosts` tuple in your config.

5. **Inspect `.help/features.yaml` for parse errors.** If `list_features()` raises, open the file directly and confirm every entry has `name`, `description`, and an optional `path`. An unexpected key or a YAML syntax error will surface as a `KeyError` or a YAML parser exception.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
