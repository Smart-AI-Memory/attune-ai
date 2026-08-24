# Session Spend Ledger — Decisions

All decisions below are **PROPOSED** (lead, 2026-08-24), implemented
in the same PR so the chair reads working code, not hypotheticals.
Each is cheap to re-rule; none is one-way. Counter-cases are stated
per D11d COUNTER-CASE.

---

## D1 — "Session" = rolling 5-hour window (PROPOSED)

Spend counts toward the cap while its ledger entry is younger than
`WINDOW_SECONDS` (= the envelope's `DEFAULT_TTL_SECONDS`, 5 h).
No window-start state, no expiry bookkeeping — the sum over recent
entries IS the session, and it shares the spend-gate envelope's
clock rationale (aligned to Anthropic's rolling usage window).

- Alternatives: calendar day (resets at an arbitrary midnight,
  splits an evening session); explicit session id (needs every
  launcher to agree on id plumbing — ceremony v1 doesn't need).
- **Counter-case:** a rolling window means spend "drains back" —
  a session that burned the cap at 9 pm regains headroom at 2 am
  without anyone re-authorizing. If the chair wants a latched
  window that only a human reset clears, D1 flips to
  window-start + explicit reset; the jsonl format already carries
  timestamps, so the flip is contained in `spent_usd()`.

## D2 — Default cap $10, env-overridable (PROPOSED)

`ATTUNE_SESSION_SPEND_CAP_USD`, default **$10.00**. Derivation from
the standing $50 budget (`project_api_spend_budget`): one runaway
session is bounded to 20% of the whole budget, while the largest
known legitimate session (full probe set, ~$6–8) still fits in one
window without an override.

- **Counter-case:** $10 is 5× the probe runner's default per-run cap
  ($3) — the chair may prefer a tighter default (e.g. $5) and an
  explicit raise for probe-set days. Tightening is a one-constant
  change.

## D3 — Persistence: append-only jsonl under `~/.attune/telemetry/` (PROPOSED)

`~/.attune/telemetry/session_spend.jsonl` (override:
`ATTUNE_SESSION_LEDGER_PATH`), one `{ts, label, cost_usd}` line per
billed launch. Telemetry is the existing spend surface
(`usage.jsonl` lives there). Append-only is naturally safe under
concurrent launchers — no read-modify-write race can LOSE a spend
record the way a rewritten state file could, and undercounting is
the failure mode enforcement can least afford.

- Alternative: extend the spend-gate envelope
  (`~/.attune/spend_gate/envelope.json`). Rejected for v1: the
  envelope is a rewritten single-state file (last-writer-wins loses
  records under parallel lanes) and its semantics are
  confirm-on-exhausted, not hard-refuse; entangling the two would
  change `attune workflow run` behavior this retro item doesn't ask
  to change.

## D4 — `cap <= 0` REFUSES; the off switch is a separate env (PROPOSED)

`ATTUNE_SESSION_SPEND_CAP_USD=0` means "no budget → refuse every
billable launch", satisfying R3 (no free first call — the known
budget-latch bug class). Disabling is explicit and unambiguous:
`ATTUNE_SESSION_LEDGER=off`.

This deliberately DIVERGES from the envelope, where `cap_usd <= 0`
latches as *disabled* (its R6 off switch). Two surfaces, two
postures: the envelope is a consent gate (off = don't ask me), the
ledger is an enforcement cap (0 = spend nothing). Recording
continues even when checking is off, so the audit trail survives an
override.

## D5 — Seat spend is a flat conservative estimate (PROPOSED)

A `claude` seat subprocess reports no cost, so each invocation
records `ATTUNE_SEAT_SPEND_ESTIMATE_USD` (default **$0.25** —
deliberately above the typical single-reply `claude -p` cost, so the
ledger overcounts rather than undercounts). Probe-runner entries are
actual measured costs. `codex`/`agy` seats are not Anthropic spend
and are neither checked nor recorded (R4).

- **Counter-case:** switching the seat recipe to
  `--output-format json` would yield actual `total_cost_usd`, but
  changes the reply-parsing contract for every lane; not worth
  coupling to this item. Revisit if estimates drift far from
  `usage.jsonl` actuals.

## D6 — Refusal shape per launcher (PROPOSED)

- **Seam** (`default_invoke_seat`): raises `SessionSpendCapError`
  BEFORE spawning the subprocess. This is the enforcement point —
  every roundtable lane and review run inherits it.
- **`run_routine`**: checks upfront (before the board connect and
  the checks battery) and exits 3 with the refusal message — no
  partial thread is opened for a run that cannot afford its seats.
- **`run_review`**: the seam's raise propagates. The cross-review
  binding posture ("nothing here may gate a merge") is untouched —
  the refusal stops a NEW billable launch; it never scores or gates
  a finding.
- **Probe runner** (`_run_selected`): checks before each probe;
  on refusal, stops launching, keeps (and records to the registry)
  the probes that already ran, prints the refusal, exits 2
  (distinct from 1 = a probe failed).
