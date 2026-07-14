# Decisions — Opus 4.8 Platform Fit

**Status:** draft (2026-06-10) — matrix pre-committed with the design,
BEFORE any measurement run (the "pre-committed decision matrices
survive contact with data" discipline). Numbers below are the
contract; the run routes each axis strictly by them.

## D1 — Pre-committed Phase-0 decision matrix (2026-06-10)

Committed before `scripts/phase0/opus48_behavior.py` exists or runs.
Baseline = the Opus-4.6 leg of the same harness, same corpus.

| Axis | TUNE threshold | Knob if TUNE |
|---|---|---|
| Narration volume | mean inter-tool TextBlock run > 800 chars, OR end-of-task wrap-up > 2,500 chars, on ≥ 2 of 3 workflows | silence-default clause in subagent/orchestrator prompts (Phase 2) |
| Subagent under-use | 4.8 Task-spawn count < 70% of the 4.6 baseline on ≥ 2 of 3 workflows | explicit delegation-trigger guidance in workflow prompts (Phase 2) |
| Tool/memory under-use | 4.8 tool-call count < 60% of baseline, or zero file-memory use where 4.6 used it | "when to use tools/memory" guidance (Phase 2) |
| Ask-rate | ANY clarifying question in a headless SDK run (AskUserQuestion tool-use or interrogative terminal turn) | "decide, don't ask" clause in SDK system prompts (Phase 2) |
| Effort fit | `xhigh` token cost ≥ 1.3× `high` AND findings delta < 10% (count + severity-weighted) | premium depth map defaults to `high` in `agent_sdk_adapter` (Phase 1) |
| Cost | 4.8 $/run > 1.5× 4.6 at equal effort with findings delta < 10% | revisit premium depth→effort mapping (Phase 1) |

Verdict rule: an axis crosses → TUNE in `phase0-findings.md`; below →
LEAVE, no churn. All-LEAVE → retire the spec with the measurement
artifact (explicitly a valid outcome).

## D2 — Authoring/run decoupling (2026-06-10)

Design + matrix + harness + instrumentation are authored and merged
with zero API spend; the measurement run is gated on (a) the org
billing block clearing, (b) Patrick ratifying the budget (ceiling
$90, expected ~$50, $10/run hard cap).

## Open-question answers folded into design.md

- OQ-1 corpus: frozen in-tree snapshots under `scripts/phase0/corpus/`.
- OQ-2 baseline: one-off Opus-4.6 A/B leg, not telemetry.
- OQ-3 budget: $10/run cap, $90 matrix ceiling — pending ratification.
