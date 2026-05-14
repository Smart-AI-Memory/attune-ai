---
type: error
name: ops-dashboard-error
feature: ops-dashboard
depth: error
generated_at: 2026-05-14T14:43:23.558593+00:00
source_hash: 395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Ops Dashboard errors

## Common error signatures

Errors in the ops dashboard typically fall into three categories:

- **Configuration errors** — `build_config()` raises when required paths are missing or environment defaults cannot be resolved. Check that `project_root` exists and that `ATTUNE_HOME` (or `~/.attune`) is readable.
- **Server startup errors** — `cmd_ops()` or `main()` fail to bind the FastAPI server. Common causes include the configured `host`/`port` (default `127.0.0.1:8765`) already being in use, or FastAPI not being installed in the current environment.
- **Rejected requests (`403`)** — `TrustedHostMiddleware.dispatch()` rejects any request whose `Host` header is not in the `trusted_hosts` allowlist. Add the originating host to `trusted_hosts` in your `Config`.
- **Missing data directories** — Accessors such as `Config.runs_dir`, `Config.memory_dir`, and `Config.sessions_dir` resolve paths under `attune_home` that may not exist until the first write. Code that reads from these paths before any run has completed can raise `FileNotFoundError`.
- **Invalid spec phase status** — Phase file readers validate `status` against `_VALID_STATUSES`. A value outside `{'draft', 'in-review', 'approved', 'complete', 'completed', 'done'}` produces a validation error surfaced in the `SpecPhase` snapshot.
- **Missing features file** — `list_features()` and `first_feature()` parse `<project_root>/.help/features.yaml`. If that file is absent or malformed, these functions raise and the scope picker cannot populate.

## Where errors originate

| Entry point | What it does | Likely failure |
|---|---|---|
| `build_config()` | Assembles a `Config` from arguments and environment defaults | Bad paths, unresolvable `attune_home` |
| `create_app()` | Lazily imports the FastAPI factory | `ImportError` if FastAPI is not installed |
| `cmd_ops()` | Starts the blocking dashboard server | Port conflict, missing config values |
| `main()` | Standalone entry (`python -m attune.ops`) | Any error from `cmd_ops()` propagates here |
| `list_features()` / `first_feature()` | Reads `.help/features.yaml` | `FileNotFoundError`, YAML parse error |

## How to diagnose

1. **Read the exception type and message first.** An `ImportError` pointing at FastAPI means the dependency is missing. An `OSError` or `FileNotFoundError` points to a path problem. A `400`/`403` HTTP status from `TrustedHostMiddleware` means a host header mismatch.

2. **Verify your `Config` values.** Print or log the `Config` dataclass after `build_config()` returns. Confirm that `project_root`, `attune_home`, `host`, and `port` match your environment. Remember that `runs_dir`, `memory_dir`, and `sessions_dir` are derived properties — they reflect whatever `attune_home` resolved to.

3. **Check whether the data directories exist.** If `Config.runs_dir` or `Config.sessions_dir` does not exist yet, any code that tries to read from them before the first write will fail. Create the directories manually or run the dashboard at least once to let it initialize them.

4. **Confirm `trusted_hosts` covers your client.** If the dashboard returns `403`, compare the `Host` header your client sends against the `trusted_hosts` tuple in your `Config`. Add the missing host or adjust your client's request headers.

5. **Validate `.help/features.yaml`.** If the scope picker is blank or `list_features()` raises, open `<project_root>/.help/features.yaml` and confirm it is valid YAML. Each entry must supply at least `name` and `description`; `path` and `tags` are optional.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
