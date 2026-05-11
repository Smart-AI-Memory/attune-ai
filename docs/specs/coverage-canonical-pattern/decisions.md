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

(per-phase decisions appended as commits land)
