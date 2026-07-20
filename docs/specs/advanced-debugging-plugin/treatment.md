# Advanced Debugging Plugin — One-Page Treatment

**Status:** treatment draft (2026-07-19) — pre-spec, for chair
reaction. Chair-ratified leans from the originating conversation
are marked ✓. Next artifact: `requirements.md` via `/spec`
interview.

## Vision

A self-healing application closes a five-stage loop. Attune has
quietly built four of the five stages; this plugin is the missing
middle.

| Stage | State | What exists |
|-------|-------|-------------|
| Sense | ✅ | Canonical run-record corpus (every path emits, with `trigger`/`project` provenance), typed `sdk_error_kind`, health checks, telemetry |
| **Diagnose** | ⬅ gap | `fix-test` is shallow; everything else stops at "it failed" |
| Propose | ✅ | Curator + next-workflow recs (attribution live), pipeline-learner miner behind RR-1's gate |
| Verify | ✅ | Receipts discipline, lifecycle gates, drift-guard tests |
| Learn | ✅ | Lessons corpus (727), Redis recall, decisions.md trail |

## First target (✓ chair-ruled): attune's own failed runs

Dogfood-first. The sensors, error taxonomy, and rec surface exist;
every diagnosis is verifiable against a codebase we control; the
corpus grows just by working.

## Core artifact: the DiagnosisRecord

A failed run record is picked up and produces a first-class,
minable record: symptom → evidence chain → root-cause hypothesis →
confidence → proposed fix → verification receipt. Verified
diagnoses graduate into lessons; the learn stage closes the
flywheel.

**The moat: lessons as diagnostic priors.** The diagnoser recalls
before it spelunks — 727 receipt-backed lessons are confirmed
root-cause episodes for THIS codebase (MAPPING trap, stash dance,
exit-139 class). Generic debuggers have no memory; attune's does.

## The LLM team (roundtable) as debugging staff

The multi-model round table (Claude, Antigravity, Codex —
moderator/board/chair machinery all shipped) takes three debugging
roles, reusing existing loops:

1. **Diagnosis panel** — for hard or ambiguous failures, seats
   hypothesize independently from the same evidence packet
   (R1 text-only), the moderator synthesizes, dissent is recorded.
   Judge-panel beats one-model-iterated exactly when the failure
   space is wide.
2. **Fix loop with cross-seat review** — the existing solutions
   loop (V2-P3): seats propose fixes as text, the moderator
   materializes in a scratch worktree, named checks produce
   exact-tail receipts, a DIFFERENT seat reviews the diff, the
   chair rules. Failures present failed-with-receipts, never
   laundered green (TAC-4).
3. **Automated error-check routines** — the `clean-run` routine
   precedent: a headless check battery (preflight + unit suite +
   failed-run triage) runs on cadence, seats deliberate the
   results, and a digest thread waits for the chair. R8 holds: a
   routine never promotes, never auto-fixes.

### Use cases, nearest first

- "Why did this fail?" button on a failed run view → diagnosis
  chip on the rec surface (on-demand, v1).
- Nightly failed-run triage digest: batch-diagnose the day's
  `success=False` records, cluster by root cause, one digest.
- Automated error-check sweep: run the keyless battery + targeted
  probes, deliberate anomalies before they become incidents.
- Test-failure debugging: `fix-test` deepened with evidence chains
  and lesson priors (v2).
- CI red-lane diagnosis from `gh` data (v2 — rich lesson priors).
- Runtime self-healing for arbitrary apps (horizon — the vision,
  not the plan).

## Ratified v1 constraints (✓)

- **Propose-only.** The chair rules on every fix (mirrors
  roundtable R4). Auto-apply is a later rung behind its own gate.
- **On-demand trigger.** Diagnosis is LLM spend; the button first,
  auto-diagnosis as an opt-in threshold later.
- **Self-records included but stamped.** Diagnostic runs carry a
  new trigger class (`attune-heal`), enter the corpus, and are
  excluded from mining — the diagnoser can diagnose itself without
  polluting the manual-evidence class.

## What v1 must build (the gap list)

- `diagnose` workflow + `DiagnosisRecord` schema (+ persistence
  beside the run corpus).
- Lessons-recall priors step (query `idx:attune_memory` with the
  error shape before evidence gathering).
- Run-view button + diagnosis chip surface.
- `attune-heal` trigger value threading (the RC-3 seam extends).
- Roundtable debugging brief template + evidence-packet builder.
- Failed-run triage routine registration (manual-first, then arm).

## Non-goals (v1)

Auto-apply of fixes; non-attune applications; always-on
auto-diagnosis; replacing `fix-test` (it deepens later, not now).
