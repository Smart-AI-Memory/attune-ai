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

## Sequencing after these rulings

1. D1 inversion PR (R1 as amended by the 2026-08-25 cross-review
   lane: `dict[str, str]` primitive arg, injection chains upward).
2. D2 renames, spread over the design phase's proposal — aliases
   first, hard rename at the next major.
3. D3 sleeps until its trigger; no scheduled work.
