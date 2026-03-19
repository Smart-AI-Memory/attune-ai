# v2.4.0 Plan: Security & CI Stability

**Created:** 2026-02-04
**Goal:** Complete deferred config path migration + fix CI failures

---

## Phase 1: Path Validation Migration (Security)

### HIGH Priority (User-controlled paths) - 6 files

| File | Line | Issue |
|------|------|-------|
| [workflow_commands.py:709](src/attune/workflow_commands.py#L709) | `open(debugging_file, "w")` | User parameter |
| [test_maintenance_crew.py:294](src/attune/workflows/test_maintenance_crew.py#L294) | `full_test_path.write_text()` | User path |
| [test_gen_parallel.py:260](src/attune/workflows/test_gen_parallel.py#L260) | `Path(task.output_path).write_text()` | User path |
| [test_gen_behavioral.py:481](src/attune/workflows/test_gen_behavioral.py#L481) | `test_path.write_text()` | User path |
| [autonomous_test_gen.py:310,842,1075](src/attune/workflows/autonomous_test_gen.py#L310) | Multiple `write_text()` | User paths |
| [test_generator/cli.py:152](src/attune/test_generator/cli.py#L152) | `open(json_file, "w")` | Workflow ID in filename |

### MEDIUM Priority (Instance variables) - 11 files

| File | Line | Issue |
|------|------|-------|
| [cli_router.py:195](src/attune/cli_router.py#L195) | `open(self.preferences_path, "w")` | Instance var |
| [vscode_bridge.py:111](src/attune/vscode_bridge.py#L111) | `open(output_path, "w")` | Depends on `get_empathy_dir()` |
| [cost_tracker.py:287](src/attune/cost_tracker.py#L287) | `open(self.costs_jsonl, "a")` | Append mode |
| [socratic/storage.py:142,210,277](src/attune/socratic/storage.py#L142) | `path.open("w")` | IDs in path |
| [socratic/embeddings.py:563](src/attune/socratic/embeddings.py#L563) | `self.storage_path.open("w")` | Instance var |
| [socratic/feedback.py:295,301](src/attune/socratic/feedback.py#L295) | `open("w")` | Parent not validated |
| [socratic/ab_testing.py:799](src/attune/socratic/ab_testing.py#L799) | `self.storage_path.open("w")` | Instance var |
| [attune_llm/code_health.py:1119](attune_llm/code_health.py#L1119) | `filepath.write_text()` | |
| [attune_llm/agent_factory/crews/refactoring.py:852](attune_llm/agent_factory/crews/refactoring.py#L852) | `open(profile_path, "w")` | |
| [attune_llm/context/compaction.py:284](attune_llm/context/compaction.py#L284) | `open(filepath, "w")` | |
| [attune_llm/pattern_resolver.py:156](attune_llm/pattern_resolver.py#L156) | `open(file_path, "w")` | |

### LOW Priority (Internal/hardcoded paths) - 5 files

| File | Line | Issue |
|------|------|-------|
| [cli_unified.py:104](src/attune/cli_unified.py#L104) | `TIER_CONFIG_PATH.write_text()` | Constant |
| [dependency_check.py:74](src/attune/workflows/dependency_check.py#L74) | `cache_path.write_text()` | Internal cache |
| [attune_llm/security/audit_logger.py:178](attune_llm/security/audit_logger.py#L178) | `open(self.log_path, "a")` | Audit log |
| [attune_llm/security/secure_memdocs.py:304](attune_llm/security/secure_memdocs.py#L304) | `open(pattern_file, "w")` | |
| [attune_llm/learning/storage.py:323](attune_llm/learning/storage.py#L323) | `open(patterns_file, "w")` | |

---

## Phase 2: Fix Pattern

For each file, apply this pattern:

```python
from attune.config import _validate_file_path

# Before writing:
validated_path = _validate_file_path(user_path)
with validated_path.open("w") as f:
    f.write(content)
```

---

## Phase 3: Add Security Tests

Create `tests/unit/test_path_validation_coverage.py`:

```python
"""Verify all file write operations use _validate_file_path()."""
import pytest
from pathlib import Path

# Test each HIGH priority file for path traversal protection
class TestWorkflowPathValidation:
    def test_workflow_commands_validates_debugging_file(self):
        """workflow_commands.py:709 should validate debugging_file."""
        pass  # Implementation

    def test_test_maintenance_crew_validates_paths(self):
        """test_maintenance_crew.py:294 should validate paths."""
        pass

    # ... one test per HIGH priority location
```

---

## Phase 4: CI Fixes

### Investigate Test Workflow Failures

```bash
gh run view 21690831551 --log-failed
```

**Known issues to check:**
1. Pre-commit hooks failing on formatting
2. Optional dependency tests on Ubuntu CI (no Redis/OTEL)
3. Import errors from environment differences

### Fix Strategy

1. Ensure all optional dependency tests use proper skip markers
2. Add Ubuntu-specific test configuration if needed
3. Fix any pre-commit hook issues

---

## Execution Order

1. **HIGH priority paths** (security risk) - 6 files
2. **Security tests** for HIGH priority
3. **CI investigation** - identify root cause
4. **MEDIUM priority paths** - 11 files
5. **LOW priority paths** - 5 files
6. **Final validation** - run full test suite
7. **Release v2.4.0**

---

## Success Criteria

- [ ] All 22 file write operations use `_validate_file_path()`
- [ ] Security tests pass for path traversal prevention
- [ ] CI Tests workflow passes
- [ ] CI Pre-commit Checks workflow passes
- [ ] 900+ tests passing locally
- [ ] No security scan warnings

---

## Estimated Scope

- **Files to modify:** 22
- **Tests to add:** ~10 security tests
- **CI fixes:** TBD after investigation
