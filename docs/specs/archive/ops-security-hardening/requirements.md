# Requirements — Ops Dashboard Security Hardening

**Status:** complete (2026-05-16)

See `decisions.md` for context, `design.md` for the implementation shape, `tasks.md` for the phase plan.

---

## Scope

**In scope:**
- Host header allowlist (TrustedHost middleware)
- `--trusted-host` repeatable CLI flag
- Warning when `--host 0.0.0.0` is used without explicit `--trusted-host`
- Subscriber queue bound (`maxsize=1000`) + test
- Structured logging on the run-view route
- End-to-end "output survives refresh" test

**Out of scope:** see `decisions.md`.

---

## User stories

### US-1 — DNS-rebinding attack fails

**As Pat, when I have `attune ops` running and I visit a malicious website that attempts a DNS-rebinding attack, the website's POST to `localhost:8766/workflows/release-prep/run` fails with 400 — no workflow runs.**

Acceptance:
- The attack pattern documented in `decisions.md` is blocked at the middleware layer before the route handler runs.
- The rejected request returns `400 Bad Request` with body `{"detail": "untrusted Host header"}` (or similar).
- The rejection is logged at WARN with the offending `Host:` value (sanitized — no full headers).

### US-2 — Loopback and default access still work

**As Pat, when I run `attune ops` and visit `http://localhost:8766` or `http://127.0.0.1:8766` in my browser, the dashboard loads normally. No new friction.**

Acceptance:
- `localhost:<port>` and `127.0.0.1:<port>` are on the default allowlist.
- `curl http://localhost:8766/api/info` works without configuration.
- The dashboard renders all tabs without errors.

### US-3 — Tunneled / proxied setups work via `--trusted-host`

**As a developer accessing `attune ops` through a Cloudflare Tunnel or Tailscale or remote SSH port-forward, I can add my external hostname to the allowlist via a repeatable CLI flag.**

Acceptance:
- `attune ops --trusted-host my-tunnel.example.com --trusted-host my-other.example.com` adds both hostnames.
- The `--trusted-host` value can include a port (`example.com:8443`) or not (defaults to standard 80/443).
- Without a port, both http (80) and https (443) variants are accepted.
- Help text on the flag explains the use case.

### US-4 — `--host 0.0.0.0` without trust-list is loud

**As Pat, when I run `attune ops --host 0.0.0.0` (binding to all interfaces) without an explicit `--trusted-host`, the startup output prints a yellow warning explaining the risk.**

Acceptance:
- Warning appears on stderr at startup, even with `--no-browser`.
- Warning text: "Binding to 0.0.0.0 without --trusted-host means any host header is treated as untrusted. Add --trusted-host <external-hostname> for each external hostname you intend to reach the dashboard at."
- The dashboard still starts (warning, not error).

### US-5 — Subscriber queue can't grow without bound

**As Pat, when a subscriber to `/runs/<id>/stream` is slow or disconnected without proper cleanup, the runner's broadcast queue does NOT grow indefinitely.**

Acceptance:
- The queue is bounded at `maxsize=1000` events.
- When the bound is hit, the existing `except QueueFull` block in `_broadcast` fires and the slow subscriber is dropped.
- A test exercises this: push 1000+ events to a non-consuming subscriber, assert it gets dropped.

### US-6 — Run-view route is observable

**As Pat, when I look at the `attune ops` server log, I can see which run_ids users tried to view that returned 404 or 400.**

Acceptance:
- `run_view_page` logs at INFO on 404 with `run_id` context.
- `run_view_page` logs at WARN on 400 (invalid run_id) with the offending input (sanitized).
- No PII in the log (no IP, no user identity — just run_id and what went wrong).

### US-7 — "Output survives refresh" has an integration test

**As a future maintainer, when I look at the test suite for the run-view feature, I can see a test that exercises the headline scenario end-to-end (start run, complete it, request /view URL, parse stream URL from HTML, attach, assert full output).**

Acceptance:
- Test exists at `tests/unit/ops/test_runner.py::test_run_view_replays_full_output_after_completion`.
- Test runs in CI on all platforms.
- Test fails if the replay mechanism breaks (regression guard).

---

## Contracts

### C-1 — Allowlist resolution

The Host allowlist is computed at `create_app()` time:

```python
def _compute_trusted_hosts(config: Config) -> set[str]:
    hosts: set[str] = set()
    # Always allow the bind address itself
    hosts.add(f"{config.host}:{config.port}")
    # Loopback aliases for convenience
    if config.host in ("127.0.0.1", "0.0.0.0", "localhost"):
        hosts.add(f"localhost:{config.port}")
        hosts.add(f"127.0.0.1:{config.port}")
    # User-specified additions
    for extra in config.trusted_hosts:
        hosts.add(extra)
        # If no port specified, allow both 80 and 443
        if ":" not in extra:
            hosts.add(f"{extra}:80")
            hosts.add(f"{extra}:443")
    return hosts
```

The middleware compares `request.headers.get("host")` (case-insensitive) against this set. Match → pass. No match → 400.

### C-2 — CLI flag shape

```
--trusted-host HOST       Repeatable. Hostname (optionally with :port) that
                          the dashboard accepts in the Host: header. Use this
                          when reaching the dashboard via a tunnel, reverse
                          proxy, or non-default hostname. Examples:
                            --trusted-host my-tunnel.example.com
                            --trusted-host my-tunnel.example.com:8443
```

`config.trusted_hosts: tuple[str, ...] = ()` field added to `Config` dataclass.

### C-3 — Queue maxsize

```python
# attune/ops/runner.py — line 90
queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=1000)
```

Single-line change. The existing `except QueueFull` block in `_broadcast` becomes live with no other code changes.

### C-4 — Run-view logging

```python
# In run_view_page:
logger.info("run_view: not found", extra={"run_id": run_id})
# (only on 404 path; 200 path stays silent to avoid noise)
```

Standard library `logging`, namespaced `attune.ops.routes.dashboard`. No structlog dependency added — ops already uses stdlib logging elsewhere.

### C-5 — Test name and location

`tests/unit/ops/test_runner.py::test_run_view_replays_full_output_after_completion`. Test must NOT use real subprocess if a portable alternative exists (use the existing `_echo_cmd` fixture).
