# Agent work handoff

## Goal

attune-ai works well with Claude Fable 5.1: every Fable 5.0 model
reference (`claude-fable-5`) that describes the *current* premium tier
points at `claude-fable-5-1`, and the code absorbs 5.1's breaking
changes (forced `tool_choice` is a 400; cache reads are $0.25/MTok).

## Acceptance criteria

- `attune.model_tiers._DEFAULTS["premium"] == "claude-fable-5-1"`, with
  `claude-fable-5` kept as a known override and priced by id.
- The curator (the one raw-SDK forced-`tool_choice` premium call) sends
  `tool_choice: auto` + `strict: true` for fable models; other pins keep
  the forced call.
- `AnthropicProvider.calculate_actual_cost` prices Fable 5.1 cache reads
  at $0.25/MTok; every other row keeps the 0.1x derivation.
- Projected docs (bulk skill + `.agents` mirror, help concept page,
  blog tier lines) name 5.1; CHANGELOG + spec decisions record it.
- Full test tree green except the model-tiers drift guard, which is red
  by design until attune-rag ships the mirrored defaults (see Risks).

## Scope and assumptions

- Branch/worktree: `claude/attune-ai-fable-5-1-64d292` at
  `.claude/worktrees/attune-ai-fable-5-1-64d292`
- Provider/session: Claude (lead), autonomous session 2026-09-03
- Assumptions: historical documents (weekly reports, COVERAGE_BUG_LOG,
  archived spec text, the dated blog cost post, CHANGELOG history) keep
  their `claude-fable-5` mentions — they describe the past. Pricing is
  unchanged ($10/$50), so no savings figures move.

## Current state

- Status: implemented and verified; PR open (see Next action).
- Changed files: `src/attune/model_tiers.py`, `llm/fable_call.py`,
  `llm/providers/anthropic.py`, `models/registry.py`,
  `models/telemetry/analytics.py`, `cost_tracker.py`,
  `authoring/spec_runner.py`, `workflows/config.py`,
  `routing/model_router.py`, `curator/core.py`, `curator/schema.py`;
  `plugin/skills/bulk/SKILL.md` (+ `.agents` mirror),
  `plugin/help/generated/{concepts/tier-routing,tasks/use-bulk,references/skill-bulk}.md`,
  `scripts/generate_concept_templates.py`, three `content/blog` guides,
  `CHANGELOG.md`, `docs/specs/fable-premium-tier/decisions.md`, tests.
- Decisions: recorded in `docs/specs/fable-premium-tier/decisions.md`
  (2026-09-03 entry) — array-form `fallbacks` kept, per-message effort /
  `clear_at` / `display: "updates"` not adopted.
- Risks or open questions:
  - `attune.model_tiers` is a byte-mirror of `attune_rag.model_tiers`;
    CI installs attune-rag from PyPI (1.1.0 = `claude-fable-5`). The
    drift guard stays red until attune-rag ships the mirror
    (`~/attune-rag` branch `feat/fable-5-1-premium-tier`).
  - attune-author carries its own mirror of the attune-rag contract
    with its own drift test — needs the same retarget when attune-rag
    ships (out of scope here).
  - `plugin/help/generated/tasks/use-bulk.md` and
    `references/skill-bulk.md` were hand-edited (their regeneration
    path spends API budget, which is capped at zero).

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| No live-code `claude-fable-5` default remains | `grep -rn 'claude-fable-5"' src/ plugin/skills scripts/` shows only the deliberate predecessor entries | pass |
| Targeted suites green | `pytest tests/unit/test_model_tiers.py tests/unit/models tests/unit/curator tests/unit/config ... tests/unit/gates` (4500 passed, 15 skipped) | pass |
| Drift guard compares constants to attune-rag | `pytest tests/unit/test_model_tiers_drift.py` against installed attune-rag 1.1.0 | fail (expected — predecessor default) |
| Drift guard green against the attune-rag branch | `PYTHONPATH=~/attune-rag/.claude/worktrees/fable-5-1/src pytest tests/unit/test_model_tiers_drift.py` | pass (5 passed) |
| Full tree | `pytest tests` (3 drift tests deselected) | pass (25268 passed, 258 skipped, 3 xfailed) |

## Next action

Ship attune-rag `feat/fable-5-1-premium-tier` (release ≥1.2.0 to PyPI),
then re-run this PR's CI so the drift lane goes green, then merge.
