---
description: Known Issues & Technical Debt: ## VSCode Extension ### Category Mismatch (Fixed ✓) **Status:** ✓ RESOLVED **Was:** The VSCode extension expected "quick" workflo
---

# Known Issues & Technical Debt

## VSCode Extension

### Category Mismatch (Fixed ✓)

**Status:** ✓ RESOLVED

**Was:** The VSCode extension expected "quick" workflows that didn't exist in Python CLI.

**Fix Applied:** Remapped categories to actual workflows returned by Python CLI:
- **Quick** (3): `health-check`, `bug-predict`, `code-review`
- **Tool** (5): `doc-gen`, `test-gen`, `refactor-plan`, `manage-docs`, `keyboard-shortcuts`
- **Workflow** (8): `security-audit`, `perf-audit`, `dependency-check`, `release-prep`, `secure-release`, `pro-review`, `pr-review`, `doc-orchestrator`
- **View** (0): None currently (placeholder for future)

**Result:**
- `empathy.quickPick.quick` now shows 3 workflows ✓
- `empathy.quickPick.tool` now shows 5 workflows ✓
- `empathy.quickPick.workflow` now shows 8 workflows ✓
- `empathy.quickPick.all` shows all 16 workflows ✓

---

## Test Suite

### Floating Point Precision (Fixed ✓)
- **Issue:** Tests failed due to `0.1 + 0.2 == 0.30000000000000004`
- **Fix:** Use `pytest.approx()` for all floating point comparisons
- **Status:** ✓ Fixed

---

## Created: 2025-01-03
## Last Updated: 2025-01-03 (Phase 3 Complete)
