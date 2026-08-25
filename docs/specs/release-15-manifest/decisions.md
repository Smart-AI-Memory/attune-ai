# 15.0.0 Manifest — Decisions

Append-only. Chair rules; the lead records.

## D1 — attune.exceptions removal rides 15.0.0 (PRE-AUTHORIZED chair 2026-08-22)

Recorded from the standing hold: the removal is DONE on
`claude/eager-mendeleev-3352e2` (92a3714b7) and the chair
pre-authorized it into the next major on 2026-08-22 — unpark at
release prep, do not re-ask. Branch state re-verified 2026-08-24
(`git merge-tree` vs `origin/main`): two mechanical content
conflicts, `CHANGELOG.md` and `src/attune/__init__.py`. First
passenger.

## D2 — Fate of `empathy_level` (RATIFIED chair 2026-08-24 — Option B, die with the framework)

The 1–5 level concept survives the 9.0.0 framework excision as a
live knob: agent_factory
([base.py:83](../../../src/attune/agent_factory/base.py)), config,
llm state, plugin discovery, and the MCP tools
`attune_get_level`/`attune_set_level`. Removing the framework while
keeping the knob is incoherent long-term. **This ruling gates
#2238's breaking half** — the replacement plugin `BaseWorkflow`
signature and the MCP tool surface both depend on it.

**Option A — survive under a new name.** The knob is reframed as a
generic capability/depth level (e.g. `analysis_level`), plumbing
kept, MCP tools renamed with 14.x aliases. Pro: no behavior change
for anyone using levels; smaller diff. Con: carries a 5-point scale
whose semantics were defined BY the retired framework — the rename
keeps the ghost's shadow.

**Option B — die with the framework.** Level plumbing removed from
agent_factory/config/llm state; `attune_get_level`/`attune_set_level`
deleted (14.x deprecation first); plugin contract loses the
parameter. Pro: coherent end-state, one less concept. Con: largest
blast radius of any 15.0.0 item; any external caller of the level
tools breaks.

**RULING (chair, 2026-08-24): Option B.** The level concept dies
with the framework. Consequences now unblocked for #2238's
breaking half:

- 15.0.0 removes `empathy_level` plumbing from agent_factory,
  config, and llm state; the replacement plugin `BaseWorkflow`
  contract carries no level parameter.
- `attune_get_level`/`attune_set_level` MCP tools are deleted in
  15.0.0, with a 14.x `DeprecationWarning` first (deprecation-story
  item 3 in requirements.md now has its shape).
- Blast-radius acknowledgment from the option text stands: any
  external caller of the level tools breaks at 15.0.0 — the 14.x
  deprecation window is the mitigation.

## D3 — anthropic SDK 1.x does NOT ride the major (RECORDED lead 2026-08-24; chair may overrule)

Basis, verified against the 2026-08-24 tree: the migration
substantively landed in 14.x. #2254 (merged 2026-08-24, closing
work under #2243) widened the ceiling to `anthropic>=0.40.0,<2.0.0`
with core 1.x compatibility (sampling params via `extra_body`)
verified live on both a 0.125 lock env and a scratch 1.0.0 env —
per the pyproject comment and the #2254 changelog. The manifest's
"<1.0.0 ceiling stays" premise was stale by one day.

Remainder, not major-scoped: the dev lockfile stays on 0.x until
langchain-anthropic (dev/test extra) widens its `<1.0.0` pin
upstream. When the lock adopts 1.x, that PR carries a **live-fire
receipt requirement** (real SDK round-trip on the locked env, not
the scratch env). Issue #2243 stays open to track lock adoption.

## D4 — Timing (chair constraint, recorded verbatim 2026-08-24) — SUPERSEDED by D5

> the major must NOT ship before mid-to-late September 2026.
> attune-ai's first external user begins onboarding 2026-09-01 and
> a stable 14.x during his first weeks is worth more than the
> architecture.

## D5 — Timing INVERTED: ship before 2026-09-01; the class starts on 15.0.0 (RATIFIED chair 2026-08-25 — supersedes D4)

The 2026-09-01 onboarding is a **class** (cohort), not a lone
user, and the chair wants the class working on 15.0.0 from day
one. This inverts D4's premise: instead of holding the major so
the first weeks happen on stable 14.x, the major ships BEFORE the
class arrives — they never see the legacy surfaces or a
mid-course breaking change.

Consequences:

- **The 14.x deprecation story is no longer a prerequisite.**
  Warning shims protect existing external consumers; telemetry
  signal is ~0 and the class starts fresh on 15.0.0. Items
  already landed (`AttuneMCPServer` alias, dual-read entry-point
  discovery, level-tool `DeprecationWarning`s) simply ride until
  their 15.0.0 removal. The one unlanded item (old `BaseWorkflow`
  warning on instantiation, deprecation-story item 3) is DROPPED,
  not built.
- **Window:** ~6 days from ruling (2026-08-25 → 2026-08-31). The
  squeeze is CI cycles and the release-audit sitting, not code
  volume.

## D6 — Passenger 1 correction: attune.exceptions removal already SHIPPED (recorded lead 2026-08-25)

D1/passenger 1 describe the removal as parked on
`claude/eager-mendeleev-3352e2` awaiting a boarding rebase. Stale:
it merged as PR #2177 (`093cd7acd`, `feat!: remove the legacy
attune.exceptions hierarchy`) and shipped in 14.0.0 —
`src/attune/exceptions.py` is absent from `origin/main` (verified
2026-08-25 against `f2f3fe97a`). Nothing boards for it; the
parked branch is superseded and can be deleted.

## D7 — D2 scope clarification: PUBLIC level surface only (RATIFIED chair 2026-08-25)

Executing D2 against the tree surfaced a two-layer reality the
ruling's text did not distinguish:

- **Shallow public knobs** — plugin `BaseWorkflow.empathy_level` +
  `get_empathy_level()`, `PluginRegistry.find_workflows_by_level`
  (+ `workflows_by_level` stats), `UnifiedAgentConfig.empathy_level`,
  agent_factory `AgentConfig.empathy_level` + factory param,
  agents_md frontmatter parsing/validation +
  `get_by_empathy_level`, the two MCP level tools,
  `MetricsCollector.record_metric(empathy_level=…)` (top-level
  public export; SQLite column migration), and the first-run
  config template.
- **The engine** — `EmpathyLLM` (llm/core.py) is itself a
  five-level progression machine (`_determine_level`,
  `_level_1_reactive`…`_level_5_systems`,
  `CollaborationState.current_level`/`level_history`), imported by
  14 modules. D2's "llm state" item, executed literally, guts a
  live class with no specced replacement.

**RULING (chair, 2026-08-25): 15.0.0 removes the public level
surface only** (the shallow list above — the user-visible API is
level-free). `EmpathyLLM`'s internal progression stays as
un-exported implementation detail (it is not in `attune.__all__`);
its redesign or retirement is spun off as its own post-15 issue.
llm/state, learning/evaluator internals, and the security audit
log's level field ride along untouched as internals.
