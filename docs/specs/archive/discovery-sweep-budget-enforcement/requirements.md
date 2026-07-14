# Discovery-Sweep Budget Enforcement — requirements

**Status:** complete (2026-06-28) — shipped in PR #1159 (per-source cap plumbed to SDK `max_budget_usd`; prerequisite cost fix #1156); D5 dogfood acceptance PASSED (decisions.md D8) · **Owner:** Patrick + agent

Make `discovery-sweep`'s `budget_usd` an actual spend cap. Today it is
decorative: the engine splits `budget_usd` across sources by
`budget_multiplier` and passes each source its share, but every LLM
source `discover()` does `del budget_usd` and calls
`workflow.execute(path, depth)` — so the share is ignored and a sweep
can spend without limit.

This is the v2 follow-up the source docstrings already promise: *"A
later PR can plumb the per-source share down once the wrapped workflows
accept an explicit per-call cap."* The chosen mechanism (D1) is a
**per-source hard cap** — each source's allocation becomes the wrapped
workflow's `max_budget_usd`, preserving the concurrent fan-out.

**Depends on** the cost-tracking fix (PR #1156): `spent_usd` must report
real per-source spend before enforcement is meaningful or testable.

## Grounding (verified against code, not docstrings)

- `DiscoverySweepWorkflow._allocate_budget` (`workflow.py:636`) already
  splits `budget_usd * (mult / total_mult)` per source and the engine
  passes it to `discover(paths, allocations[s.name])`
  (`workflow.py:573-585`). The allocation is correct; it is just dropped.
- Every LLM source's `discover()` opens with `del budget_usd`
  (e.g. `sources/security_audit.py:69`) and calls
  `workflow.execute(path=path, depth=self.depth)` — `budget_usd` never
  reaches `execute()`.
- The wrapped workflows ALREADY have a USD cap primitive:
  `get_max_budget_usd(depth)` (`agent_sdk_adapter.py:955`) returns a
  per-depth cap, and e.g. `security_audit.py:255` passes
  `max_budget_usd=get_max_budget_usd(depth)` into the SDK agent options.
  Today that cap is derived from `depth` only, NOT from the sweep
  allocation. Enforcement = let the sweep allocation OVERRIDE it.
- A source may call `execute()` **once per path** (the `for path in
  paths` loop), so the per-source allocation must be divided across the
  source's paths, not handed in full to each call (else N paths overshoot
  Nx).
- `PatternScanSource` is deterministic (`is_llm=False`,
  `budget_multiplier=0.0`) — it has no spend and is out of scope.

## Functional requirements

- **FR-1 (execute accepts an explicit cap).** Each SDK-native analysis
  workflow's `execute()` accepts an optional `max_budget_usd: float |
  None` kwarg. When provided it is used as the SDK `max_budget_usd`;
  when `None` it falls back to today's `get_max_budget_usd(depth)`. No
  behavior change for non-sweep callers (default `None`).

- **FR-2 (sources plumb their allocation down).** Each LLM source's
  `discover(paths, budget_usd)` stops discarding `budget_usd`: it
  divides the allocation across its `paths` and passes the per-call
  share to `execute(..., max_budget_usd=share)`. Division policy in D2.

- **FR-3 (cap is a true ceiling, not an estimate).** When a wrapped
  workflow reaches its `max_budget_usd`, it returns partial findings
  (the SDK already truncates the run); the source surfaces this as an
  `info`-severity Finding noting the cap was hit (per the existing
  `FindingSource` Protocol contract, `workflow.py:202-204`), rather than
  overspending or raising.

- **FR-4 (telemetry parity).** The board footer `$X / $Y spent` (now
  truthful after #1156) must show `X ≤ Y` for a well-behaved sweep. A
  best-effort overshoot tolerance is defined in D3; any overshoot beyond
  it is a test failure, not a silent pass.

## Non-functional requirements

- **NFR-1 (concurrency preserved).** The fan-out stays
  `asyncio.gather`-concurrent. No sequential serialization (rejected
  alternative, D1).
- **NFR-2 (no new MCP surface / kwargs to the tool).** The
  `discovery_sweep` MCP tool signature (`path`, `budget_usd`, `no_llm`)
  is unchanged; enforcement is internal.
- **NFR-3 (graceful degradation).** If the SDK/CLI does not honor
  `max_budget_usd` (older binary), the sweep still runs — enforcement
  degrades to today's behavior, logged once, never crashes.

## Out of scope

- **Global dynamic running-total cap / cancellation.** A hard global
  ceiling that cancels in-flight sources mid-call (D1 alternatives 2/4)
  is deferred — racy and higher surface. Per-source caps bound the worst
  case to `sum(allocations) == budget_usd` modulo the D3 tolerance.
- **Re-balancing unspent allocation** from cheap sources to expensive
  ones. Static proportional allocation stays; a later spec can add
  dynamic re-allocation if telemetry shows chronic under-spend.
- **PatternScanSource** (no spend).

## Acceptance criteria

- A sweep with a deliberately low `budget_usd` over a multi-finding
  target reports `spent_usd ≤ budget_usd * (1 + tolerance)` (D3), proven
  by a real (de-nested) dogfood — not only mocks.
- Unit tests: each source forwards a per-call `max_budget_usd` derived
  from its allocation (assert via a fake workflow capturing the kwarg);
  `execute(max_budget_usd=None)` reproduces today's depth-derived cap.
- No change to the MCP tool schema or the 47-tool count guard.
- `spent_usd` (from #1156) and the footer stay truthful.
