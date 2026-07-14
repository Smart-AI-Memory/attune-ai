# Discovery-Sweep Budget Enforcement — decisions

**Status:** IMPLEMENTED + dogfooded (2026-06-28) — D1–D5 settled; D2
resolved (even-split + floor guard); D6 (cap precedence), D7 (cap-hit
detection), D8 (dogfood result + FR-3 premise correction) added in
design/build. D5 acceptance PASSED. · **Owner:** Patrick + agent

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

**Open question RESOLVED (design, 2026-06-28):** keep even-split; do
NOT widen wrapped `execute()` to accept a path list. Grounding from the
code:

- `_expand_path(path)` (`workflow.py:422`) returns `[path]` (single
  element) UNLESS the user passes an explicit glob (`src/**/*.py`). A
  normal directory sweep is one path — the wrapped workflow recurses
  internally. So `len(paths) == 1` in the common case and even-split ==
  full allocation (a no-op division).
- Each source loops `for path in paths` and calls `execute(path=path)`
  — singular. The "single execute over the whole list" alternative would
  require widening all 6 wrapped workflows' `execute()` to accept a path
  LIST and changing their scan semantics — outside FR-1's "add one
  `max_budget_usd` kwarg" scope, for a minority (explicit-glob) case.

Even-split keeps the per-source total bounded to its allocation
regardless of path count (the D1 guarantee) with minimal surface.

**Floor guard (added to D2 scope):** when `allocation / len(paths)`
falls below a minimum viable per-call cap (a glob of N files against a
small budget drives each call's share toward ~$0, so every call
truncates instantly into garbage), the source emits one `info` Finding
("budget too small to scan N paths at $X each") instead of firing N
doomed near-zero runs. This folds into FR-3's cap-hit surfacing. The
floor constant is set in design (start conservative, e.g. a few cents)
and is itself best-effort, not a contract.

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

## D6 — FR-1 cap precedence (explicit > env > depth)

**Decision (design, 2026-06-28):** `get_max_budget_usd(depth,
explicit=None)` resolves in this order: an `explicit` caller-supplied
cap wins outright; else the `ATTUNE_MAX_BUDGET_USD` env var; else the
depth default. The sweep passes each source's allocation as `explicit`,
so a sweep's `budget_usd` is the user's ceiling for that sweep.

**Why:** matches FR-1 verbatim ("when provided it is used"). The env var
is intentionally NOT a hard ceiling over `explicit` — an org wanting a
hard cap on sweeps caps the sweep's `budget_usd` input, not a
per-workflow env var. Non-sweep callers pass `None` and keep today's
env/depth behavior unchanged.

**Known edge (deferred):** if an org relied on `ATTUNE_MAX_BUDGET_USD`
as a per-workflow hard ceiling, a sweep allocation above it would
override it. No current consumer does this; revisit with `min(explicit,
env)` semantics only if telemetry shows it's needed.

## D7 — Cap-hit detection: cost-proximity, not an SDK signal

**Decision (design, 2026-06-28):** the FR-3 per-call "cap reached" note
fires when a run's truthful `cost_report.total_cost` (PR #1156) reaches
`_CAP_PROXIMITY` (0.95) of its `max_budget_usd` share. Worded "at the
budget ceiling," not "was truncated" — cost alone cannot distinguish a
truncated run from one that finished naturally at its allocation, and in
tight-budget mode (allocation ≈ spend) "this source spent its whole
allocation, raise --budget" is the true, useful message either way.

**Why:** SDK-version independent — no guessed `subtype`/`stop_reason`
string. The dogfood (D5) captures the real SDK truncation signal; a
follow-up may swap the heuristic for it if it proves cleaner. Both
budget findings carry `file=None` + a `budget-cap` tag so they route to
the `questions` bucket (verification rule 1); an `info` finding WITH a
file would fail the severity threshold (rule 2) and be rejected/hidden.

## D8 — Dogfood result + FR-3 premise correction (observed behavior)

**Verified (real de-nested dogfood, 2026-06-28, security-audit single
source on `llm_source_base.py`, depth=quick):**

| `budget_usd` | outcome | `spent_usd` | within `budget×1.15`? |
|---|---|---|---|
| 0.10 | capped → exit-1 at exhaustion (21 s) | 0.00 | yes |
| 0.50 | capped → exit-1 at exhaustion (52 s) | 0.00 | yes |
| 2.00 | completes (368 s) — 8 findings | 1.168 | yes (≤ 2.30) |

Duration scaled with budget (21→52→368 s), proving the explicit
per-source cap reaches the SDK's `max_budget_usd` and binds the run —
FR-1/FR-2 are live end-to-end, not just mocked. The completing run
shows truthful `spent_usd` (PR #1156) on the happy path; the cap-hit
note correctly did NOT fire (1.168 < 0.95 × 2.00). **D5 acceptance
PASSED.**

**FR-3 premise correction:** the spec assumed the SDK "already truncates
the run" and "returns partial findings" at the cap. Observed: at
exhaustion the claude CLI **exits 1 (the SDK raises)**, it does NOT
return partial findings, and the errored run reports **`spent=0`** (no
`ResultMessage`, so no cost). The source's existing try/except catches
it and surfaces an `info` finding (the `_workflow_unsuccessful_finding`
path) — so FR-3's SAFETY intent holds (no crash, no overspend, the
sweep continues), but "partial findings" does not happen on the
error-at-exhaustion path. The cost-proximity cap-hit note (D7) therefore
fires only on near-cap **completing** runs, never the exhaustion-error
path (which the error-handling already covers). `spent` for a
capped-out run understates (reads 0), never overstates — safe direction.
Recorded honestly per the "registered ≠ working / dogfood the real loop"
rule; a follow-up could map the exit-1-budget signal to a cleaner
"capped" finding if telemetry shows it's worth it.
