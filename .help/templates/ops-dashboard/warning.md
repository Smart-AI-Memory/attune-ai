---
type: warning
name: ops-dashboard-warning
feature: ops-dashboard
depth: warning
generated_at: 2026-05-16T06:19:45.806518+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Ops Dashboard cautions

## What to watch for

The ops dashboard (`attune ops`) is a local FastAPI server that exposes a scope-aware workflow runner, persisted run history, SSE log streaming, and a session browser. Because it binds to a network port and can execute workflows when `allow_run=True`, a few configuration and startup decisions carry more risk than their defaults suggest.

## Risk areas

### `allow_run` defaults to `False` — verify it before expecting run buttons to work

`Config.allow_run` is `False` by default, which disables workflow execution from the UI. If you start the server without explicitly setting `allow_run=True`, the dashboard loads without error but all run actions silently do nothing. Pass the flag deliberately rather than relying on environment-level defaults that may differ between local and CI environments.

### `TrustedHostMiddleware` rejects requests whose `Host` header isn't on the allowlist

If you access the dashboard through a proxy, a tunneling tool (such as `ngrok`), or a non-loopback interface, the `Host` header in incoming requests may not match the values in `Config.trusted_hosts`. The middleware returns a rejection response — not a redirect or an explanation — so the failure can look like a network error rather than a configuration problem. Add every hostname and IP you intend to use to `trusted_hosts` before starting the server.

### `build_config()` silently falls back to `~/.attune` when `ATTUNE_HOME` is unset

`attune_home()` resolves the attune home directory first from an environment variable, then from `~/.attune`. If `ATTUNE_HOME` is set to a stale or wrong path in one shell but not another, two instances of the dashboard will read from different `telemetry_path`, `runs_dir`, and `sessions_dir` locations. This makes run history and telemetry appear inconsistent across sessions. Set `ATTUNE_HOME` explicitly in any environment where the default is not appropriate.

### `runs_retention_days` silently drops run history older than 30 days

`Config.runs_retention_days` defaults to `30`. Runs older than this threshold are purged from `runs_dir` without prompting. If you depend on long-lived run history for auditing or reporting, override this value in your `build_config()` call before the dashboard processes its first cleanup cycle.

### `create_app()` and `build_config()` use lazy imports — import order affects availability

Both `create_app()` and `build_config()` in `attune.ops` delay their real imports so that importing the `attune` package doesn't pull in FastAPI. If you call either function in a context where FastAPI or its dependencies are not installed, you will get an `ImportError` at call time, not at import time. This means import-time checks won't catch a missing dependency — test the call path explicitly in environments where the dependency set may be reduced.

### `specs_roots` defaults to an empty tuple — no workflow specs are loaded silently

`Config.specs_roots` is an empty tuple by default. If you start the dashboard without providing at least one path, the scope picker and workflow list render empty rather than raising an error. Confirm that `specs_roots` contains at least one valid path and that those paths are accessible from the process's working directory.

## How to avoid problems

- **Pin your configuration explicitly.** Construct `Config` (or call `build_config()`) with all non-default values stated in code or a controlled config file. Relying on environment variable fallbacks makes behavior differ across machines.
- **Check `trusted_hosts` before deploying behind any proxy.** Add every hostname variant — `localhost`, `127.0.0.1`, and any tunnel domain — to `trusted_hosts` before the server starts.
- **Do not depend on private helpers.** Names starting with `_` (such as `_PHASE_FILES`, `_VALID_STATUSES`, `_PLACEHOLDER`) can change without notice. Use only the public API exported through `__all__`: `create_app`, `build_config`, and `Config`.
- **Test with the full call path.** Because lazy imports defer `ImportError` to call time, include at least one integration test that actually invokes `create_app()` and `build_config()` in any environment where you trim optional dependencies.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
