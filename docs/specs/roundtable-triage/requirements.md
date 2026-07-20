# Roundtable Triage — Requirements

**Status:** approved (2026-07-20) — codifies the chair-ruled contract
(charter + T3/T4, q-briefing-triage-001; n=2 validation + "T4 y"
arming, q-briefing-triage-002). New scope beyond those rulings needs
new approval. Implementation: `attune.roundtable.triage_appendix`
(landed with this document).

## Purpose

Turn the live ops briefing into a weekly, bounded, chair-ruled triage
digest — attached to the existing clean-run routine, never a second
ruling sitting. Born from the live demo promoted as
q-briefing-triage-001; validated manually at n=1 (2026-07-19) and
n=2 (2026-07-20) before headless arming (T4).

## Requirements

**TA-1 — Appendix, not a routine.** The triage digest runs as an
appendix to the weekly clean-run, posting to the SAME board thread
(one weekly ruling sitting). It never registers as an independent
scheduled routine. (T4)

**TA-2 — Item cap, no silent drops.** At most 5 decidable items per
digest. Anything the cap drops is named in the brief ("N further
candidate items dropped"), never silently truncated. (T4; the
no-silent-caps discipline)

**TA-3 — Deterministic distillation, read-only pull.** The briefing
pull is read-only and free: curator source readers, the gate verdict
ledger, usage.jsonl freshness. NO LLM curation pass. Distillation
into items is deterministic code — seat deliberation is where model
judgment enters. (charter; T3)

**TA-4 — Honest darkness over refresh spend.** An empty source
renders "dark" in the brief. The appendix never schedules or
performs LLM sweeps to freshen a source; refresh happens only when
a chair-authorized run does it anyway. (T3)

**TA-5 — Gate-verdict input from CI at render time.** The durable
gate-verdict input is fetched from CI at digest render time
(timestamped unavailable/expired handling, no scheduled refresh).
SHIPPED 2026-07-20: implemented as a check-run-conclusions fetch on
main head (`gh api .../commits/main/check-runs`) — the CI-truth
surface that exists today; nothing in CI uploads a verdicts
artifact, so an artifact fetch would read a void (see decisions.md).
The local ledger is still read for producing-run receipts and its
darkness-by-construction (D7 CI-only test gates) rendered honestly.
(A4 ruling, 2026-07-20)

**TA-6 — Auto-demotion with a recorded-outcome ledger.** Each digest
records `{thread, at, items, rulings: null}` in the appendix state
file; the interactive ruling session records the chair's ruling
count via `record_rulings()`. After two consecutive digests with a
RECORDED ruling count of zero, the appendix demotes itself to
chair-invoked and says so. Unrecorded outcomes never demote. (T4)

**TA-7 — Carried table gates.** The appendix respects the shared R5
ceiling (its own sub-cap of 4 invocations keeps clean-run + appendix
≤ 8, under the ruled ceiling of 10), tolerates absent seats (R6),
and NEVER promotes its own thread (R8).

**TA-8 — Kill switch.** `ATTUNE_TRIAGE_APPENDIX=off` skips the
appendix with a printed notice — operational off-ramp without a
code change.

## Done-when

- A scheduled clean-run produces the appendix on the same thread
  with ≤5 evidence-bearing items, or an explicit 0-item /
  demoted / killed notice — receipts: the contract tests in
  `tests/unit/roundtable/test_triage_appendix.py` plus the first
  live scheduled run's thread.
- The demotion loop closes: digests recorded, rulings recordable,
  two recorded zero-ruling digests demote (test-receipted).
- TA-5's CI verdict fetch renders alongside the local-ledger read
  (SHIPPED — see decisions.md 2026-07-20 follow-on entry).
