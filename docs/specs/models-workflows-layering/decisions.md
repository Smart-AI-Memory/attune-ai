# Models↔Workflows Layering — Decisions

Chair rulings, batched form, 2026-08-25 (this session — the
open-questions walkthrough Patrick requested after the spec-text
cross-review lane).

## D1 — Edge-1 inversion lands FIRST, independent of #2238 (ruled 2026-08-25)

The R1 constructor inversion ships as its own small PR (4 call
sites + constructor + probe extension), not folded into the 15.0.0
empathy-excision train. A dead Edge 1 simplifies whatever the
excision later touches. (Chair picked the lead's recommendation.)

## D2 — WorkflowConfig story is RENAME-BY-ROLE (ruled 2026-08-25)

`workflows.config.WorkflowConfig` keeps the name (the public
`workflows.yaml`-backed one). The other three
(`agent_factory/base.py`, `config/sections/workflows.py`,
`config/agent_config.py`) get role-true names with deprecation
aliases. This is a DIRECTION ruling: exact names are verified and
proposed in the design phase, per-class, against what each actually
does — not invented here. Consolidation-to-one-class and
keep-and-document were both declined. (Chair picked the lead's
recommendation.)

## D3 — workflows/config.py: SPLIT-ON-TRIGGER (ruled 2026-08-25)

Ruling history, kept honest: a first form pick landed on
"split now" and the chair immediately flagged it as a misclick; on
re-ask the chair requested the full pros/cons before ruling. With
the analysis on the table (no consumer exists by construction after
D1's injection; the file's seam is registry-bound, not clean; the
subprocess no-upward-import probe already gates the boundary
mechanically; 35 importers make any carve expensive), the chair
ruled the middle path the lead recommended:

**Stay put today; the split is PRE-APPROVED in direction and
executes — no fresh ruling needed — the first time a lower-layer
consumer actually needs a piece of `workflows/config.py`.** Binding
constraints on the triggered split:

- **R4 fence holds:** no new top-level package — the carved module
  lands inside an existing package (in practice `attune/models/`,
  since the trigger IS a lower-layer consumer).
- **R5 discipline holds:** definitions move WITH their tests'
  monkeypatch targets in the same PR; any back-compat re-export
  carries the defining-module warning; the slice-1 identity-test
  pattern applies.
- Scope of "registry-free" is determined at trigger time by grep,
  not by this spec's guess (the code is the contract): anything
  importable without `attune.models` is a candidate; anything
  touching `MODEL_REGISTRY`/`ModelTier` stays.
- Until the trigger fires, the CI probe
  (`tests/unit/models/test_sdk_adapter_layering.py`, extended per
  amended R1) is the boundary's enforcer.

## D4 — `config/agent_config.WorkflowConfig` is DELETED, not renamed (ruled 2026-08-26)

The design phase found what D2's ruling did not have in front of it:
that class is field-for-field identical to `agent_factory/base.py`'s
(same ten fields, pydantic twin of a dataclass) and has NO consumer —
`AgentWorkflowConfig` appears exactly twice in the tree, both in
`config/__init__.py` (the aliased import and its `__all__` entry). No
src caller, no test, no doc. It entered in `dc6c8f69e` AFTER the
dataclass (`faeac70db`), as consolidation leftover.

Against `removing-dead-code.md` this trips zero-usage-evidence and
orphaned-motivation, whose gate says stop renaming the surface and
remove the engine. The chair took the lead's recommendation to delete
rather than rename, together with the `AgentWorkflowConfig` alias
export. This does NOT reopen D2's declined
consolidation-to-one-class: that ruling concerned LIVE classes, and
this one is not live.

## D5 — `agent_factory/base.WorkflowConfig` -> `AgentGraphConfig` (ruled 2026-08-26)

Chair ruled yes, having read the counter-case the lead raised against
its own recommendation: inside its own module the current name is
already coherent beside `AgentConfig`/`BaseAgent`/`BaseWorkflow`, so
the collision is only visible globally, and the rename costs 8 sites.
D2's intent — that exactly one class holds the bare name — outranks
local coherence, and the deprecation alias absorbs the churn.

`config/sections/workflows.py` -> `WorkflowsConfig` was not in
dispute: its six sibling sections are all `<module>Config`
(`AnalysisConfig`, `AuthConfig`, `EnvironmentConfig`,
`PersistenceConfig`, `RoutingConfig`, `TelemetryConfig`) and it is
the only one breaking the pattern. 3 import sites.

## Sequencing after these rulings

1. D1 inversion PR — SHIPPED as #2314 (Edge 1 dead; the boundary is
   now gated by a static AST scan, since the subprocess probe R1
   originally named proved blind to lazy function-local imports).
2. D4 delete first — it removes a third of the collision and the
   duplication question in one step.
3. `config/sections` rename (3 sites), then D5 (8 sites). One PR per
   class: each independently revertible, and the test churn should
   not ride with the three-line change. Aliases first, hard rename at
   the next major, per D2.
4. D3 sleeps until its trigger; no scheduled work.
