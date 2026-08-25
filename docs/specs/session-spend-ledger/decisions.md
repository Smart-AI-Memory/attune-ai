# Session Spend Ledger — Decisions

D1–D6 are **PROPOSED** (lead, 2026-08-24), implemented in the same PR
so the chair reads working code, not hypotheticals. Each is cheap to
re-rule; none is one-way. Counter-cases are stated per D11d
COUNTER-CASE.

**D7 is CONFIRMED** (chair, 2026-08-25) — it clarifies D5's scope
rather than ratifying it, so D5 itself stays PROPOSED.

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

- Known bound (D11 lane, 2026-08-24): check-and-launch is not atomic
  across processes, so N launchers racing the same headroom can
  overshoot the cap by at most the sum of their per-run
  `ATTUNE_MAX_BUDGET_USD` caps. Cross-process file locking was
  considered and declined for v1 (Windows-portable locking is its
  own project; the overshoot is bounded and the racers' entries all
  land, so the NEXT launch refuses). Revisit only on evidence of
  real concurrent-launcher overshoot.
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
  (distinct from 1 = a probe failed). A probe that CRASHES
  mid-workflow records the per-run budget cap, not $0 — its
  cost_report is lost with the exception, and the conservative
  bound is the most it could have billed (D11 lane, 2026-08-24).

---

## D7 — D5 sizes the estimate, not what counts as spend (CONFIRMED 2026-08-25)

Raised while fixing #2311. The `claude` seat was recorded absent at
three consecutive release-audit sittings; root cause was an expired
OAuth session, reproduced live (exit 1, stdout `Failed to authenticate:
OAuth session expired and could not be refreshed`). Each of those runs
had recorded the flat `$0.25` seat estimate — roughly `$0.75` of spend
against the cap for calls that never reached a provider.

`tests/unit/roundtable/test_routine_session_ledger.py::
test_failed_but_spawned_seat_still_records` asserted in its docstring
that "a timeout **or auth failure** may still have billed — overcount,
never undercount (D5)". That reading would keep charging for calls that
provably consumed nothing.

**RULING (chair, 2026-08-25): D5 does not say that.** Its scope is the
MAGNITUDE of the estimate recorded for a call that did, or may have,
consumed tokens. It is silent on a call that never reached the
provider, and such a call is not spend. Verified across all three
surfaces stating D5 — the first reading of this question cited only
one, which was not enough to support the claim:

| Surface | Text | Covers a never-authenticated call? |
|---|---|---|
| [decisions.md D5](#d5--seat-spend-is-a-flat-conservative-estimate-proposed) | flat estimate "deliberately above the typical single-reply `claude -p` cost, so the ledger overcounts rather than undercounts" | no — magnitude only |
| `src/attune/gates/session_ledger.py` `seat_estimate_usd` | "Flat conservative estimate for one **billed** `claude` seat call" | no — presupposes the call billed |
| `scripts/workflow_probe_runner.py` (crashed-probe path) | "A probe that crashed mid-workflow **may have billed** … record the per-run budget cap as the conservative bound" | no — conditions on "may have billed" |

The probe-runner surface is the closest analogue in the tree and draws
the same line: the conservative bound applies BECAUSE the call may have
billed.

Consequences, shipped in #2312:

- `attune.roundtable.routine.unbilled_failure(exit_code, output)`
  excludes only provably-free failures — binary-not-found (127) and a
  deliberately tight set of never-authenticated output signatures.
- Ambiguous failures (timeouts, mid-stream crashes) still record, so
  the conservative default is unchanged everywhere else.
- The test's docstring is narrowed in place, with the reason recorded
  next to it.

**Counter-case (D11d COUNTER-CASE).** The exclusion matches on output
text, so a call that billed and *then* emitted a matching auth message
would be undercounted. Judged unreachable for a single short
`claude -p` invocation, since authentication precedes the request — but
a signature list that grows carelessly could make it reachable, which
is why the list is kept tight and its rationale is stated at the
constant. If seat estimates ever drift from `usage.jsonl` actuals, this
exclusion is the first thing to re-measure.

D5 itself remains PROPOSED; this clarifies its scope, and does not
ratify it.

---

## D11 lane record (2026-08-24, codex, pre-chair)

Thread `review-claude-great-galileo-bb76a2-…`; 14 sent / 0 omitted;
5 findings. Accepted and fixed in-branch: non-finite cap bypass
(high→ `get_cap_usd` rejects NaN/inf), unreadable-ledger fail-open
(high → `check` refuses on an existing-but-unreadable ledger),
crashed-probe $0 record (high → records the budget cap).
Documented, not mechanized: check-and-launch race (bounded — see
D3's known-bound note) and the append-failure residual (R7).
Rejected with reason: the upfront routine check "violates R4 for
codex/agy-only routines" — every routine convenes the full
`SEAT_RECIPES` roster, which includes a claude seat, so no such
routine exists; the seam check remains the governing enforcement
if one ever does. Full row: `docs/specs/cross-review/receipts.md`.
