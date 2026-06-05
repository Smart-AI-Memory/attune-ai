# Tasks: Collaboration Gates

> Phase 1 implementation — the spend gate, CLI surface, budget
> envelope. Decomposed into independently-shippable units.
> Companion to [`requirements.md`](requirements.md),
> [`design.md`](design.md), [`decisions.md`](decisions.md).

**Status:** approved (2026-06-05)
**Last updated:** 2026-06-05

Ordering: T1 and T2 are leaf modules (shippable alone, no
user-facing change). T3 composes them. T4 takes the gate live
on the CLI. T5 hardens + documents. Each row ships as its own
PR unless two are trivially small.

---

## T1 — Envelope persistence module

**Status:** done (2026-06-05) — merged #637

**Objective.** Build `src/attune/gates/envelope.py`: a TTL'd,
on-disk session spend envelope modeled on the `Budget` dataclass
(`ops/session_summarizer.py:120`) and its `cap<=0` latch.

**Files to create.**

- `src/attune/gates/__init__.py`
- `src/attune/gates/envelope.py` — `Envelope` dataclass
  (`window_start`, `ttl_seconds`, `authorized`, `cap_usd`,
  `spent_usd`, `meter`), load/save to
  `~/.attune/spend_gate/envelope.json`, `is_expired(now)`,
  `record(cost)`, `would_breach(cost)`, reset-on-expiry.
- `tests/unit/gates/test_envelope.py`

**Decisions honored.** D6 (TTL window, default 5h aligned to
Anthropic's rolling window), D2 (envelope model).

**Validation.**

- Round-trips through the JSON file; `tmp_path`, never a literal
  `~`/`/tmp` (Windows path lessons).
- `is_expired` flips on an injected `now` past `window_start +
  ttl_seconds` (pin the clock — edge-of-bucket timing lesson).
- Corrupt/missing file → fresh envelope (fail safe).
- `cap_usd <= 0` latches `authorized=False`-equivalent off
  semantics (R6).

**Risks.** `low` — leaf module, no callers yet.

---

## T2 — Meter resolution module

**Status:** done (2026-06-05) — merged #638

**Objective.** Build `src/attune/gates/meter.py`: resolve the
active meter from `AuthStrategy`/`AuthMode` and produce the
framing string.

**Files to create.**

- `src/attune/gates/meter.py` — `resolve() -> Meter`
  (`mode`, `framing(estimate) -> str`).
- `tests/unit/gates/test_meter.py`

**Decisions honored.** D3, D8.

**Validation.**

- API mode → dollar framing ("≈ up to $X; counts against your
  Anthropic API spend").
- Subscription mode → usage-headroom framing, **never $0** (R5).
- Both auth modes mocked (don't read real auth state in tests).

**Risks.** `low`.

---

## T3 — Spend-gate core (compose envelope + meter)

**Status:** done (2026-06-05) — merged #638
**Depends on:** T1, T2

**Objective.** Build `src/attune/gates/spend_gate.py`:
`evaluate_spend_gate(workflow_name, depth, *, now=None) ->
GateDecision` returning `proceed` | `confirm` | `block` per the
design data-flow. Pure logic; no TTY, no I/O beyond the envelope
store.

**Files to create.**

- `src/attune/gates/spend_gate.py` — `GateDecision` +
  `evaluate_spend_gate`; the off-switch short-circuit
  (`ATTUNE_SPEND_GATE=off` / `ATTUNE_MAX_BUDGET_USD=0`);
  estimate band from `get_max_budget_usd(depth)` (D7).
- `tests/unit/gates/test_spend_gate.py`

**Decisions honored.** D7, D9, D10 (non-interactive →
`block` unless pre-authorized; the core returns `block`, the
surface enforces the TTY check by passing interactivity in).

**Validation.**

- Fresh/expired window → `confirm`.
- Authorized & within envelope → `proceed`.
- Would-breach → `confirm` (breach amount in the decision).
- Off switch → `proceed` (heuristic-free).
- Non-interactive without pre-auth → `block`; with
  `ATTUNE_SPEND_GATE_AUTHORIZED=1` → `proceed`.
- Inject `now` for all window logic.

**Risks.** `medium` — this is the invariant-bearing module; the
regression guard (T5) locks its core property.

---

## T4 — CLI wiring (gate goes live)

**Status:** done (2026-06-05) — wider file set per [decisions.md](decisions.md) D11
**Depends on:** T3

**Objective.** Wire `evaluate_spend_gate` into `cmd_workflow_run`
between `get_workflow()` and `run_workflow_with_exit_code()`;
render the decision; own the confirm I/O; persist the authorized
envelope on yes; record actual cost after a paid run.

**Files to modify.**

- `src/attune/cli_commands/workflow_commands.py` —
  call the core, branch on `GateDecision.action`, prompt on
  `confirm`, print env-override hint on `block`, exit cleanly on
  decline (no charge), persist on yes.
- `tests/unit/cli_commands/test_workflow_commands.py` (or a new
  `test_workflow_spend_gate.py`)

**Decisions honored.** D4 (CLI surface), D1.

**Validation.**

- `confirm` path: yes → runs + persists envelope; no → exits 0,
  no workflow run, no charge.
- `proceed` path within an authorized window: no prompt.
- `block` path (non-interactive): prints the env hint, exits
  cleanly, no run.
- Free/local (`--no-llm`) and non-billable workflows never reach
  the gate (R8).
- The post-run cost record updates the envelope (R4).

**Risks.** `medium` — touches the live workflow-run path;
must not change exit-code semantics for non-gated runs
(workflow-failure-exit-propagation contract).

---

## T5 — Regression guard, docs, dogfood

**Status:** todo
**Depends on:** T4

**Objective.** Lock the core invariant, document the gate, and
verify end-to-end against a real run.

**Files to create/modify.**

- `tests/unit/gates/test_spend_gate_regression.py` — assert that
  with the gate on and no authorized envelope, the first
  billable call is unreachable without a `confirm` (the locked
  invariant).
- Docs: the gate's env vars (`ATTUNE_SPEND_GATE`,
  `ATTUNE_SPEND_GATE_AUTHORIZED`), behavior, off switch — in the
  CLI reference + a `.help` entry if the help corpus covers
  workflow-run.
- CHANGELOG entry.

**Validation (dogfood — not only unit tests).**

- A real `attune workflow run <paid-workflow>` shows the confirm
  on the first call of a window, proceeds on yes; a second run
  in the window proceeds silently. (Spends real budget — gated
  by the spend gate itself; run only with an explicit go.)
- Subscription-mode run shows headroom framing, not $0.

**Risks.** `low` — hardening; the dogfood is the receipt
(§7 verification).

---

## Deferred to later phases (not Phase 1)

- **Dashboard runner** confirm modal (reuses the T3 core).
- **Workflow/MCP-layer** gating for agent-invoked runs (confirm
  bubbles through the agent).
- **Referent gate** (A) — guidance hardening + partial
  enforcement in attune's interactive surfaces (R9–R10).
