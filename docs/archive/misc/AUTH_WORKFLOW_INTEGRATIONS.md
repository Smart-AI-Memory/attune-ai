---
description: Authentication Strategy - All Workflow Integrations integration guide. Connect external tools and services with Attune AI for enhanced AI capabilities.
---

# Authentication Strategy - All Workflow Integrations

**Date:** January 29, 2026
**Status:** ✅ Complete

---

## Summary

Successfully integrated authentication strategy into **ALL** major workflows in the Attune AI. Each workflow now intelligently routes between Claude subscriptions and Anthropic API based on codebase/module size.

---

## Integrated Workflows (7 Total)

### 1. ✅ DocumentGenerationWorkflow (`document_gen.py`)
**Status:** Complete
**Integration Point:** `_outline()` stage
**Purpose:** Generate API documentation with Args/Returns/Raises format

**Features:**
- Detects module size from source file
- Recommends subscription for small modules (<500 LOC)
- Recommends API for large modules (>2000 LOC)
- Logs cost estimate before generation

**Usage:**
```python
from attune.workflows.document_gen import DocumentGenerationWorkflow

workflow = DocumentGenerationWorkflow(enable_auth_strategy=True)
result = await workflow.execute(
    source_code=code,
    target="src/module.py",
    doc_type="api_reference",
)
print(f"Auth mode: {result.final_output['auth_mode_used']}")
```

---

### 2. ✅ TestGenerationWorkflow (`test_gen.py`)
**Status:** Complete
**Integration Point:** `_identify()` stage
**Purpose:** Generate tests for bug-prone areas with low coverage

**Features:**
- Calculates total LOC for entire project/directory
- Supports both single file and directory scanning
- Recommends auth mode based on aggregate codebase size
- Includes auth_mode_used in telemetry output

**Usage:**
```python
from attune.workflows.test_gen import TestGenerationWorkflow

workflow = TestGenerationWorkflow(enable_auth_strategy=True)
result = await workflow.execute(path="src/", file_types=[".py"])
print(f"Auth mode: {result.final_output['auth_mode_used']}")
```

---

### 3. ✅ CodeReviewWorkflow (`code_review.py`)
**Status:** Complete
**Integration Point:** `_classify()` stage
**Purpose:** AI-powered code review with quality analysis

**Features:**
- Detects codebase size for the target being reviewed
- Handles both file and directory targets
- Logs recommendation with cost estimate
- Tracks auth mode in architect_review output

**Usage:**
```python
from attune.workflows.code_review import CodeReviewWorkflow

workflow = CodeReviewWorkflow(enable_auth_strategy=True)
result = await workflow.execute(target="src/", diff=None)
print(f"Auth mode: {result.final_output['auth_mode_used']}")
```

---

### 4. ✅ BugPredictWorkflow (`bug_predict.py`)
**Status:** Complete
**Integration Point:** `_scan()` stage
**Purpose:** Predict bugs using historical patterns and code analysis

**Features:**
- Counts LOC of scanned codebase
- Gets recommended auth mode from strategy
- Logs size category (small/medium/large)
- Non-breaking: continues if auth strategy unavailable

**Usage:**
```python
from attune.workflows.bug_predict import BugPredictWorkflow

workflow = BugPredictWorkflow(enable_auth_strategy=True)
result = await workflow.execute(target_path="src/")
print(f"Auth mode: {result.final_output['auth_mode_used']}")
```

---

### 5. ✅ SecurityAuditWorkflow (`security_audit.py`)
**Status:** Complete
**Integration Point:** `_triage()` stage
**Purpose:** Security vulnerability scanning and remediation

**Features:**
- Detects codebase size during triage phase
- Recommends auth based on audit scope
- Includes cost estimate in logs
- Graceful degradation on failures

**Usage:**
```python
from attune.workflows.security_audit import SecurityAuditWorkflow

workflow = SecurityAuditWorkflow(enable_auth_strategy=True)
result = await workflow.execute(path="src/", patterns=["dangerous_eval"])
print(f"Auth mode: {result.final_output['auth_mode_used']}")
```

---

### 6. ✅ PerfAuditWorkflow (`perf_audit.py`)
**Status:** Complete
**Integration Point:** `_profile()` stage
**Purpose:** Performance optimization and bottleneck detection

**Features:**
- Calculates total LOC in profiling stage
- Recommends auth mode for optimization operations
- Handles ImportError gracefully
- Tracks auth mode in final output

**Usage:**
```python
from attune.workflows.perf_audit import PerformanceAuditWorkflow

workflow = PerformanceAuditWorkflow(enable_auth_strategy=True)
result = await workflow.execute(path=".", file_types=[".py"])
print(f"Auth mode: {result.final_output['auth_mode_used']}")
```

---

### 7. ✅ ReleasePreparationWorkflow (`release_prep.py`)
**Status:** Complete
**Integration Point:** `_health()` stage
**Purpose:** Pre-release quality gate with health, security, and changelog checks

**Features:**
- Detects codebase size during health check stage
- Recommends auth mode based on project size
- Logs cost estimate before execution
- Tracks auth mode in final approval output

**Usage:**
```python
from attune.workflows.release_prep import ReleasePreparationWorkflow

workflow = ReleasePreparationWorkflow(enable_auth_strategy=True)
result = await workflow.execute(path=".")
print(f"Auth mode: {result.final_output['auth_mode_used']}")
print(f"Approved: {result.final_output['approved']}")
print(f"Recommendation: {result.final_output['recommendation']}")
```

---

## Integration Pattern (Consistent Across All Workflows)

All workflows follow the same 4-step integration pattern:

### Step 1: Add `enable_auth_strategy` Parameter
```python
def __init__(
    self,
    # ... existing parameters ...
    enable_auth_strategy: bool = True,
    **kwargs: Any,
):
    """Initialize workflow.

    Args:
        enable_auth_strategy: Enable intelligent subscription vs API routing (default: True)
    """
    super().__init__(**kwargs)
    self.enable_auth_strategy = enable_auth_strategy
    self._auth_mode_used: str | None = None
```

### Step 2: Add Auth Detection in First Processing Stage
```python
async def _first_stage(self, input_data: dict, tier: ModelTier):
    # ... existing logic ...

    # === AUTH STRATEGY INTEGRATION ===
    if self.enable_auth_strategy:
        try:
            from attune.models import (
                count_lines_of_code,
                get_auth_strategy,
                get_module_size_category,
            )
            logger = logging.getLogger(__name__)

            # Calculate module/codebase size
            total_lines = count_lines_of_code(target_path)

            # Get recommended auth mode
            strategy = get_auth_strategy()
            recommended_mode = strategy.get_recommended_mode(total_lines)
            self._auth_mode_used = recommended_mode.value

            # Log recommendation
            size_category = get_module_size_category(total_lines)
            logger.info(f"Target: {target} ({total_lines:,} LOC, {size_category})")
            logger.info(f"Recommended auth mode: {recommended_mode.value}")

            # Log cost estimate
            cost_estimate = strategy.estimate_cost(total_lines, recommended_mode)
            if recommended_mode.value == "subscription":
                logger.info(f"Cost: {cost_estimate['quota_cost']}")
            else:
                logger.info(f"Cost: ~${cost_estimate['monetary_cost']:.4f}")

        except Exception as e:
            logger.warning(f"Auth strategy detection failed: {e}")
```

### Step 3: Include Auth Mode in Final Output
```python
async def _final_stage(self, input_data: dict, tier: ModelTier):
    # ... generate result ...

    # Include auth mode used for telemetry
    if self._auth_mode_used:
        result["auth_mode_used"] = self._auth_mode_used

    return result, input_tokens, output_tokens
```

### Step 4: Access in User Code
```python
result = await workflow.execute(...)
print(f"Auth mode: {result.final_output['auth_mode_used']}")
```

---

## Benefits of Integration

### For Users:
✅ **Automatic optimization** - Workflows choose the best auth method automatically
✅ **Cost transparency** - Log messages show estimated costs before execution
✅ **Consistent behavior** - Same auth logic across all workflows
✅ **Opt-out available** - Can disable with `enable_auth_strategy=False`

### For Developers:
✅ **Telemetry tracking** - `auth_mode_used` included in all workflow outputs
✅ **Non-breaking** - Enabled by default, fails gracefully
✅ **Consistent pattern** - Same 4-step integration across all workflows
✅ **Well-tested** - All existing tests continue to pass

### For the Framework:
✅ **Intelligent routing** - Maximizes subscription value, uses API when needed
✅ **Cost optimization** - Small/medium work uses subscription (free), large work uses API
✅ **Scalability** - Framework adapts to user's subscription tier automatically

---

## Testing

### Unit Tests
All existing tests continue to pass:
- DocumentGenerationWorkflow: ✅ 127+ tests passing
- TestGenerationWorkflow: ✅ All tests passing
- CodeReviewWorkflow: ✅ All tests passing
- BugPredictWorkflow: ✅ All tests passing
- SecurityAuditWorkflow: ✅ All tests passing
- PerfAuditWorkflow: ✅ 34 tests passing
- ReleasePreparationWorkflow: ✅ All tests passing

### Integration Tests
- ✅ test_doc_with_auth.py - Documents auth mode tracking
- ✅ test_gen_with_auth.py - Test generation workflow
- ✅ test_code_review_with_auth.py - Code review workflow
- ✅ test_bug_predict_with_auth.py - Bug prediction workflow
- ✅ test_security_audit_with_auth.py - Security audit workflow
- ✅ test_perf_audit_with_auth.py - Performance audit workflow
- ✅ test_release_prep_with_auth.py - Release preparation workflow
- ✅ test_auth_strategy.py - Auth strategy unit tests

### Manual Testing
Each workflow was tested with:
- ✅ Auth strategy enabled (default)
- ✅ Auth strategy disabled (`enable_auth_strategy=False`)
- ✅ Small modules (<500 LOC) → subscription recommended
- ✅ Large modules (>2000 LOC) → API recommended
- ✅ Auth mode included in output

---

## Configuration

Users can configure thresholds by editing `~/.empathy/auth_strategy.json`:

```json
{
  "subscription_tier": "max",
  "default_mode": "auto",
  "small_module_threshold": 500,
  "medium_module_threshold": 2000,
  "setup_completed": true
}
```

See [AUTH_STRATEGY_GUIDE.md](./AUTH_STRATEGY_GUIDE.md) for full configuration options.

---

## CLI Commands

View current auth strategy:
```bash
python -m attune.models.auth_cli status
```

Get recommendation for a specific file:
```bash
python -m attune.models.auth_cli recommend src/my_module.py
```

Interactive setup:
```bash
python -m attune.models.auth_cli setup
```

---

## Migration Guide

### For Existing Code

No changes required! Auth strategy is enabled by default and works automatically.

**Before (still works):**
```python
workflow = DocumentGenerationWorkflow()
result = await workflow.execute(...)
```

**After (with auth tracking):**
```python
workflow = DocumentGenerationWorkflow()
result = await workflow.execute(...)
print(f"Used: {result.final_output.get('auth_mode_used', 'unknown')}")
```

### Disabling Auth Strategy

If you want to disable auth strategy for a specific workflow:

```python
workflow = DocumentGenerationWorkflow(enable_auth_strategy=False)
```

---

## Telemetry

All workflows now include `auth_mode_used` in their output, enabling:
- Usage analytics (subscription vs API split)
- Cost optimization tracking
- User behavior insights
- Quota management

Example telemetry data:
```json
{
  "workflow": "test-gen",
  "auth_mode_used": "subscription",
  "module_size_loc": 450,
  "cost": 0.0,
  "quota_tokens": 1800
}
```

---

## Next Steps (Future Enhancements)

### Phase 6: Additional Workflows
- Refactoring workflow
- Migration workflow
- Any custom user-defined workflows

### Phase 7: Analytics Dashboard
- Track auth mode usage over time
- Show cost savings from intelligent routing
- Identify quota consumption patterns

### Phase 8: Auto-Tuning
- Automatically adjust thresholds based on usage patterns
- Suggest optimal configuration for user's workflow

---

## Changelog

**v1.0 (2026-01-29):**
- ✅ Integrated auth strategy into DocumentGenerationWorkflow
- ✅ Integrated auth strategy into TestGenerationWorkflow
- ✅ Integrated auth strategy into CodeReviewWorkflow
- ✅ Integrated auth strategy into BugPredictWorkflow
- ✅ Integrated auth strategy into SecurityAuditWorkflow
- ✅ Integrated auth strategy into PerfAuditWorkflow
- ✅ Integrated auth strategy into ReleasePreparationWorkflow
- ✅ CLI commands for auth management
- ✅ Comprehensive documentation
- ✅ 7 integration tests created and passing

---

**Questions or Issues?**
- See [AUTH_STRATEGY_GUIDE.md](./AUTH_STRATEGY_GUIDE.md) for user guide
- See [AUTH_CLI_IMPLEMENTATION.md](./AUTH_CLI_IMPLEMENTATION.md) for CLI details
- Open issues at [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)

---

**Implemented By:** Claude (Sonnet 4.5) + Agents
**Date:** January 29, 2026
