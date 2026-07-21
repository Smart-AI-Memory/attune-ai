# Agent work handoff

## Goal

attune-author-consolidation T3 (D10): the generator/polish machinery
absorbed into `attune.authoring`, LLM calls repointed to
`attune.models.single_turn`, polish-master action wired into the
author-feature skill. Ships as a **held draft** under the 10.6.0 hold
(`hold-until-07-27`); merging it unblocks T4 (archive-without-yank,
D12). Serves the ratified north star (`project_evolution_north_star`
memory): one wheel, adapters as the growth surface.

## Acceptance criteria

- `git grep attune_author src/` clean except the T4-owned
  `ops/help_regen.py` CLI path and held-#1562-owned scripts/tests.
- Absorbed suites green serially (`tests/unit/authoring`,
  `tests/unit/models/test_single_turn_*`).
- `scripts/polish_master.py <slug>` reaches the credential boundary
  with everything upstream live (master parse, source extraction,
  RAG grounding) — verified without spend.
- Draft PR open with `hold-until-07-27`, CI green, `Closes #1567`.

## Scope and assumptions

- Branch/worktree: `claude/session-f4b4f3` at
  `.claude/worktrees/session-f4b4f3`
- Provider/session: Claude Code (Fable 5), 2026-07-21
- Assumptions: scripts/aggregator-test repoints belong to held PR
  #1562 (do NOT touch here); T4 execution is a separate later PR.

## Current state

- Status: built and verified; PR being opened (see Next action).
- Changed files: `src/attune/models/single_turn.py` (new),
  `src/attune/authoring/{generator,polish,polish_prompts,
  maintenance_contract,rag_hook}.py` + `faithfulness/` +
  `ground_truth/` + `meta_templates/` (new), `manifest.py`/
  `staleness.py` (status/manual ports), `__init__.py` exports,
  `scripts/polish_master.py` (new),
  `plugin/skills/author-feature/SKILL.md` (+ `.agents` mirror),
  `src/attune/memory/personal.py`,
  `tests/unit/authoring/**` (absorbed suites + conftest),
  `tests/unit/models/test_single_turn_{routing,retry}.py`,
  `tests/unit/memory/test_personal_internals.py`,
  `tests/unit/test_website_version_accuracy.py`, `pyproject.toml`
  (package-data `*.j2`), `CHANGELOG.md`, spec decisions.md.
- Decisions: recorded in
  `docs/specs/attune-author-consolidation/decisions.md`
  ("T3 executed", 2026-07-21).
- Risks or open questions: syrupy golden-template test not absorbed
  (no syrupy dep); `ATTUNE_AUTHOR_*` env names kept for behavior
  parity (rename is a later polish); single_turn's counters stay
  out of UsageTracker pending telemetry-models-layering OQ-2.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Absorbed machinery imports + jinja loads | `_build_jinja_env(None).list_templates()` via worktree PYTHONPATH | pass (16 templates) |
| Absorbed + adapted suites green | serial pytest `tests/unit/authoring` + `test_single_turn_*` | pass (691) |
| Touched-surface sweep | serial pytest models+memory+adapter+website-accuracy | pass (2570) |
| polish_master wiring live to the LLM boundary | credential-free run (`ATTUNE_AUTH_MODE=api`, empty key) | pass (exit 1 at credential check, RAG fired) |
| Skills mirror in sync | `sync_agents_skills.py --write` + guard tests | pass (58) |

## Next action

Open the draft PR (`hold-until-07-27`, `Closes #1567`); wait for full
CI including Windows lanes (touches path-handling code). On the
2026-07-27 sitting: lift the hold, merge, then execute T4 per D12 and
delete this handoff when the branch merges.
