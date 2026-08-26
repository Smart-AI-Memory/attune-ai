# Models↔Workflows Layering — Requirements

**Status:** active (2026-08-25) — the three open questions were
chair-ruled same-day (D1–D3, `decisions.md`); design phase next
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
  argument **typed as a models-owned primitive** —
  `hybrid_config: dict[str, str] | None` (tier → model_id), the
  shape the executor already reduces `WorkflowConfig` to
  internally (`config.custom_models["hybrid"]`,
  `empathy_executor.py:89`). Accepting a
  `workflows.config.WorkflowConfig` as the argument type is
  explicitly NON-compliant: the annotation alone re-creates
  Edge 1 (cross-review finding, 2026-08-25).
  **Config-construction ownership:** the `workflows.yaml` read
  happens at the topmost workflows-layer call site only; no models
  module reads `workflows.yaml` or imports the config type
  (cross-review finding, 2026-08-25).

  **Caller list corrected 2026-08-26 (execution).** The
  2026-08-24 list named four sites; re-grepped against the tree at
  execution time, only ONE is a migration site:
  - `workflows/executor_mixin.py:133` — constructs with
    `provider=self._provider_str`, the only path that can be
    `"hybrid"`. **The injection site.**
  - `workflows/escalation/chain.py:112` and
    `workflows/escalation/evaluator.py:163` — both hardcode
    `provider="anthropic"`, so the hybrid read never fired for
    them. Nothing to inject; untouched.
  - `models/resilient_executor.py` — **not a caller.** The
    `EmpathyLLMExecutor` mentions at lines 40–41 are a `>>>`
    docstring example; the class takes a pre-built
    `executor: Any`. There is no constructor to thread a mapping
    through, so "injection chains upward through models-layer
    intermediaries" describes a chain that does not exist. The
    requirement's intent is unchanged — it is one hop, not a chain.

  **Receipt amended 2026-08-26 — the named probe is NOT sufficient
  on its own.** R1 originally named "the subprocess
  no-upward-import probe extended to
  `attune.models.empathy_executor`". Verified by mutation at
  execution time: that probe observes what a module import LOADS,
  so it is blind to a LAZY function-local import — and both #2239
  cycle edges were exactly that shape. Reinstating the original
  lazy `_load_hybrid_config` left the subprocess probe GREEN.
  (This also means slice 1's probe never proved slice 1; it proves
  the eager import graph stays clean, which is real but weaker
  than claimed.) The binding receipt is therefore a **static AST
  scan** — `test_no_models_module_imports_workflows_at_any_scope`
  — asserting no module under `src/attune/models/` imports
  `attune.workflows` at any scope, mutation-verified red against
  eager, lazy-function-local, and relative (`from ..workflows`)
  shapes. The subprocess probe is extended as specified and kept,
  since it additionally pins the eager import graph.
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

## Open questions — RULED (2026-08-25, see decisions.md)

1. R2 ordering → **D1: inversion first**, independent of #2238.
2. R3 → **D2: rename-by-role**; `workflows.config.WorkflowConfig`
   keeps the name, the other three get role-true names with
   deprecation aliases (exact names proposed in design).
3. `workflows/config.py` → **D3: split-on-trigger** — stays put
   today; the carve is pre-approved in direction and executes
   (under R4/R5, scope by grep) the first time a lower-layer
   consumer actually needs part of it. The CI no-upward-import
   probe holds the boundary meanwhile.
