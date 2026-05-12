# Tasks — Ops Dashboard Security Hardening

**Status:** complete (2026-05-12, pending Phase 5 smoke)

Single-phase implementation (small enough to ship in one PR) plus a verification phase. See `decisions.md`, `requirements.md`, `design.md` for context.

---

## Phase 1 — Host header middleware (primary fix)

Goal: DNS-rebinding attacks fail at the middleware layer.

- [x] **1.1** Add `trusted_hosts: tuple[str, ...] = ()` to `Config` dataclass. Add `trusted_hosts` param to `build_config()`.
- [x] **1.2** Add `--trusted-host` repeatable CLI flag to `cli.py`. Thread through to `build_config()`.
- [x] **1.3** Add startup warning for `--host 0.0.0.0` without `--trusted-host` (stderr, yellow if TTY).
- [x] **1.4** Create `src/attune/ops/middleware.py` with `TrustedHostMiddleware` and `compute_allowlist()`.
- [x] **1.5** Mount the middleware FIRST in `create_app()` (before any other middleware).
- [x] **1.6** Tests:
      - `test_middleware_allows_loopback` — `Host: localhost:<port>` passes
      - `test_middleware_allows_127_0_0_1` — `Host: 127.0.0.1:<port>` passes
      - `test_middleware_rejects_unknown_host` — `Host: evil.com:8766` returns 400 with the expected detail
      - `test_middleware_rejects_missing_host_header` — request without Host header → 400
      - `test_middleware_case_insensitive` — `Host: LOCALHOST:8765` passes
      - `test_middleware_logs_rejection` — caplog captures WARN with the host value
      - `test_trusted_host_flag_widens_allowlist` — `--trusted-host my.tunnel.example.com` lets `Host: my.tunnel.example.com:80` and `:443` through
      - `test_trusted_host_flag_with_port` — `--trusted-host example.com:8443` accepts that exact value
      - `test_compute_allowlist_loopback_aliases` — binding to `0.0.0.0` adds both `localhost:<port>` and `127.0.0.1:<port>` to the allowlist

## Phase 2 — Queue bound

- [x] **2.1** One-line change in `runner.py`: `asyncio.Queue(maxsize=1000)`.
- [x] **2.2** Test: `test_subscriber_queue_drops_slow_subscriber` — push 1001+ events to a non-consuming subscriber, assert it's removed from `self.subscribers` after the QueueFull path fires.
- [x] **2.3** Test: `test_subscriber_queue_does_not_block_fast_subscribers` — one slow subscriber doesn't slow down a fast one.

## Phase 3 — Run-view logging

- [x] **3.1** Add `logger = logging.getLogger(__name__)` to `dashboard.py` if not present.
- [x] **3.2** Log at INFO on 404 path of `run_view_page` with `run_id` context.
- [x] **3.3** Log at WARN on invalid-run_id path with the (truncated) offending input.
- [x] **3.4** Test: `test_run_view_logs_404` — caplog captures the INFO line with run_id.
- [x] **3.5** Test: `test_run_view_logs_invalid_input` — caplog captures the WARN line with the bad input.

## Phase 4 — End-to-end "output survives refresh" test

- [x] **4.1** Add `test_run_view_replays_full_output_after_completion` in `tests/unit/ops/test_runner.py`. Pattern:
      ```python
      # Start a run, wait for terminal, request /runs/<id>/view,
      # parse the stream_url out of the rendered HTML, attach to the
      # SSE stream, assert the replayed lines match the expected
      # output, and assert we get the terminal `done` event.
      ```
- [x] **4.2** Test must run async (the existing `_wait_terminal` helper expects it).
- [x] **4.3** Run the existing ops suite to confirm no regressions: `pytest tests/unit/ops/ --no-cov`.

## Phase 5 — Manual verification

- [ ] **5.1** Smoke: `curl -H "Host: evil.com:8766" http://localhost:8766/api/info` returns 400.
- [ ] **5.2** Smoke: `curl http://localhost:8766/api/info` returns the JSON.
- [ ] **5.3** Smoke: `curl http://127.0.0.1:8766/api/info` returns the JSON.
- [ ] **5.4** Smoke: `attune ops --host 0.0.0.0` prints the startup warning.
- [ ] **5.5** Smoke: `attune ops --trusted-host my.example.com` adds it to the allowlist (verify via curl with that Host).
- [ ] **5.6** Patrick reviews the implementation in a preview deploy + browser, confirms the dashboard still loads normally.

## Phase 6 — Close

- [ ] **6.1** All `requirements.md` acceptance criteria pass.
- [ ] **6.2** CI green on all 12 platform lanes.
- [ ] **6.3** Open follow-up specs for any out-of-scope items that surfaced (rate limit on `/workflows/<name>/run`, capability levels, etc.).
- [ ] **6.4** Add a brief mention in the next release changelog: "Hardened the ops dashboard against DNS-rebinding attacks."

---

## Out of scope (parking lot)

- HTTPS / TLS for the dashboard
- Auth tokens (Bearer / cookie / OAuth)
- CSRF tokens (Host validation closes the same threat)
- Per-workflow capability gating
- Audit log of all runs
- Subprocess sandboxing

---

## Rollback plan

Each phase is a single squash-merge commit. Rollback = `git revert <commit>`.

The highest-risk phase is **Phase 1** (middleware). If it inadvertently blocks legitimate access:
- Symptom: dashboard returns 400 for `localhost:8766` requests
- Cause: bug in `compute_allowlist` or middleware comparison
- Mitigation: `attune ops --trusted-host localhost:8766` adds an explicit override; revert PR if widespread

Phase 2 (queue bound): rollback restores unbounded queue (no change from today).
Phase 3 (logging): pure additive; rollback removes log lines.
Phase 4 (test): rollback removes the test only.
