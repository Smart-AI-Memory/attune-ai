# Refactoring: Dead Code Cleanup and Complexity Reduction

**Created:** 2026-02-22
**Source:** /plan refactor
**Route:** refactor
**Status:** pending

## Problem

The codebase (682 files, 178K lines) has accumulated 3
monolithic duplicate files from a reverted package
refactor, plus 3 functions over 200 lines with complex
nested control flow. These reduce maintainability and
obscure the clean package structure that already exists.

## Goals

- Remove 3,393 lines of dead duplicate code
- Reduce the 3 most complex functions to under 60 lines
  each by extracting focused helpers
- Maintain 100% test pass rate throughout

## End State

Zero monolithic crew files remaining. The 3 targeted
functions are each under 60 lines, with extracted
helpers that have clear single responsibilities. All
14,503 tests still pass.

## Scope

- **Files:** `src/attune/agent_factory/crews/`,
  `src/attune/workflows/`, `src/attune/models/`
- **Type:** refactor

## Approach

### Phase 1: Remove Dead Duplicates (Quick Wins)

Three files in `agent_factory/crews/` have both a
monolithic `.py` file AND a package directory. The
packages are the active versions (verified via grep:
zero imports target the monolithic files). All imports
go through `crews/__init__.py` which re-exports from
the packages.

| Remove | Keep | Lines |
|--------|------|-------|
| `crews/code_review.py` | `crews/code_review/` | 1,113 |
| `crews/health_check.py` | `crews/health_check/` | 1,262 |
| `crews/security_audit.py` | `crews/security_audit/` | 1,018 |

Evidence: `code_review.py` is a plain class (no
`CrewBase` inheritance), while `code_review/crew.py`
properly inherits `CrewBase`. Git history confirms
these are stale revert artifacts from commit
`428a02c4`.

Steps:
1. Run baseline test suite
2. Delete the 3 monolithic files
3. Run test suite — expect zero regressions
4. Verify imports:
   `python -c "from attune.agent_factory.crews import CodeReviewCrew, HealthCheckCrew, SecurityAuditCrew"`
5. Commit

### Phase 2: Split Complex Functions

**Target 1: `_execute_tier_fallback` (200 lines)**
File: `src/attune/workflows/execution_tier_fallback.py`

Most complex function — nested loops with 3 control
flow paths and duplicate heartbeat code. Extract:

- `_handle_stage_skip()` — skip logic
- `_handle_stage_success()` — success path with
  telemetry, cost tracking, heartbeat
- `_handle_validation_failure()` — validation path
- `_handle_execution_error()` — exception path
- `_update_heartbeat()` — deduplicate repeated code

Main function becomes ~40 lines of orchestration.
Commit separately.

**Target 2: `format_test_gen_report` (278 lines)**
File: `src/attune/workflows/test_gen/report_formatter.py`

Multiple independent report sections. Extract:

- `_parse_xml_review()` — XML parsing
- `_format_quality_section()` — quality display
- `_format_findings_section()` — findings display
- `_format_tests_section()` — tests display
- `_format_recommendations()` — next steps

Main function becomes ~30 lines of section assembly.
Commit separately.

**Target 3: `estimate_workflow_cost` (221 lines)**
File: `src/attune/models/token_estimator.py`

Multi-step calculation with file I/O. Extract:

- `_get_workflow_stages()` — stage config lookup
- `_estimate_input_tokens()` — token estimation
  with file reading
- `_calculate_stage_costs()` — per-stage loop
- `_determine_risk_level()` — risk classification

Main function becomes ~50 lines. Commit separately.

### Phase 3: Skip / Defer

| Item | Decision | Reason |
|------|----------|--------|
| `mcp/server.py` (1,022) | Skip | Single responsibility, well-organized |
| `_build_file_test_html` (297) | Skip | Template code, splitting hurts clarity |
| `_register_tools` (247) | Defer | Config data, not logic |
| `test_maintenance_crew.py` (843) | Skip | Deprecated, planned for removal |

## Verification

After each phase:

1. `uv run pytest -x -q` — all tests pass
2. `uv run ruff check src/` — no lint issues
3. Phase-specific tests:
   - Phase 1: `pytest tests/agent_factory/`
   - Phase 2a: `pytest -k "tier_fallback or execution"`
   - Phase 2b: `pytest -k "test_gen or report"`
   - Phase 2c: `pytest -k "token or cost"`

## Commit Strategy

1. `refactor: remove 3 stale monolithic crew files
   (3,393 lines)`
2. `refactor: split _execute_tier_fallback into
   focused methods`
3. `refactor: split format_test_gen_report into
   section formatters`
4. `refactor: split estimate_workflow_cost into
   focused helpers`

## Open Questions

- Should the deprecated `test_maintenance_crew.py`
  be removed now or kept through a deprecation
  period?
