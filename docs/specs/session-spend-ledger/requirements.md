# Session Spend Ledger — Requirements

**Status:** active (2026-08-24) — implemented same-session; decisions
PROPOSED, awaiting chair ratification (see `decisions.md`)
**Origin:** 14.1.0-retro item 4 — chair: "I want it to be
ENFORCEABLE", explicitly not advisory.

---

## Problem

Billed launchers — the workflow probe runner
(`scripts/workflow_probe_runner.py`), roundtable lanes
(`src/attune/roundtable/`), and cross-model review runs
(`src/attune/roundtable/review.py`) — each cap a single run
(`ATTUNE_MAX_BUDGET_USD`), but nothing accumulates spend ACROSS
launchers within a session or refuses the next launch once a session
ceiling is reached. On this machine, CLI-spawned `claude` runs bill
the API key (org disabled subscription auth for the CLI), so a
runaway session burns real money against the standing $50 budget
(project memory `project_api_spend_budget`).

The existing spend-gate envelope
(`src/attune/gates/envelope.py` + `spend_gate.py`) gates the
`attune workflow run` CLI with confirm/block semantics, but the three
launchers above never pass through it, and its exhausted state
re-CONFIRMS interactively rather than hard-refusing.

## Requirements

- **R1 — cross-launcher accumulator.** One persisted per-session
  ledger that every billed launcher appends to: actual measured cost
  where available (probe runner reads `cost_report.total_cost`), a
  conservative flat estimate where the spend happens in an opaque
  subprocess (a `claude` seat invocation).
- **R2 — hard refusal.** Once cumulative session spend reaches the
  cap, the next billable launch RAISES
  (`SessionSpendCapError`) — not a warning, not a confirm prompt.
  The refusal message states spent/cap and the override.
- **R3 — no free first call.** A cap that is already `<= 0` (or a
  ledger already at cap) refuses the FIRST call — the known
  `__post_init__` budget-latch bug class must not recur. Enforced by
  a regression test.
- **R4 — only Anthropic-billed launches are gated.** `codex` and
  `agy` seats bill other providers; they are neither checked nor
  recorded. The budget being protected is the Anthropic $50.
- **R5 — enforcement at the shared seam.** Roundtable enforcement
  lives in `default_invoke_seat` (routine.py), which every lane —
  routine seats, synthesis, review, producing, countersign,
  gate-triage, skeptic — uses by default. Injected test invokers
  bypass it by design (they make no billable call).
- **R6 — explicit off switch, refuse-by-default posture.**
  `ATTUNE_SESSION_LEDGER=off` disables checking (recording
  continues). Setting the cap to `0` is NOT an off switch — it means
  "no budget" and refuses everything (contrast: the envelope's
  `cap<=0 == disabled` latch; divergence recorded in D4).
- **R7 — degrade toward enforcement, never past it.** A missing
  ledger file counts as $0 spent; corrupt lines are skipped (bounded
  undercount, work not blocked by a torn write); a malformed cap env
  falls back to the DEFAULT cap, never to "unlimited".

## Acceptance criteria

- A launcher call at cap raises/refuses — covered by unit tests for
  the ledger core, `default_invoke_seat`, `run_routine`,
  `run_review`, and the probe runner loop.
- Cap `<= 0` refuses the first call (R3 regression test).
- ≥85% coverage on changed code; keyless suite green.
