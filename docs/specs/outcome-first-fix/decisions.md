# Outcome-First Fix — Decisions

## D1 — Canonical Fix scenario: hardened failing-test (RATIFIED)

**Chair, 2026-07-30.** The roundtable left the canonical
scenario as an open chair decision. Patrick leaned failing-test;
the lead rendered the counter-case unprompted (plain
failing-test lets the fix target and the verification probe
collapse into one artifact, leaving H2's goal/probe separation
unproven, and it exercises the path attune already serves best).
Three options were presented — hardened failing-test, plain
failing-test, seeded runtime bug with agent-authored regression
test. Chair picked **hardened failing-test**: the failing-test
scenario with plural, distinct done conditions (target test
passes + full fixture suite green + diff confined to source,
not tests). The seeded-runtime-bug option was declined because
an LLM-authored regression test adds nondeterminism to repeated
evaluation; determinism won.

## D2 — "XML task for the Fix proof slice" scoped to Phase 0 (PROPOSED)

**Lead, 2026-07-30.** The ruling says the spec's only executable
unit is a cold-handoff-capable XML task "for the Fix proof
slice." Read literally, the proof slice spans ruling Phases 0–2,
but one XML task covering inventory + contract design + live
execution is multi-session-sized and not cold-handoff-capable.
Interpretation adopted: Task 0 covers ruling Phase 0
(architecture and characterization proof) only; the Phase 1 and
Phase 2 tasks are authored after Phase 0's acceptance passes and
the chair gates each. Counter-reading (one task for the whole
slice) recorded and rejected for handoff size. Chair may
overrule.

## D3 — Initial metric subset of four (PROPOSED)

**Lead, 2026-07-30.** The ruling lists ten Phase 3 metrics.
Standing up measurement for all ten during the thin slice risks
building the parallel telemetry system the ruling itself
forbids. Proposal: measure evidence-valid receipt completeness,
verification-failure honesty, time-to-verified-outcome, and
compatibility regressions from Phase 2 onward; the
routing-behavior metrics (false-confident-route,
contract-edit, route-correction, abstention, abandonment)
activate at Phase 4 where their labeled corpus exists anyway.
The full list remains ratified; this only sequences it. Chair
may overrule. (Amended 2026-07-30: the codex D11 lane caught
false-confident-route rate sitting in the Phase 2 set while the
same decision deferred routing metrics to Phase 4 — it is a
routing metric and moved there.)

## D4 — Spec drafted directly from the roundtable synthesis (NAMED)

**Lead, 2026-07-30.** Per the decision routine, originating a
spec normally offers the `/spec` interview. Skipped here and
named out loud: the roundtable WAS the interview — the ruling
already contains the hypotheses, non-goals, gates, and
counter-case a Stage 1 interview would re-derive. The spec
transcribes the ruling; it does not re-litigate it.
