# Decisions — Ops Dashboard Security Hardening

**Status:** complete (2026-05-12, pending Patrick's Phase 5 smoke)
**Owner:** Patrick
**Opened:** 2026-05-11
**Closed:** 2026-05-12 — implementation landed via v6.7.1 (#254, #256) + Phase 2.3 test added today
**Trigger:** Code-review report on PR #251 (2026-05-11) flagged the ops dashboard's command-execution endpoints as vulnerable to DNS-rebinding attacks. Verified real. Not introduced by #251 — pre-existing since the ops runner shipped.

---

## Problem

`attune ops` binds to `127.0.0.1:8766` by default. This protects against direct external network access — an attacker can't reach the dashboard from the internet. But it does NOT protect against **DNS-rebinding** attacks from any website the user visits in their browser:

1. User has `attune ops` running locally.
2. User visits `attacker.com` in another browser tab.
3. `attacker.com` resolves to attacker's IP, serves JavaScript.
4. JS waits, then `attacker.com` DNS-rebinds to `127.0.0.1`.
5. JS does `fetch("http://attacker.com:8766/workflows/release-prep/run", {method: "POST"})`.
6. Same-Origin Policy thinks this is still `attacker.com` → allows the request.
7. The TCP connection actually lands on `localhost:8766` because of the rebind.
8. The ops server checks the URL path (`/workflows/release-prep/run`) but **NOT the `Host:` header** (which is still `attacker.com`).
9. Workflow executes locally. `release-prep` publishes to PyPI. `simplify-code` writes to disk. Anything.

Verified by `grep -rn "Host\|TrustedHost\|allowed_host\|CORSMiddleware" src/attune/ops/` → zero matches. No defense exists today.

This is the dominant risk in the recent code-review report. The other findings (unbounded subscriber queue, missing logging, gap in "output survives refresh" test) are valid but lower-severity. This spec bundles them so a single hardening pass closes the cluster.

---

## Decision

**Add a `TrustedHost` middleware** that validates the `Host:` header against an allowlist before the request reaches any route handler. The allowlist is computed from `--host` / `--port` config so it's deterministic and matches the actual bind. DNS rebinding fails because the rebinder's `Host:` is `attacker.com`, not `localhost:8766`.

Also in scope (small, defensible additions in the same PR):
- **Bound the subscriber queue** at a sensible maxsize (e.g., 1000 events) so the `except QueueFull` block in `_broadcast` becomes live.
- **Add structured logging** to the new run-view route (`run_view_page`) so 404s and 400s show up in the server log with run_id context.
- **Add the "output survives refresh" integration test** — currently the replay mechanism is tested at the SSE-stream level but there's no end-to-end test for "request the /view URL after a run completes, confirm full output present."

Out of this spec's scope but worth naming:
- HTTPS / TLS — for a localhost dashboard, not warranted.
- Authentication tokens (Bearer / cookie / OAuth) — could be a follow-up if `--host 0.0.0.0` ever becomes common. Today's bind is loopback; the TrustedHost middleware closes the realistic threat.
- Per-workflow capability gating (e.g. "release-prep needs an extra confirmation") — interesting but separate UX question.

---

## Decisions made

| Question | Decision |
|----------|----------|
| Defense layer for DNS rebinding | **Host header allowlist middleware**. CORS isn't sufficient — CORS validates the `Origin` header which the browser sets, but the same-origin GET/POST baseline allows requests to fire even when CORS would refuse them at JS-callback time. Host validation rejects at request-time before the route runs. |
| Where the allowlist is computed | At `create_app()` time, from `config.host` + `config.port`. Default: `["localhost:<port>", "127.0.0.1:<port>"]`. CLI flag `--trusted-host` (repeatable) lets users widen for tunneled / proxied setups. |
| What happens on rejection | Return **400 Bad Request** with a short body. Not 403 (no auth involved). Not 421 Misdirected (the request landed at the right server, just lying about Host). Log the rejected Host header for diagnosis. |
| Queue maxsize value | **1000 events**. A reasonable run is ~1k–5k log lines; if a subscriber falls 1k events behind, dropping them is correct (the existing `except QueueFull` was the intended behavior — we just never bounded the queue to trigger it). |
| Should rejection be configurable to disable? | **No.** A flag like `--no-host-check` would be an attractive nuisance. If a user genuinely needs to reach the dashboard from a different hostname (Tailscale, Cloudflare Tunnel), they add it to `--trusted-host`. |
| Backward compatibility for the bind-host change | None needed. The bind defaults stay (`127.0.0.1:8765`). Existing users who run `attune ops` and `curl localhost:8765` keep working because `localhost:8765` is on the default allowlist. |

---

## Open questions

| Question | Lean | Notes |
|----------|------|-------|
| Should the dashboard refuse to start if `--host 0.0.0.0` is set without an explicit `--trusted-host`? | Yes — warning level. | `0.0.0.0` means "bind on all interfaces," so without an explicit allowlist the user gave the dashboard's command surface to their LAN. Warning + suggest `--trusted-host` keeps the door open but flags the risk. |
| Should there be a rate limit on `/workflows/<name>/run`? | Probably yes (low pri) | Even with Host check, a malicious local process could spam runs. Single-concurrent-run via `RunnerService` already partially handles this. Token-bucket on POST is a separate small task. |

---

## Out of scope

- **TLS / HTTPS** — localhost-only by default.
- **Auth tokens / OAuth** — requires a much larger UX story (cookie storage, signout, etc.).
- **CSRF tokens** — Host validation closes the same threat at lower cost.
- **Workflow capability levels** ("release-prep is dangerous; confirm twice") — UX call, separate spec if/when wanted.
- **Audit log of all runs** — partially covered by Tier 2's persistence (Phase 3); audit-specific telemetry is a follow-up.
- **Sandboxing the subprocess** (e.g., seccomp, container) — outside this spec.

---

## Resolution criteria

Spec closes when:

1. `TrustedHost` middleware is mounted in `create_app()` with default allowlist derived from `config.host` + `config.port`.
2. `--trusted-host` repeatable CLI flag exists and adds to the allowlist.
3. Subscriber queue has `maxsize=1000`; the `except QueueFull` block has at least one test asserting drop-on-overflow.
4. `run_view_page` route logs 404 / 400 at INFO with `run_id` context (no PII leak).
5. End-to-end test: start a run, complete it, GET `/runs/<id>/view`, parse the stream URL from the rendered HTML, connect, assert full log replays.
6. Manual DNS-rebinding repro fails (e.g., `curl -H "Host: evil.com:8766" http://localhost:8766/api/info` returns 400).
7. CI green on all 12 platform lanes.

---

## 2026-05-12 — Spec closed

All implementation work landed across three PRs during the May 11–12
window:

| PR | Title | What landed |
|----|-------|-------------|
| #254 | feat(ops): security hardening — DNS-rebinding fix + cluster | Middleware, Config field, CLI flag, startup warning, queue bound, dashboard logging, e2e test |
| #256 | release: v6.7.1 — DNS-rebinding fix for ops dashboard | Cut release; CHANGELOG entry satisfies Phase 6.4 |
| (today) | Phase 2.3 missing test added | `test_subscriber_queue_does_not_block_fast_subscribers` regression guard for queue isolation |

**Resolution criteria — all satisfied in code:**

1. ✅ `TrustedHostMiddleware` mounted in `create_app()` via
   `server.py:41 add_middleware(...)`.
2. ✅ `--trusted-host` repeatable CLI flag in
   `cli.py:58`; threaded through `build_config()`.
3. ✅ Queue bound: `runner.py:100 asyncio.Queue(maxsize=_SUBSCRIBER_QUEUE_MAXSIZE)`
   with two tests now covering both drop-on-overflow and fast-subscriber
   isolation.
4. ✅ `run_view_page` logs 404 at INFO (`dashboard.py:118`) and 400 at
   WARN (`dashboard.py:110`).
5. ✅ E2E test: `test_run_view_replays_full_output_after_completion`
   in `tests/unit/ops/test_runner.py:280`.
6. 🟡 Phase 5 smoke tests (Patrick's manual run, interactive).
7. ✅ CI green: all 12 platform lanes pass; 142 ops tests in
   `tests/unit/ops/`.

**Spec is closeable upon Patrick's Phase 5 smoke pass.** All
remaining work is the manual verification step (`curl` checks +
browser-load).

### What's left as a follow-up (not blocking)

Per the spec's own out-of-scope list — these were always deferred,
not regressions:

- HTTPS / TLS for the dashboard
- Auth tokens / OAuth
- Per-workflow capability gating
- Audit log of all runs
- Subprocess sandboxing

Open follow-up specs only when one becomes a real ask.
