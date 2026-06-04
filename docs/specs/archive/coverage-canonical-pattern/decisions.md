# Per-decision log — Canonical Coverage Pattern

Append-only log. Pre-execution decisions and per-phase resolution as
commits land.

---

## Pre-execution context (2026-05-10)

This spec exists *because* PR #212's commit 2651ce75 attempted the
canonical pattern with only 2 of the 5 required pieces and made CI
worse than before. The spec encodes the lesson: subprocess coverage
under pytest-xdist requires `sitecustomize.py` (or equivalent) +
`COVERAGE_PROCESS_START` env var + `sigterm = true` flag, in addition
to `parallel = true` + `concurrency = [...]` that the failed attempt
had.

The revert of 2651ce75 (commit 2c59fc45 on the
`ci-add-pytest-timeout` branch) returns CI to its pre-canonical state
— known floor (1/12 jobs reliably green, others hit the runner-
shutdown infrastructure flake). That's the baseline this spec
improves on.

### Lesson worth preserving

The "first attempt at the right architecture failed → demote the
right architecture" reasoning that led to PR #212's mid-flight
mistake is a generally bad pattern. The right response when a
proactive option fails is to figure out *what's missing about the
attempt*, not to abandon the architecture. Most "this didn't work"
moments reveal incomplete setup, not wrong direction. (Saved as a
feedback memory: `feedback_rank_proactive_first.md`.)

---

## 2026-05-12 — Spec premise invalidated, paused

Pre-execution diagnosis of recent main-branch CI runs found the spec's
premise no longer matches reality:

- **Original premise**: CI fails with `[100%] PASSED → runner shutdown`
  pattern, caused by OOM during pytest-cov's IPC merge step.
- **Current reality**: Last four main runs (releases v6.7.1 incl. #256,
  #254, #253, #251) all fail Windows-only. Ubuntu and macOS pass.
  Windows runs complete the suite (`18036 passed, 268 skipped` in
  ~34 min) — no runner shutdown, no OOM at merge. Failures are:
  - 1 real assertion bug in
    `tests/unit/hooks/test_session_continuity_io.py` (encoding-related,
    fixed in this session).
  - 3 xdist worker crashes on Windows (`worker 'gw0/1/2' crashed`).
    Likely belong in `windows-memory-detection` or `windows-xdist-honor`
    specs.

Either PR #212 (despite its incomplete canonical-coverage attempt) or
some subsequent change resolved the original OOM/shutdown pattern.
Phase 3A (sitecustomize.py + concurrency flags) would not fix any of
the current failures.

**Action**: pause this spec. Do NOT execute Probe 0a (already implicitly
ran — `--cov-report=term-missing` is already absent from `tests.yml`)
or Probe 0b. Re-open only if the runner-shutdown pattern recurs.

**Status**: `paused` (not `complete` — original work was never done; not
`partial` — never attempted Phase 3A locally; not `closed` — premise
might recur and the design.md is still the right fix if it does).

---

(per-phase decisions appended as commits land)
