# Spec: CI gating-lane isolation

**Status:** superseded (2026-06-17) — by the ci-runner-hang root-cause fix (#930); Layer A shipped (#910) then was retired (#931, #932) once the hang was gone; Layers B/C never needed
**Opened:** 2026-06-15
**Layer:** attune-ai (CI / `.github/workflows/`)
**Owner:** Patrick + agent

---

## Problem

The merge gate and the slow/flaky lanes live in the **same** `Tests`
workflow, and the auto-merge trigger fires on `workflow_run` only when
the **whole** workflow completes. So when *any* lane in `Tests` hangs —
including a non-gating one — the merge is blocked even though every
gate that matters is green.

This is the recurring tax observed across QA #6 (2026-06-13 →
2026-06-14): the systemic runner-hang lets the suite run to ~99%
(tests passing) and then freezes at session finalize, leaving the
lane `in_progress` for 25–47 min until the job timeout cancels it.
(Corrected 2026-06-15 from an earlier "~1s after start" guess — the
first captured stack disproves it; see
[`ci-runner-hang/phase2-findings.md`](../ci-runner-hang/phase2-findings.md)
"Phase 3", run 27541609728.) Two distinct failure shapes both trace
to this topology:

1. **Non-gating lane hangs, blocks the merge trigger.** `clock-tz
   (Pacific/Kiritimati)`, the Windows lane, etc. hang; `coverage` is
   already green but `workflow_run` never fires because the run hasn't
   completed. Recovery today: `gh run cancel` to force completion so
   `workflow_run` fires and the merge job (which re-checks `coverage`
   independently) admin-merges. Manual, per-PR.

2. **The gating lane itself hangs.** `coverage` (required) freezes.
   This is *not* bypassable — coverage is the gate — and matrix
   right-sizing does not help because `coverage` is required, not
   advisory. Recovery today: `gh run rerun --failed`, wait for
   coverage to conclude, and if it re-hangs, either re-run again
   (fleet-wedge risk) or admin-merge on the reasoning that
   `test (ubuntu-latest, 3.12)` (same suite) is green and the diff
   can only raise coverage. Both are manual judgment calls.

Across this session the hang cost ~15–25 min per affected PR and
multiple cancel/re-run cycles on #901, #904, #892–#894. It is the
single largest source of merge friction and the reason the
auto-merge-safe class still needs babysitting.

## Verified context (grounded)

| Fact | Source |
|------|--------|
| Required checks = `CodeQL, code-quality, coverage, lint, platform-compat, pre-commit, test (ubuntu-latest, 3.12)` | `gh api .../branches/main/protection/required_status_checks` |
| Auto-merge fires on `workflow_run: ["Tests"] types:[completed]` and re-checks `coverage` independently | `.github/workflows/auto-merge-safe.yml` |
| `coverage` re-runs the FULL suite (so the ubuntu-3.12 lane is redundant with it) | `tests.yml` coverage job |
| The hang is environment/runner-side, not a test failure (tests pass to ~99% then the lane freezes and is timeout-cancelled) | coverage logs on #901/#904 (last test ~22:27, cancel ~22:47) |

## Relationship to existing CI specs (complementary, not duplicate)

- **`ci-runner-hang`** — attacks the *root cause* (why the runner
  freezes). This spec assumes the hang persists and makes the merge
  path *resilient to it*. If ci-runner-hang lands a real fix, this
  spec's value drops but its topology cleanup still stands.
- **`ci-matrix-right-sizing`** — *reduces lane count* on test/docs-only
  diffs (skips advisory lanes). It does **not** isolate the gate or
  help when a *required* lane (`coverage`) hangs. This spec is the
  structural complement: separate gate from non-gate.
- **`windows-xdist-flakes`** — a specific flaky-lane investigation;
  orthogonal.

---

## Goals

- A hung **non-gating** lane must NEVER block the merge trigger or the
  required-check set.
- A hung **gating** lane (`coverage`) must self-recover without manual
  `cancel`/`rerun` — bounded auto-retry, then fail loud (never silently
  block forever).
- No reduction in actual signal: every check that gates today still
  gates; the full matrix still runs (just not in the gating path).
- Minimal branch-protection churn; never leave a required check
  "missing" (the merge-blocking trap from ci-matrix-right-sizing D2).

## Non-goals

- Not fixing the runner-hang root cause (that's `ci-runner-hang`).
- Not changing *which* checks are required (policy stays; only their
  workflow *home* and *robustness* change).
- Not removing platform coverage — Windows/macOS lanes keep running.

---

## Proposed approach (to be refined in design.md)

Three independently-shippable layers, cheapest first:

### A. Per-job timeouts + auto-retry on the gating lanes (cheapest)

Add `timeout-minutes` to the gating jobs (esp. `coverage`) well below
the current implicit ceiling, and wrap the test step in a bounded
retry (e.g. `nick-fields/retry` or a shell re-invoke) so a single
frozen attempt is auto-killed and retried in-run instead of hanging
25 min and needing a human `rerun`. Converts the #1/#2 manual recovery
into automatic behavior. Smallest diff, highest immediate relief.

### B. Topology split — gate workflow vs matrix workflow

Move the 7 required checks (incl. `coverage`) into a lean `Gate`
workflow and the full OS×Python matrix + clock-tz into a separate
`Matrix` (advisory) workflow. Point the auto-merge `workflow_run`
trigger at `Gate` only. Then a hung Windows/clock-tz lane lives in
`Matrix` and cannot delay the merge trigger — failure shape #1
disappears structurally. Requires updating branch protection to the
same required names emitted by `Gate` (careful: name parity to avoid
"missing required check").

### C. Coverage sharding / fail-fast (optional, if B insufficient)

If `coverage` itself remains hang-prone, shard it (pytest-xdist groups
across N jobs) so one frozen shard is a small bounded loss and retried
independently, or run coverage with a strict step timeout that fails
fast into B's retry.

**Recommended sequence:** A first (immediate, low-risk, self-contained),
then B (the structural fix), then C only if measurements still show
coverage hangs after A+B.

---

## Done when

- A non-gating lane can hang and a tests/docs-only PR still
  auto-merges with no manual `cancel` (proven on a real PR).
- A coverage hang auto-retries within the run and concludes without a
  human `rerun` (proven, or documented as moved to layer C).
- Branch protection's required set is intact and emits with the new
  workflow topology (no "missing required check").
- `decisions.md` records the layering decisions and any
  branch-protection edits.

## Risks

- **Branch-protection name parity (high).** Splitting workflows renames
  the check *context*; if the required names don't match exactly, every
  PR blocks on a "missing" required check (ci-matrix-right-sizing D2,
  and the `required_check_app_ids` memory). Stage with a non-required
  dry run first.
- **Retry masking real failures (medium).** Auto-retry must
  distinguish a hang (no progress) from a deterministic failure; cap
  attempts and surface the retry in logs so a real failure isn't
  silently re-run green.
- **Two workflows double the matrix minutes (low).** Repo is public →
  free; acceptable. Mitigate by composing with ci-matrix-right-sizing
  (slim matrix on test/docs diffs).
