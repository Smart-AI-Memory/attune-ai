# Wizard Migration Plan — Workflows to Wizards

**Version:** 1.0
**Created:** February 2026
**Status:** In Progress

---

## Architecture Overview

```text
                    ┌─────────────────────┐
                    │   Domain Hubs        │
                    │ /dev /testing /workflows │
                    └──────────┬──────────┘
                               │ routes to
                    ┌──────────▼──────────┐
                    │   Built-in Wizards   │
                    │ SecurityWizard, etc.  │
                    └──────────┬──────────┘
                               │ delegates to (via _run_llm_step override)
                    ┌──────────▼──────────┐
                    │   Existing Workflows │
                    │ SecurityAuditWorkflow │
                    │ RefactorPlanWorkflow  │
                    └──────────┬──────────┘
                               │ uses
                    ┌──────────▼──────────┐
                    │   BaseWorkflow Mixins │
                    │ LLM, Cache, Telemetry │
                    └─────────────────────┘
```

**Key principle**: Wizards provide guided UX (AskUserQuestion + XML decomposition). Workflows provide the analysis engine (multi-stage pipelines). The wrapper pattern combines both.

---

## Completed Migrations

### SecurityWizard + SecurityAuditWorkflow (Phase 3)

- **File:** `src/attune/wizards/builtin/security_wizard.py`
- **Pattern:** `_run_llm_step()` override delegates `scan` step to triage+analyze+assess, `generate_fixes` step to remediate
- **Fallback:** Graceful — if workflow fails, falls back to independent LLM call
- **Status:** Done

### RefactorWizard + RefactorPlanWorkflow (Phase 3)

- **File:** `src/attune/wizards/builtin/refactor_wizard.py`
- **Pattern:** `_run_llm_step()` override delegates `analyze` step to scan+analyze+prioritize+plan
- **Fallback:** Graceful — if workflow fails, falls back to independent LLM call
- **Status:** Done

---

## Migration Candidates

| # | Workflow | Wizard | Priority | Complexity | Target |
| --- | ---------- | -------- | ---------- | ------------ | -------- |
| 1 | `CodeReviewWorkflow` | New: CodeReviewWizard | Medium | Medium | v2.9 |
| 2 | `BugPredictWorkflow` | New: BugPredictWizard | Low | Low | v2.9 |
| 3 | `PerfAuditWorkflow` | New: PerfAuditWizard | Low | Medium | v3.0 |
| 4 | `SecureReleaseWorkflow` | ReleasePrepWizard | Medium | High | v3.0 |
| 5 | `TestGenWorkflow` (pkg) | TestGenWizard | Low | Low | v2.9 |
| 6 | `SEOOptimizationWorkflow` | New: SEOWizard | Low | Low | v3.0 |

### 1. CodeReviewWorkflow → CodeReviewWizard

**File:** `src/attune/workflows/code_review.py`
**Stages:** scan → analyze → report
**Approach:**

- Create `src/attune/wizards/builtin/code_review_wizard.py`
- Steps: QUESTION (scope, focus) → LLM_CALL (delegates to workflow) → TASK_DECOMPOSE → PREVIEW
- Register in `builtin/__init__.py` and `pyproject.toml`
- Update `/dev review` and `/workflows review` hub routing

**Dependencies to check:** WorkflowComposer, test files

### 2. BugPredictWorkflow → BugPredictWizard

**File:** `src/attune/workflows/bug_predict.py`
**Stages:** scan → analyze → report
**Approach:**

- Create `src/attune/wizards/builtin/bug_predict_wizard.py`
- Steps: QUESTION (target path) → LLM_CALL (delegates to workflow) → PREVIEW
- Simpler than security — single analysis pass, no remediation

**Dependencies to check:** CLI `workflow run bug-predict`, test files

### 3. PerfAuditWorkflow → PerfAuditWizard

**File:** `src/attune/workflows/perf_audit.py`
**Stages:** scan → analyze → optimize
**Approach:**

- Create `src/attune/wizards/builtin/perf_audit_wizard.py`
- Steps: QUESTION (target, focus areas) → LLM_CALL (scan+analyze) → LLM_CALL (optimize, conditional) → TASK_DECOMPOSE → PREVIEW

**Dependencies to check:** CLI `workflow run perf-audit`, test files

### 4. SecureReleaseWorkflow → ReleasePrepWizard Enhancement

**File:** `src/attune/workflows/secure_release.py`
**Stages:** security-check → test-check → version-check → publish
**Approach:**

- Enhance existing ReleasePrepWizard to delegate security-check step to SecurityAuditWorkflow (already wrapped)
- Add test-check step that runs pytest
- Most complex: coordinates multiple workflows
- Consider making this the last migration

**Dependencies to check:** Release pipeline, CI integration

### 5. TestGenWorkflow → TestGenWizard Enhancement

**File:** `src/attune/workflows/test_gen/` (package)
**Note:** TestGenWizard already exists and hub routing already points to it
**Approach:**

- Add `_run_llm_step()` override in TestGenWizard to delegate to workflow package
- Low priority since hub routing already works

### 6. SEOOptimizationWorkflow → SEOWizard

**File:** `src/attune/workflows/seo_optimization.py`
**Approach:**

- Create wizard with QUESTION (target URL, mode) → LLM_CALL (audit) → PREVIEW
- Low priority, specialized use case

---

## Per-Workflow Migration Template

Use this checklist when migrating any workflow to a wizard:

### Step 1: Analyze the Workflow

- [ ] Read the workflow file and document stages, tier_map, and data flow
- [ ] Identify all dependents (`grep -r "WorkflowName(" src/ tests/`)
- [ ] Count test files and determine if any test internal stage logic
- [ ] Check for MCP integration, CLI entry points, and orchestration usage

### Step 2: Create or Update the Wizard

- [ ] Create `src/attune/wizards/builtin/<name>_wizard.py`
- [ ] Define `config` (WizardConfig) and `steps` (list of WizardStep)
- [ ] Implement `build_prompt_context()` for LLM fallback
- [ ] Implement `process_step_result()` for session storage
- [ ] Override `_run_llm_step()` to delegate to workflow
- [ ] Add `_get_or_create_workflow()` with lazy instantiation
- [ ] Add graceful fallback in `_run_llm_step()` (`try/except → super()`)

### Step 3: Register and Route

- [ ] Add to `builtin/__init__.py` BUILTIN_WIZARDS dict
- [ ] Add entry point in `pyproject.toml` under `[project.entry-points."empathy.wizards"]`
- [ ] Add keyword(s) in `cli_router.py`
- [ ] Update relevant domain hub `.md` file(s) to route through wizard flow

### Step 4: Test

- [ ] Verify wizard loads: `python -c "from attune.wizards import get_wizard; get_wizard('<id>')"`
- [ ] Verify existing workflow tests still pass (no API changes)
- [ ] Verify existing workflow dependents still work (import + instantiate)
- [ ] Test graceful fallback: mock workflow import failure, verify LLM fallback works

### Step 5: Document

- [ ] Update this migration plan (mark as completed)
- [ ] Update CHANGELOG.md

---

## Deprecation Strategy

### Phase A: Wrapper Period (Current — v2.8)

- Wizards delegate to workflows via `_run_llm_step()` override
- All existing workflow APIs remain unchanged
- No runtime warnings
- `pyproject.toml` entry points marked with `# Superseded by wizards` comment

### Phase B: Soft Deprecation (v2.9)

- Add `warnings.warn()` to workflow `execute()` methods (not `__init__`)
- Warning message: "Direct workflow execution is deprecated. Use the wizard instead: `from attune.wizards import get_wizard; wizard = get_wizard('<id>')`"
- Category: `DeprecationWarning` (silent in production, visible in tests with `-W`)
- Skip warning if called from wizard wrapper (check call stack or pass `_internal=True`)

### Phase C: Documentation Deprecation (v3.0)

- Update all documentation to reference wizards as primary API
- Remove workflow examples from quickstart guides
- Keep workflow API reference with deprecation notices

### Phase D: API Removal (v4.0)

- Remove deprecated workflow entry points from `pyproject.toml`
- Remove CLI `workflow run` commands that have wizard replacements
- Keep workflow classes as internal implementation (used by wizard wrappers)
- Never delete the workflow code — it's the engine underneath the wizards

---

## Testing Requirements Per Migration

| Test Category | What to Verify |
| --------------- | ---------------- |
| Import | Wizard class loads without error |
| Registry | `get_wizard("<id>")` returns the correct class |
| Listing | `list_wizards()` includes the new wizard |
| Fallback | If workflow import fails, LLM fallback works |
| Delegation | Workflow stages are called with correct input |
| Session | Results are stored in session correctly |
| Existing tests | All workflow tests pass unchanged |
| Hub routing | Domain hub `.md` file routes correctly |

---

## Risk Mitigation

| Risk | Mitigation |
| ------ | ------------ |
| Workflow API changes break wizard wrapper | Wrapper catches all exceptions, falls back to LLM |
| Circular imports | Lazy import inside `_get_or_create_workflow()` |
| Performance overhead of double initialization | Lazy instantiation, cached on instance |
| Breaking existing tests | Zero workflow API changes — only wizards change |
| Noisy deprecation warnings | Defer to Phase B, use `execute()` not `__init__()` |

---

## Timeline Summary

| Version | Milestone |
| --------- | ----------- |
| v2.8 (current) | SecurityWizard + RefactorWizard wrappers |
| v2.9 | CodeReview, BugPredict, TestGen wizard wrappers |
| v3.0 | PerfAudit, SecureRelease, SEO wizard wrappers + soft deprecation |
| v4.0 | Remove deprecated workflow entry points |
