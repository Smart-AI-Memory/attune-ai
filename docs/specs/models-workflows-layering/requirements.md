# Models↔Workflows Layering — Requirements

**Status:** draft (2026-08-25) — awaiting chair review
**Origin:** issue #2239 (2026-08-24 step-16 runner pair). Slice 1
(SDK adapter core + `sdk_errors` → `attune.models`, facade kept) was
executed as its own PR per the issue's verified plan; this spec owns
the REMAINDER, which the chair flagged as needing more than a one-off
prompt (2026-08-25): the `WorkflowConfig` edge, the four-way
`WorkflowConfig` name collision, and the flat-cluster
non-proliferation constraint.

---

## Problem

`attune.models` and `attune.workflows` had a circular dependency
managed by two lazy function-local imports. Slice 1 removed one edge
(`models/single_turn.py` → `workflows.agent_sdk_adapter`, now an
eager models-internal import). The remaining edge:

- **Edge 1 —** `models/empathy_executor.py:85` →
  `workflows.config.WorkflowConfig` (hybrid tier→model mapping).

The issue's original fix direction ("move the shared types into a
neutral lower layer") is **not implementable as written** — verified
2026-08-24: `workflows/config.py:28` imports `attune.models`
(`MODEL_REGISTRY`, `ModelInfo`, `ModelProvider`, `ModelTier`), so
`WorkflowConfig` cannot move below models without dragging the
registry with it.

Two adjacent structural problems make a naive move actively harmful:

1. **Four classes named `WorkflowConfig`** already exist:
   `workflows/config.py`, `agent_factory/base.py:102`,
   `config/sections/workflows.py:11`, `config/agent_config.py:265`.
   Relocating a fourth without a consolidation story deepens the
   confusion.
2. **~52 flat top-level packages** with overlapping orchestration
   responsibilities (`workflows`, `workflow_patterns`,
   `meta_workflows`, `pipeline`, `orchestration`, `roundtable`).
   Any layering work must at minimum not add to the cluster
   (slice 1 honored this: the adapter landed inside
   `attune/models/`, no new top-level package).

## Requirements

- **R1 — kill Edge 1 by dependency inversion, not relocation.**
  `EmpathyExecutor` takes its hybrid config as a constructor
  argument; the `workflows.yaml` read stays above models. Callers to
  migrate (verified 2026-08-24): `workflows/escalation/chain.py`,
  `workflows/escalation/evaluator.py`, `workflows/executor_mixin.py`,
  `models/resilient_executor.py`.
- **R2 — sequencing against the 15.0.0 empathy excision (#2238).**
  Edge 1 lives in `EmpathyLLMExecutor`'s module — the LIVE EmpathyLLM,
  not the dead EmpathyOS — so the excision does NOT moot it (verified
  2026-08-25: `EmpathyLLMExecutor` is exported from
  `models/__init__.py`). But #2238's `empathy_level` removal (D2,
  release-15 manifest) touches the same surfaces; R1 must either land
  before the excision or be folded into it, decided in design.
- **R3 — a ruled consolidation story for the four `WorkflowConfig`s**
  BEFORE any of them moves: merge, rename, or scoped-keep per class,
  recorded in `decisions.md`. No move without the ruling.
- **R4 — no new top-level packages.** Whatever homes emerge must live
  inside existing packages (`models/`, `config/`, …). Work that wants
  a 53rd top-level package is out of scope for this spec and needs
  its own ruling.
- **R5 — monkeypatch-target discipline.** Any relocation keeps the
  #2253/#2162 rule: definitions move WITH their tests' patch targets
  in the same PR; re-export shims carry a defining-module warning.
  Slice 1's `tests/unit/models/test_sdk_adapter_layering.py` is the
  pattern (subprocess no-upward-import probe + facade identity
  assertions).
- **R6 — flat-cluster scope fence.** The 52-package cluster
  consolidation is NOT this spec's execution scope — it is recorded
  here as the standing constraint (R4) plus an open design question
  for a future spec. This spec closes #2239 when Edge 1 is dead and
  R3 is ruled.

## Non-goals

- Consolidating the orchestration cluster (own spec, if ever).
- Touching the SDK adapter surface again (slice 1 shipped it).
- Any behavioral change to empathy tier mapping — R1 is pure
  wiring inversion.

## Open questions (for design)

1. R2 ordering: inversion-before-excision, or fold R1 into the
   #2238 remainder work?
2. R3: which of the four `WorkflowConfig`s is the survivor, and do
   the config-section ones merge or get renamed to their actual
   roles (`WorkflowsSection`, `AgentWorkflowConfig`, …)?
3. Does `workflows/config.py` (676 lines, 23 defs) split so the
   registry-independent parts can sink, or does it stay put once
   Edge 1 dies (simplest — nothing then NEEDS to move)?
