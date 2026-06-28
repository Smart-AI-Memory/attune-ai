# Discovery-Sweep Budget Enforcement — decisions

**Status:** approved (2026-06-28) — D1/D3/D4/D5 settled; D2 per-path
division left open to the design phase · **Owner:** Patrick + agent

## D1 — Enforcement mechanism: per-source hard cap

**Decision (Patrick, 2026-06-28):** plumb each source's existing
proportional allocation down into the wrapped workflow's
`max_budget_usd`, so each sub-workflow self-limits via the SDK's own
USD cap. Keep the `asyncio.gather` concurrent fan-out.

**Why:** the allocation logic (`_allocate_budget`) and the per-call USD
cap primitive (`get_max_budget_usd` → SDK `max_budget_usd`) BOTH already
exist; this connects two wires rather than building a new system. It
preserves concurrency and bounds the worst case to `sum(allocations) ==
budget_usd` (modulo D3). No single source can run away.

**Rejected alternatives:**

- **Cooperative cancellation** (run concurrently, cancel remaining /
  in-flight sources once a running total crosses `budget_usd`). A hard
  global ceiling, but cancellation mid-LLM-call is racy and in-flight
  sources overshoot before observing the signal — more surface, weaker
  guarantee than it appears. Deferred to a possible later spec.
- **Sequential spend-gating** (one source at a time, check running total
  before each). Simplest hard global cap but serializes the fan-out —
  unacceptable wall-clock regression (a 6-min concurrent sweep becomes
  the sum of all sources). Rejected.
- **Hybrid (per-source cap + global gate).** Best enforcement, most
  surface. The per-source cap (this spec) already bounds the worst case;
  add the global gate only if telemetry shows it's needed.

## D2 — Per-path budget division within a source

**Decision:** a source divides its allocation **evenly across its
`paths`** and passes `allocation / len(paths)` as `max_budget_usd` to
each `execute()` call. When `paths` is empty the source emits its
existing "no files matched" finding and spends nothing.

**Why:** even division is the simplest defensible policy and keeps the
source-level total at its allocation. Weighting by per-path size/LOC is
a refinement deferred until telemetry justifies it (most sweeps target a
single path or a small dir, where even-split == whole allocation).

**Open question (for review):** several sources today iterate
`for path in paths` and call `execute()` once per path. Confirm whether
a single `execute()` over the whole `paths` list is preferable (one
capped run vs N capped runs). If a source can accept a path LIST, one
run with the full allocation is simpler and avoids division entirely —
revisit per source in design.

## D3 — Overshoot tolerance

**Decision:** the cap is best-effort at the SDK boundary — a run can
exceed `max_budget_usd` by up to the cost of the final in-flight turn
before truncation. Acceptance asserts `spent_usd ≤ budget_usd * 1.15`
(15% headroom) for a real sweep; tighten once observed overshoot is
measured.

**Why:** the SDK truncates between turns, not mid-token, so a small
deterministic overshoot is unavoidable without hard cancellation (D1
rejected). 15% is a starting guard, not a contract — the design phase
sets the real number from a measured dogfood.

## D4 — Dependency on cost-tracking fix (#1156)

**Decision:** this spec lands AFTER PR #1156 (real `spent_usd`).
Enforcement is untestable and unobservable while the footer reports
`$0.00` — the cost fix is the prerequisite that makes "did we stay under
budget?" a real, measurable question.

## D5 — Verification discipline

**Decision:** the acceptance dogfood runs the REAL sweep (de-nested per
[[project_sdk_workflows_blocked_nested]]) with a low `budget_usd` and
asserts the truthful `spent_usd` stays within D3 tolerance. Mocked unit
tests (fake workflow capturing the `max_budget_usd` kwarg) are
necessary-not-sufficient — the "registered ≠ working / dogfood the real
loop" rule applies, the same way it surfaced the original $0.00 bug.
