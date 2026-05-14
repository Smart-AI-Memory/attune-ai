---
type: warning
name: ops-dashboard-warning
feature: ops-dashboard
depth: warning
generated_at: 2026-05-14T14:43:23.564490+00:00
source_hash: 395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Ops Dashboard Warnings

## What to watch for

The `attune ops` dashboard is a blocking server process with lazy-loaded dependencies, host-allowlist enforcement, and persisted run history. The risks below apply whether you are running the dashboard directly, embedding it in another process, or writing code that imports from `attune.ops`.

## Risk areas

### `allow_run` defaults to `False` — workflows will not execute without it

`build_config()` sets `allow_run=False` by default. If you start the dashboard without explicitly passing `allow_run=True`, the workflow runner is disabled and no runs are recorded. This is intentional as a safety default, but it is easy to miss when standing up a new environment and wondering why runs never appear in history.

**Mitigation:** Pass `allow_run=True` explicitly when you intend to execute workflows, and verify the `Config` object your app receives before assuming the runner is active.

---

### `trusted_hosts` left empty opens the dashboard to host-header spoofing

`TrustedHostMiddleware` rejects requests whose `Host` header is not on the allowlist. If you pass an empty `trusted_hosts` tuple to `build_config()`, the middleware has nothing to enforce and all `Host` values are accepted. In a network-accessible deployment this allows host-header injection attacks.

**Mitigation:** Always populate `trusted_hosts` with the exact hostnames (and port, if non-standard) the dashboard should answer to. The default bind address is `127.0.0.1:8765`; if you change `host` or `port`, update `trusted_hosts` to match.

---

### Lazy imports in `create_app()` and `build_config()` defer errors until call time

Both functions use lazy imports so that `import attune` does not pull in FastAPI or the config builder at module load. This means import errors and missing dependencies surface only when you first call the function, not when the module is imported — which can make failures appear in unexpected places during startup.

**Mitigation:** Call `create_app()` and `build_config()` early in your startup path (not on first request) so any import failures surface immediately and with a clear traceback.

---

### `runs_dir` does not exist until the first write

`Config.runs_dir` is a property that returns the disk path for persisted ops runs, but the directory is not created until the first run is written. Code that stats or lists `runs_dir` before any run has completed will encounter a missing directory.

**Mitigation:** Check for existence with `runs_dir.exists()` before reading from it, or create the directory explicitly during initialization if your code depends on it being present.

---

### `runs_retention_days` silently drops old run history

`build_config()` defaults `runs_retention_days` to `30`. Runs older than this threshold are eligible for deletion. If you lower this value in a long-running deployment, previously visible history disappears without an explicit deletion event.

**Mitigation:** Treat `runs_retention_days` as a deployment-level decision and document its value alongside your other ops configuration. Avoid changing it in production without first archiving runs you want to keep.

---

### Private helpers and module constants can change without notice

`_PHASE_FILES`, `_VALID_STATUSES`, and other underscore-prefixed names are implementation details. They are not part of the public API (see `__all__`: `create_app`, `build_config`, `Config`) and may change between releases.

**Mitigation:** Depend only on the names listed in `__all__`. If you need access to phase-file names or valid status values in your own code, define them locally rather than importing the private constants.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
