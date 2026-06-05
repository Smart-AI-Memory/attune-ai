# Design: Collaboration Gates

> Technical design for the spend gate (v1, CLI surface) and the
> shared estimate-and-gate core that later surfaces reuse.
> Companion to [`requirements.md`](requirements.md) and
> [`decisions.md`](decisions.md).

**Status:** approved (2026-06-05) — see [`decisions.md`](decisions.md)
**Last updated:** 2026-06-05

---

## Overview

The spend gate is a **budget envelope** enforced at the moment
attune is about to make its first billable workflow call of a
session. It reuses existing machinery wherever possible:

- **Injection point:** `cmd_workflow_run` in
  `src/attune/cli_commands/workflow_commands.py` — between
  `get_workflow(name)` (line ~101) and `run_workflow_with_exit_code(...)`
  (line ~149). The gate runs after the workflow is resolved and
  input validated, before any paid call.
- **Meter detection:** `AuthStrategy` / `AuthMode` /
  `SubscriptionTier` in `src/attune/models/auth_strategy.py`.
- **Cap primitive:** `get_max_budget_usd(depth)` +
  `ATTUNE_MAX_BUDGET_USD` (0 = off) in
  `src/attune/workflows/agent_sdk_adapter.py`; the envelope is
  modeled on the `Budget` dataclass
  (`src/attune/ops/session_summarizer.py:120`) and its
  `cap_usd <= 0` latch.
- **State persistence:** a TTL'd JSON file under `~/.attune/`,
  mirroring the `~/.attune/session_stash` pattern
  (`src/attune/memory/file_stash.py:88`).

The gate is a **guardrail** (per decisions.md D5) — it can only
*block or confirm*, never silently spend.

---

## Architecture: shared core + thin surfaces

Per open-question 5 (decisions.md D9): the gate logic lives in a
**shared core module**, callable by all three future surfaces.
v1 wires only the CLI; the dashboard and MCP layers reuse the
same core in later phases.

```text
src/attune/gates/                  # new package
├── __init__.py
├── spend_gate.py                  # core: estimate + gate decision
├── envelope.py                    # persisted session envelope state
└── meter.py                       # subscription-vs-API meter resolution
```

Core entry point (signature illustrative, finalized in code):

```python
def evaluate_spend_gate(
    workflow_name: str,
    depth: str,
    *,
    now: float | None = None,        # injectable clock for tests
) -> GateDecision:
    """Pure-ish decision: read the persisted envelope + the
    active meter, return whether this run needs a confirm,
    proceeds silently, or is blocked (non-interactive)."""
```

`GateDecision` carries: `action` (`proceed` | `confirm` |
`block`), the estimate, the meter framing string, the current
envelope state, and a reason. The **surface** (CLI) owns the
*presentation and the confirm I/O*; the core owns the *logic*.
This keeps the core testable without a TTY and lets the
dashboard render a modal / the MCP layer bubble the confirm
through the agent later.

---

## Resolving the five open questions

### Q1 — What is a "session" for the CLI? (the load-bearing one)

Each `attune workflow run` is a fresh process, so the envelope
must persist on disk. **Decision (D6): a TTL'd state file whose
window aligns with Anthropic's rolling usage window.**

- State lives at `~/.attune/spend_gate/envelope.json`.
- Shape: `{ window_start, ttl_seconds, authorized, cap_usd,
  spent_usd, meter }`.
- The "session" is the **TTL window**. Default `ttl_seconds`
  aligns to Anthropic's rolling usage window (5h) so the gate's
  notion of "this session" matches the meter it gates against —
  a subscription user's headroom resets on the same clock.
- On each run: load the file; if `now - window_start >
  ttl_seconds`, the window expired → reset (re-gate). Else the
  envelope is live → apply R3/R4.

Rejected alternatives:

- **Bind to `CLAUDE_CODE_SESSION_ID`.** Only present when the
  CLI runs *inside* Claude Code; bare-terminal runs have no such
  id. Too fragile as the primary key. (May be used as a
  secondary scope later.)
- **Pure in-memory (no persistence).** Would re-gate every
  single `attune workflow run` — defeats R3 entirely.
- **Per-calendar-day budget.** Simpler, but misaligned with
  Anthropic's rolling window, so the gate and the meter would
  disagree about when headroom resets.

### Q2 — Estimate source of truth

**Decision (D7): the estimate is the workflow's budget *band*,
not a precise figure.** Pre-call, the exact cost is unknowable.
The honest estimate is derived from:

- `get_max_budget_usd(depth)` — the per-workflow cap, as the
  upper band.
- `AuthStrategy.estimate_cost(module_lines, mode)` /
  `estimate_tokens` — a lower/expected band when a target size
  is known.

Presented as a band ("≈ up to $X for this run") with the cap as
the ceiling, never a false-precision single number. The
estimate's accuracy band is documented in the confirm text.

### Q3 — Subscription-meter framing

**Decision (D8): the meter module resolves the active mode and
frames accordingly.**

- `meter.resolve()` reads `AuthStrategy` (tier +
  `get_recommended_mode`) → `AuthMode`.
- **API mode** → dollar framing: "≈ up to $X; counts against
  your Anthropic API spend."
- **Subscription mode** → headroom framing: "uses your
  subscription quota (no per-call charge); counts against your
  Anthropic usage window." No dollar figure, no misleading $0
  (R5).
- The envelope's `cap_usd` is meaningful only in API mode; in
  subscription mode the envelope tracks *run count / window*
  rather than dollars (the field name in the persisted state is
  generalized accordingly).

### Q4 — Fail-safe policy for non-interactive (R7)

**Decision (D10): block-by-default, with explicit env
pre-authorization.**

- Interactive (TTY) + first paid call → `confirm`.
- Non-interactive (no TTY) + first paid call + no pre-auth →
  `block`, with a clear message naming the env override.
- Pre-auth via `ATTUNE_SPEND_GATE_AUTHORIZED=1` (or a set
  budget) → `proceed` within the envelope. Lets CI / the ops
  daemon opt in explicitly.
- The existing per-workflow `ATTUNE_MAX_BUDGET_USD` cap still
  bounds any proceeding run, so pre-auth is bounded, not blank.

Rationale: "fail-safe" for *spend* means never spend silently.
A non-interactive context can't confirm, so the safe default is
to refuse the first paid call until explicitly authorized —
mirroring the discipline ("the first paid call gets an explicit
go"), translated to a machine context as an explicit env grant.

### Q5 — Where the gate logic lives

**Decision (D9): the shared `attune.gates` core** (above). CLI
v1 calls `evaluate_spend_gate(...)` and owns the confirm I/O.
Rejected: CLI-local v1 code refactored later — would duplicate
the estimate/meter logic when the dashboard surface lands and
risk drift between surfaces.

---

## Data flow (CLI, v1)

```text
attune workflow run <name>
  → cmd_workflow_run resolves workflow + input  (free)
  → evaluate_spend_gate(name, depth)
       ├─ load ~/.attune/spend_gate/envelope.json
       ├─ window expired or absent?  → action=confirm/block
       ├─ authorized & within envelope?  → action=proceed
       └─ would breach envelope?  → action=confirm (breach)
  → CLI renders decision:
       ├─ proceed → run_workflow_with_exit_code(...)
       ├─ confirm → prompt; on yes, persist authorized envelope,
       │             then run; on no, exit cleanly (no charge)
       └─ block   → print env-override hint, exit cleanly
  → after a paid run, record actual cost to the envelope (R4)
```

Off switch (R6): `ATTUNE_MAX_BUDGET_USD=0` (existing) **or** a
dedicated `ATTUNE_SPEND_GATE=off` short-circuits
`evaluate_spend_gate` to `proceed` — heuristic-free, consistent
with the `Budget` `cap<=0` latch semantics.

Free/local never gates (R8): the gate only runs for workflows
that make billable calls. `--no-llm` runs, local/Ollama paths,
and non-workflow commands never reach `evaluate_spend_gate`.

---

## Testing strategy

- **Core unit tests** (no TTY): `evaluate_spend_gate` returns
  `confirm` on a fresh window, `proceed` within an authorized
  envelope, `confirm` on breach, `block` non-interactive without
  pre-auth, `proceed` with pre-auth. Inject `now` for window
  expiry (per the edge-of-bucket timing lesson — pin the clock,
  don't use real time).
- **Meter tests:** API mode → dollar framing; subscription mode
  → headroom framing, never $0 (R5). Both auth modes mocked.
- **Persistence tests:** envelope round-trips through the TTL'd
  file; expired window resets; corrupt file fails safe.
- **Off-switch + free/local tests** (R6, R8).
- **Regression guard:** assert that with the gate on and no
  authorized envelope, the code path to the first billable call
  is unreachable without a `confirm` — locks the core invariant.
- **Dogfood:** a real `attune workflow run <paid-workflow>`
  shows the confirm, proceeds on yes, and a second run in the
  window proceeds silently (acceptance criteria, not only unit
  tests — per the "registered ≠ working" lesson).

Cross-platform: pin the clock for all TTL tests; use `tmp_path`
for the envelope file (never a literal `~`/`/tmp` path — per the
Windows path lessons).

---

## What v1 does NOT build

- Dashboard confirm modal (later phase).
- Workflow/MCP-layer gating for agent-invoked runs (later
  phase; needs the confirm to bubble through the agent).
- Referent gate enforcement (later phase; R9–R10).
- Any change to Anthropic's own account-level usage limits.
