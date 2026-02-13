# Modular Architecture Evolution Plan

## Status Tracker

| Phase | Track | Description | Status | Session |
|-------|-------|-------------|--------|---------|
| **1A** | Consolidation | Move 5 unique modules (hooks, learning, context, agents_md, utils/tokens) | **COMPLETE** | 1 |
| **1B** | Consolidation | Merge 4 complementary modules (routing, config, commands, patterns) | **COMPLETE** | 1 |
| **--** | Testing | Reorganize 131 test files into 14 domain subdirectories | **COMPLETE** | 1 |
| **--** | Testing | Remove 70 auto-generated behavioral test files (dead weight) | **COMPLETE** | 2 |
| **2A** | Workflows | Extract 7 services from mixins into services/ | **COMPLETE** | 2 |
| **3A** | Plugins | Plugin system improvements | **COMPLETE** | 3 |
| **3B** | Extraction | Dashboard + Socratic as optional extras | **COMPLETE** | 3 |
| **3C** | Extraction | Lazy loading improvements | **COMPLETE** | 3 |
| **2B-2C** | Workflows | WorkflowContext + BaseWorkflow update | **COMPLETE** | 3 |
| **1C** | Consolidation | Move LLM core + agent_factory (highest risk) | **COMPLETE** | 4 |
| **2D** | Workflows | Migrate concrete workflows (15/15, 100%) | **COMPLETE** | 4-5 |
| **1D** | Consolidation | Cleanup shims and config (after 2D) | **COMPLETE** | 5 |
| **3D** | Extraction | Memory/telemetry splitting | **COMPLETE** | 5 |
| **2E** | Workflows | Consolidate 12 overlapping workflows into 4 canonical groups | **COMPLETE** | 8 |

---

## Context

Attune AI has grown to 432+ Python files across 35+ modules. Three structural issues impede evolution:

1. **Dual packages** -- `attune_llm/` (75 files) and `src/attune/` (350+ files) have overlapping routing, config, and security with circular cross-imports
2. **Workflow mixin coupling** -- `BaseWorkflow` inherits from 11 mixins; adding/removing a capability touches the base class and affects all 30+ workflows
3. **Monolithic install** -- CLI and core import all subsystems eagerly; no way to install only what you need

---

## Track 1: Package Consolidation (attune_llm -> src/attune)

### Phase 1A: Move unique, zero-overlap modules (COMPLETE)

Moved these modules that had no counterpart in `src/attune/`:

| Source | Destination | Status |
|--------|-------------|--------|
| `attune_llm/hooks/` | `src/attune/hooks/` | Done |
| `attune_llm/learning/` | `src/attune/learning/` | Done |
| `attune_llm/context/` | `src/attune/context/` | Done |
| `attune_llm/agents_md/` | `src/attune/agents_md/` | Done |
| `attune_llm/utils/tokens.py` | `src/attune/utils/tokens.py` | Done |

**Shim pattern** (used for all migrations):

```python
"""attune_llm.hooks - DEPRECATED. Use attune.hooks instead."""
import warnings
warnings.warn(
    "attune_llm.hooks is deprecated. Use attune.hooks instead. "
    "Will be removed in v3.0.0.",
    DeprecationWarning, stacklevel=2,
)
from attune.hooks import *  # noqa: F401,F403
```

### Phase 1B: Merge complementary modules (COMPLETE)

| Source | Destination | Status |
|--------|-------------|--------|
| `attune_llm/routing/model_router.py` | `src/attune/routing/model_router.py` | Done |
| `attune_llm/config/unified.py` | `src/attune/config/agent_config.py` | Done |
| `attune_llm/commands/` | `src/attune/commands/` | Done |
| `attune_llm/pattern_*.py`, `git_pattern_extractor.py` | `src/attune/patterns/` | Done |

### Phase 1C: Move the LLM core (COMPLETE - Session 4)

Created `src/attune/llm/` sub-package for the most interconnected pieces:

- ✅ `attune_llm/core.py` (EmpathyLLM) -> `src/attune/llm/core.py`
- ✅ `attune_llm/providers.py` -> `src/attune/llm/providers.py`
- ✅ `attune_llm/state.py` -> `src/attune/llm/state.py`
- ✅ `attune_llm/levels.py` -> `src/attune/llm/levels.py`
- ✅ `attune_llm/agent_factory/` -> `src/attune/agent_factory/`

**Completed (2026-02-13):**

- Created deprecation shims in `attune_llm/` for all migrated modules
- Updated all imports in `src/attune/` to use new paths
- Fixed routing import in core.py (now uses `attune.routing`)
- Updated all agent_factory internal imports
- Tests passing, deprecation warnings working correctly

### Phase 1D: Cleanup and Documentation (COMPLETE - Session 5)

**COMPLETED:**

- ✅ Removed `test_gen_behavioral.py` - Problematic workflow replaced by `ParallelTestGenerationWorkflow`
- ✅ Cleaned up all imports/references to `BehavioralTestGenerationWorkflow` from `__init__.py`
- ✅ Documented deprecation timeline in CHANGELOG.md
- ✅ Added v3.0.0 removal notice for `attune_llm/` shims in CHANGELOG
- ✅ Updated migration guide (`docs/migration-guide.md`) with package consolidation instructions and import mapping table

**DO NOT (until v3.0.0):**

- ❌ Remove `attune_llm/` directory (shims bridge the gap for backward compatibility)
- ❌ Remove `"."` from `setuptools.packages.find.where` in pyproject.toml (package still exists)
- ❌ Remove `attune_llm` from ruff `known-first-party` (imports still valid)

---

## Track 2: Workflow Mixin Decoupling

### Phase 2A: Extract capability services (No breaking changes)

Convert each mixin into a standalone service class:

| Mixin | Service | Interface |
|-------|---------|-----------|
| `LLMMixin` | `LLMService` | `call(prompt, tier) -> str` |
| `CachingMixin` | `CacheService` | `get(key), set(key, val)` |
| `TelemetryMixin` | `TelemetryService` | `track(event)` |
| `CostTrackingMixin` | `CostService` | `record(tokens, cost)` |
| `TierRoutingMixin` | `TierService` | `route(task) -> tier` |
| `ExecutionMixin` | `ExecutionService` | `run_step(step) -> result` |
| `CoordinationMixin` | `CoordinationService` | `coordinate(agents)` |
| `StatePersistenceMixin` | `StateService` | `save(state), load()` |
| `MultiAgentStageMixin` | `MultiAgentService` | `run_stage(stage)` |
| `PromptMixin` | `PromptService` | `build_prompt(template, ctx)` |
| `ResponseParsingMixin` | `ParsingService` | `parse(response, format)` |

Each service lives in `src/attune/workflows/services/`.

### Phase 2B: Create WorkflowContext container

```python
@dataclass
class WorkflowContext:
    llm: LLMService
    cache: CacheService | None = None
    telemetry: TelemetryService | None = None
    cost: CostService | None = None
    tier: TierService | None = None
    state: StateService | None = None
```

### Phase 2C: Add composition path to BaseWorkflow

Add `ctx: WorkflowContext | None` parameter to `BaseWorkflow.__init__`. When provided, proxy methods delegate to `ctx.service.method()`. When `None`, fall back to mixin behavior. 100% backward compat.

### Phase 2D: Migrate concrete workflows incrementally (COMPLETE - Session 5)

Start with simpler workflows and migrate to `WorkflowContext`. Leave complex ones on mixins until stable.

**Progress: 15/15 workflows migrated (100%)**

#### Completed

- ✅ BugPredictionWorkflow (Session 2 or 3)
- ✅ DependencyCheckWorkflow (Session 2 or 3)
- ✅ ResearchSynthesisWorkflow (Session 2 or 3)
- ✅ TestGenerationWorkflow (Session 4)
- ✅ PerformanceAuditWorkflow (Session 4)
- ✅ CodeReviewWorkflow (Session 4)
- ✅ SecurityAuditWorkflow (Session 4)
- ✅ RefactorPlanWorkflow (Session 5)
- ✅ ReleasePreparationWorkflow (Session 5)
- ✅ DocumentManagerWorkflow (Session 5)
- ✅ KeyboardShortcutWorkflow (Session 5)
- ✅ NewSampleWorkflow1Workflow (Session 5)
- ✅ SEOOptimizationWorkflow (Session 5)
- ✅ DocumentGenerationWorkflow (Session 5)
- ✅ ParallelTestGenerationWorkflow (Session 5)

All workflows extending `BaseWorkflow` now support composition via `WorkflowContext` with `default_context()` classmethod.

#### Excluded (Deprecated/Problematic)

- ❌ BehavioralTestGenerationWorkflow - Problematic implementation, replaced by ParallelTestGenerationWorkflow. Candidate for removal in cleanup phase.

---

## Track 3: Subsystem Extraction and Plugin System

### Phase 3A: Plugin system improvements

1. Rename entry point group from `empathy_framework.plugins` to `attune.plugins`
2. Add WorkflowProtocol bridge
3. Add lifecycle hooks to BasePlugin: `on_activate()`, `get_cli_commands()`
4. Add plugin discovery cache

### Phase 3B: Extract Dashboard and Socratic as optional extras

Add to pyproject.toml:

```toml
dashboard = ["fastapi>=0.109.1,<1.0.0", "uvicorn>=0.20.0,<1.0.0"]
socratic = []
```

### Phase 3C: Lazy loading improvements

1. Convert `memory/__init__.py` to `__getattr__`-based lazy loading
2. Convert `cli/parsers/__init__.py` to lazy registration
3. Add subsystem-level availability checks

### Phase 3D: Memory and telemetry splitting (Future)

Split into core (always available) vs optional (needs Redis).

---

## Verification (after each phase)

1. `uv run pytest` -- all tests pass
2. `uv run ruff check src/` -- no lint errors
3. `python -c "import attune"` -- no circular imports
4. Old import paths still work via shims (where applicable)

---

## Phase 2E: Workflow Consolidation (COMPLETE - Session 8)

Consolidated 12 overlapping workflows into 4 canonical groups using the existing migration system (`migration.py`).

**Registry changes:** Removed 7 deprecated slugs from `_DEFAULT_WORKFLOW_NAMES`, redirected through `WORKFLOW_ALIASES` in `migration.py`:

| Removed Slug | Canonical Slug | Migration Kwargs |
| ---- | ---- | ---- |
| `pro-review` | `code-review` | `mode=premium` |
| `pr-review` | `code-review` | `mode=security` |
| `document-manager` | `doc-gen` | (deprecated) |
| `orchestrated-release-prep` | `release-prep` | `mode=full` |
| `autonomous-test-gen` | `test-gen-parallel` | `autonomous=True` |
| `progressive-test-gen` | `test-gen-parallel` | `progressive=True` |
| `test-coverage-boost` | `test-gen` | `target=coverage` |

**Deprecation warnings added to 8 classes:**
`DocumentManagerWorkflow`, `ManageDocumentationCrew` (already had), `ReleasePreparationCrew` (already had), `OrchestratedReleasePrepWorkflow`, `CodeReviewPipeline`, `PRReviewWorkflow`, `AutonomousTestGenerator`, `ProgressiveTestGenWorkflow`

**Backward compatibility preserved:** All class names remain in `_LAZY_WORKFLOW_IMPORTS` for direct imports. Migration system handles slug resolution with interactive dialog for first-time users.

---

## Refactoring Candidates (Future Work)

Identified during QA session 6 (2026-02-13). These are flagged for future cleanup -- no changes now.

### Removed (Session 7)

| File | Reason | Status |
| ---- | ------ | ------ |
| `src/attune/workflows/new_sample_workflow1.py` | Empty template with TODO stubs, zero logic | **REMOVED** |
| `src/attune/workflows/llm_base.py` | Unused abstract base class, 0% coverage, zero imports | **REMOVED** |

### Remaining Candidates

| File | Issue | Suggested Action |
| ---- | ----- | ---------------- |
| `src/attune/workflows/__init__.py` | 2 silent `except: pass` in discovery loop, complex registry logic | Add logging, simplify discovery |
| `src/attune/workflows/test_gen/workflow.py` | 7% coverage, 285 LOC, multiple TODOs | Redesign or consolidate with test_gen_parallel |
| `src/attune/workflows/autonomous_test_gen.py` | 13% coverage, 229 LOC | Overlaps with test_gen/, consolidate |
| `src/attune/workflows/progressive/` | 5-12% coverage across 4 files | Evaluate if dead code, remove or test |
| `src/attune/memory/simple_storage.py` | 12% coverage, overlaps with storage_backend.py | Consolidate into long_term.py (imports LongTermMemory) |
| `src/attune/telemetry/cli_analysis.py` | 0% coverage, 186 LOC | Evaluate if unused, remove or test |
| `src/attune/telemetry/cli_automation.py` | 0% coverage, 209 LOC | Evaluate if unused, remove or test |

---

## What NOT to do

- No big-bang rewrite -- each phase ships independently
- No new abstractions for one-time operations
- No removing `attune_llm/` until v3.0.0 (shims bridge the gap)
- No changing existing public API signatures without deprecation period
