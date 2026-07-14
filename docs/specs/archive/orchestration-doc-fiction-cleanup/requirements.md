# Requirements — orchestration-doc-fiction-cleanup

**Status:** complete (2026-06-26) — shipped in PR #1107 (merged); reconciled at 2026-07-14 triage (was: executed — pending PR)
**Owner:** Patrick + agent
**Origin:** documentation trailing edge of PR #1096
(`feat(orchestration)!: remove dead DynamicTeam engine`), which
removed two orchestration features the docs still present as live.

---

## Problem

PR #1096 removed two orchestration code paths as dead:

- The `DynamicTeam` / `DynamicTeamBuilder` / `SDKAgent` /
  `SDKAgentTeam` engine.
- The `attune.orchestration.meta_orchestrator` module
  (`MetaOrchestrator`, the natural-language meta-orchestrator).

The documentation never followed. **25 files** still reference these
removed symbols — including full code examples and two ~800–900-line
tutorials — so a reader who copies them hits `ImportError`. This is
fiction: docs describing APIs that no longer exist.

Verified against `origin/main` (096b228f3):

- `DynamicTeam`, `DynamicTeamBuilder`, `class SDKAgent`,
  `SDKAgentTeam` — **0** references in `src/` (gone).
- `src/attune/orchestration/meta_orchestrator.py` — **GONE**.
- A same-named `MetaOrchestrator` exists in
  `src/attune/workflows/progressive/orchestrator.py` — an **unrelated**
  tier-escalation class, NOT a successor.

---

## The two removed concepts differ in successor status

This distinction drives every per-file decision:

- **`DynamicTeam` HAS a successor.** The working parallel-team
  primitive is now `attune.agents.team` —
  `AgentTeam(agents, gates)`, `WorkflowAgent(key, workflow_cls,
  *, files=...)`, `GateSpec(name, agent_key, threshold,
  critical=True)`, returning `TeamReport`. Live usage:
  `src/attune/pipeline/orchestrator.py:245` (the `/spec` quality
  gate). DynamicTeam docs get **rewritten** to this API.
- **`MetaOrchestrator` has NO successor.** The meta-orchestration
  feature was removed, not relocated. Its docs describe a feature
  that no longer exists and get **deleted**, per
  `.claude/rules/attune/removing-dead-code.md`.

---

## What must be preserved (NOT fiction)

`attune.orchestration` still exists and exports live symbols. Docs
that reference these are correct and must survive any cleanup:

- Agent templates: `AgentTemplate`, `AgentCapability`,
  `ResourceRequirements`, `get_template`, `get_all_templates`,
  `get_registry`, `get_templates_by_capability`,
  `get_templates_by_tier`, `register_custom_template`,
  `unregister_template`.
- Execution strategies: `ExecutionStrategy`, `get_strategy`,
  `ToolEnhancedStrategy`, `PromptCachedSequentialStrategy`,
  `DelegationChainStrategy`.

Several heavy docs (e.g. `ORCHESTRATION_API.md` has 53 surviving-symbol
references alongside 24 DynamicTeam + 14 MetaOrchestrator) need
**section-level surgery**, not wholesale deletion.

---

## Goals

- G1. No published doc presents a removed symbol
  (`DynamicTeam`/`DynamicTeamBuilder`/`SDKAgent`/`SDKAgentTeam`/
  `MetaOrchestrator`) as a live API.
- G2. Every surviving-symbol reference (templates, strategies) is
  preserved.
- G3. Every code example that remains imports and runs against
  `origin/main` (verified, per the website-content-accuracy rule).
- G4. The generated help bundle is fixed at its single source
  (`content/features/orchestration.md`), then re-projected — never
  hand-edited under `plugin/help/generated/`.
- G5. Append-only history (bug log, prior specs) is left untouched.

---

## Out of scope

- Building any replacement for the meta-orchestration feature.
- Rewriting orchestration prose beyond removing/repointing the dead
  symbols (no tone/IA overhaul).
- The `attune.orchestration` package itself (code is already correct;
  this spec only fixes docs).

---

## Acceptance criteria (Done when)

- `git grep -nE 'DynamicTeam|DynamicTeamBuilder|class SDKAgent|`
  `SDKAgentTeam|MetaOrchestrator' -- docs/ plugin/help/` returns only
  matches inside append-only history (COVERAGE_BUG_LOG.md,
  docs/specs/**) — zero in user-facing docs.
- Every code fence remaining in the touched docs uses only symbols
  importable from `origin/main` (spot-checked by import).
- Generated help regenerated from source; `plugin/help/generated/`
  diff is a product of the projector, not hand edits.
- One PR, CI green (docs-only; the 8 required checks).

---

## See also

- `tasks.md` — the per-file decision table and phased execution.
- `decisions.md` — D1–D5 rationale.
- `.claude/rules/attune/removing-dead-code.md` — delete-vs-rewrite
  rule this spec applies.
- `docs/specs/archive/doc-fiction-cleanup/` — prior art (same class
  of cleanup).
