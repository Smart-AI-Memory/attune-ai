# Memory Feedback Signal — Decisions

**Status:** shipped (2026-07-19) — implemented same day (#1459);
receipts recorded below. Remaining thread is operational only:
read `wrong_rate` after weeks of Stop-hook accumulation.

## Thread mem-signal-001 — the first V2-P1 spec-authoring loop

Promoted from `attune:roundtable:thread:mem-signal-001` (chair:
Patrick, 2026-07-19). This spec IS the TAC-1 receipt for
`roundtable-producing-team` V2-P1: the round table's first
end-to-end authored spec.

**Subject selection (itself a receipt):** the chair's first pick
(workflow-failure-exit-propagation) was killed at S0 — the
grounding pack found the spec ARCHIVED and the exit contract
shipped (`_exit_codes.py`); the stale
`project_next_work_sequence` memory description was fixed on the
spot. The pack did its job before any member invocation was spent.
Second pick (chair): memory-insurance STEP 2 — the owed design
pass from `project_memory_as_insurance` /
`docs/specs/memory-recall-eval/decisions.md` (2026-07-14 entry).

**The loop (all three rounds used — earned, not padded):**

- **Round 1 — draft** (claude, fixed drafter role per the v2
  ruling; 44s): MI-1..MI-6 with testable acceptance criteria,
  non-goals, five open questions.
- **Round 2 — adversarial critique** (parallel): antigravity
  (10s, verdict ready-with-edits, 6 cited items — top: batched
  single Ollama pass + aggregate timeout); codex (93s, verdict
  needs-revision, 14 cited items — top: a bounded transcript tail
  cannot justify mandatory scored verdicts, insufficient evidence
  must map to `unscored`; unique catch: transcript text is
  untrusted prompt input → prompt-injection hardening).
- **Round 3 — revision** (claude): MI-1..MI-7 (MI-7 born from
  codex's injection catch), six tagged agreed, one 2-1, every
  critique item integrated, none rejected. Four of round 1's five
  open questions SETTLED by deliberation (batching, rotation
  snapshot, unscored emission, malformed-output mapping); one
  survived to the chair.

## Chair rulings (2026-07-19, batched form)

1. **All seven requirements APPROVED** as drafted (per-REQ gate;
   the drafted text already kept the sole disputed point
   reversible).
2. **OQ-1: `wrong_rate = wrong / (acted_on + wrong)` is the
   headline hard-noise metric.** `ignored` is NOT noise — an
   ignored surfacing on a quiet day is expected premium under the
   ratified insurance frame. `ignored_rate` co-reported; combined
   candidate-noise rate remains a reversible field. This resolves
   the MI-5 2-1: antigravity's formula becomes the headline, AND
   codex's reversibility requirement is preserved in the reader's
   shape — both critics' positions survive in the ruling.
3. **Destination: this new spec dir** (`memory-feedback-signal`).
   `memory-recall-eval` stays the benchmark spec that scoped
   STEP 2; this spec owns the build.

## Field notes for roundtable-producing-team (V2)

- The seat-reply cap (8000 chars, head-kept) truncated the
  round-3 REVISION mid-document — caps must be ROLE-AWARE: a
  position statement and a drafter's full document have different
  size envelopes. Worked around by raising the cap for the
  drafter call; V2-P2's typed round contracts should carry
  per-role output budgets.
- Round-2 critiques answered most of round-1's open questions —
  the "diff is the agenda" design intent showed up in practice:
  chair attention was spent on ONE genuinely-open question, not
  five.

## Implementation SHIPPED — receipts (2026-07-19, PR #1459)

Built same-day on the chair's "go build" (tier: structured
one-shot — MI-1..MI-7 proved tightly bounded, as predicted).
`plugin/hooks/_memory_verdicts.py` + `session_stash.py` wiring +
`ops/data.py` `read_memory_signal` / caption swap.

**MI-6 receipts, as specified:**

- **MI-6a (CI-mandatory, non-mocked):** real `log_memory_event`
  surfacing write → real scorer run with Ollama ABSENT (dead
  loopback port) → real reader aggregation — all `unscored`,
  rates `None` (never fabricated zeros), caption UNCHANGED
  (all-unscored must not flip it). In
  `tests/unit/hooks/test_memory_verdicts.py`.
- **MI-6b (hermetic, CI):** a real loopback fake-Ollama HTTP
  server (not a mocked client) exercises all three scored labels
  including the 2026-07-08 stale-`/recall` `wrong` case, the MI-7
  injection coercions (attacker-chosen labels and unknown items
  never survive), idempotent re-run, and the caption swap firing
  on scored verdicts (`wrong_rate` 0.5 rendered with the
  denominator note).
- **MI-6c (real-Ollama, recorded pre-release):** live
  `llama3.1:8b` run in an isolated `ATTUNE_HOME` (2026-07-19):
  a followed lesson scored `acted_on`, a stale finding scored
  `wrong` — real nondeterministic model output surviving the
  strict parse contract, exactly the false-positive class that
  motivated the feature.

Suite: 11 new tests; hooks + ops = 2191 passed. All pre-commit
hooks green.

**Operational caveat (recorded, not a blocker):** the 3s default
verdict timeout is the session-end latency budget; a COLD
`llama3.1:8b` needs longer (the MI-6c receipt used
`ATTUNE_MEMORY_VERDICT_TIMEOUT=60`). Warm-model sessions score
fine; cold-start sessions degrade to `unscored` — which is the
designed honest behavior, but expect early denominators to skew
`unscored` until usage keeps the model warm. Revisit the default
only with measured data.

## Next

The denominator now builds itself: every session's Stop hook
scores its own injections. After a few weeks of accumulation,
read `wrong_rate` via `attune.ops.data.read_memory_signal` and
let task-shape routing fall out of the measured noise (ratified
frame) — no earlier.
