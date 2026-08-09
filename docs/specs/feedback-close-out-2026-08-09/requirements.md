# Feedback Close-Out 2026-08-09 — Requirements

**Status:** complete (2026-08-09, same-day) — R1/R2/R3 merged in
#2007; R4 resolved via its miss condition: chip PR #2001 landed
the retroactive [10.5.0] callout but not the 11.6.0-section one,
so the callout was direct-written per R4 in #2009 (merged; no
parallel CHANGELOG edit — the chip had already merged). Task-level
detail in tasks.md (flipped by #2011). Approved earlier same day:
chair selected all four
feedback items via the session form and assigned the lead to
order and manage them as a spec; receipt: the in-session
AskUserQuestion response "I think all of the items have positive
elements... step up as a lead programmer and order the feedback
items as part of a spec you will manage/optimize".
**Slug:** `feedback-close-out-2026-08-09`
**Owner:** lead (Claude), chair Patrick
**Provenance:** post-11.6.0-ship feedback review in the
2026-08-09 session; four items chair-selected from the lead's
self-critique.

## Problem

Four small debts surfaced by the session's feedback pass, each
cheap individually but repeatedly deferred or unratified:

- **F1** — the fable-premium-tier Task 9 price callout has now
  missed three releases (10.5.0-era through 11.6.0).
- **F2** — the memory-security-hardening R1-followup task-2
  "void" flip (#1997) was a lead interpretation of the D1
  narrowing, never explicitly chair-ratified.
- **F3** — usage-signals US-3's outreach round expired
  (~2026-08-03) without the mandated UNRESOLVED closure entry.
- **F4** — usage-signals US-4's 24-72h BEFORE-window is
  structurally unsatisfiable under same-day release decisions;
  the warning fires on every ship (11.5.0, 11.6.0).

## Requirements (lead-ordered; rationale in tasks.md)

- **R1 (from F2):** the task-2 void ruling is recorded as a
  decisions.md entry carrying the chair's form-selection receipt —
  ratified, not lead-assumed.
- **R2 (from F3):** US-3 closes with an explicit UNRESOLVED
  record per its own requirement text (responses and
  non-responses reported separately; no adoption inference).
- **R3 (from F4):** usage-signals gains a chair-reviewable
  cadence amendment: the BEFORE leg is satisfied by a scheduled
  (cron/launchd) snapshot rather than a per-planned-tag capture,
  so the receipt exists by construction. Ships as amendment text
  + a launchd template; machine install stays chair-gated (D6
  pattern).
- **R4 (from F1):** the 11.6.0 CHANGELOG carries the premium
  price callout. EXECUTION CONSTRAINT: chip session task_0630d99f
  is executing fable Task 9 concurrently — this spec VERIFIES
  that PR lands with the callout and only writes it directly if
  the chip stalls or misses the placement (no parallel CHANGELOG
  edits; the docs-outbox conflict class).

## Out of scope

- Running the reach snapshot itself (session-level task).
- Installing the launchd job (chair's machine, chair-gated).
- The rest of fable Task 9 (tier-docs regen) — owned by the chip.
