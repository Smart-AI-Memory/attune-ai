# Top 10 Files Refactoring Plan

**Goal:** Refactor largest files for better maintainability and test coverage
**Status:** 2/10 Complete
**Created:** 2026-01-30

## Completed Refactorings

### ✅ 1. long_term.py (P0) - DONE
- **Before:** 1,498 lines
- **After:** 921 lines (38% reduction)
- **Approach:** Extracted 4 independent modules
  - long_term_types.py (99 lines) - Pure types/enums
  - encryption.py (159 lines) - AES-256-GCM
  - storage_backend.py (167 lines) - File storage
  - simple_storage.py (302 lines) - Simplified interface
- **Tests Generated:** 161 tests for extracted modules
- **Status:** ✅ Complete, all tests passing

### ✅ 2. unified.py (P0) - DONE
- **Before:** 1,281 lines
- **After:** 197 lines (85% reduction)
- **Approach:** Mixin composition pattern (7 mixins)
  - capabilities_mixin.py (206 lines)
  - lifecycle_mixin.py (51 lines)
  - short_term_mixin.py (195 lines)
  - long_term_mixin.py (353 lines)
  - handoff_mixin.py (211 lines)
  - promotion_mixin.py (114 lines)
  - backend_init_mixin.py (268 lines)
- **Status:** ✅ Complete, basic functionality verified

## Planned Refactorings

### 3. short_term.py (2,143 lines) - HIGH PRIORITY
**Sections:**
- Core Redis operations (386 lines)
- Working Memory (120 lines)
- Pattern Staging (148 lines)
- Conflict Management (129 lines)
- Session Management (99 lines)
- Pub/Sub (122 lines)
- Streams (180 lines)
- Timeline (148 lines)
- Queues (141 lines)
- Batch Operations (138 lines)
- Advanced/Atomic (179 lines)

**Proposed Extraction:**
```
short_term/
├── core.py              - Main class, basic operations (~600 lines)
├── pubsub.py            - Pub/Sub functionality (122 lines)
├── streams.py           - Streams, Timeline, Queues (469 lines)
├── patterns.py          - Pattern staging (148 lines)
├── conflicts.py         - Conflict management (129 lines)
├── sessions.py          - Session management (99 lines)
└── batch.py             - Batch operations (138 lines)
```
**Expected:** 2,143 → 600 lines (72% reduction)

### 4. core.py (1,511 lines) - HIGH PRIORITY
**Structure:** Single large module with framework core logic
**Proposed Extraction:**
- Identify 3-4 main functional areas
- Extract into core/submodules
- Target: <500 lines per module

**Expected:** 1,511 → 400 lines (74% reduction)

### 5. telemetry/cli.py (1,936 lines) - MEDIUM PRIORITY
**Structure:** CLI commands and telemetry operations
**Proposed Extraction:**
```
telemetry/
├── cli_core.py          - Main CLI setup (~300 lines)
├── cli_commands.py      - Command implementations (~800 lines)
├── cli_formatters.py    - Output formatting (~400 lines)
└── cli_analysis.py      - Analytics/reports (~400 lines)
```
**Expected:** 1,936 → 300 lines (85% reduction)

### 6. workflows/test_gen.py (1,917 lines) - MEDIUM PRIORITY
**Structure:** Test generation workflow
**Proposed Extraction:**
```
workflows/test_gen/
├── workflow.py          - Main workflow class (~300 lines)
├── analyzers.py         - Code analysis (~500 lines)
├── generators.py        - Test generation (~600 lines)
└── validators.py        - Validation logic (~500 lines)
```
**Expected:** 1,917 → 300 lines (84% reduction)

### 7. cli_meta_workflows.py (1,809 lines) - MEDIUM PRIORITY
**Structure:** 15+ independent CLI command functions
**Proposed Extraction:**
```
meta_workflows/cli/
├── __init__.py          - CLI setup (~100 lines)
├── template_commands.py - Template operations (~400 lines)
├── workflow_commands.py - Workflow execution (~500 lines)
├── memory_commands.py   - Memory operations (~400 lines)
└── admin_commands.py    - Admin/analytics (~400 lines)
```
**Expected:** 1,809 → 100 lines (94% reduction)

### 8. models/telemetry.py (1,660 lines) - MEDIUM PRIORITY
**Structure:** Multiple model classes and utilities
**Proposed Extraction:**
- Extract model groups into separate files
- Group by feature (cost, metrics, reports)
**Expected:** 1,660 → 400 lines (76% reduction)

### 9. workflows/document_gen.py (1,605 lines) - LOW PRIORITY
**Structure:** Single large DocumentGenerationWorkflow class
**Proposed Extraction:**
- Extract phases into separate modules
- Similar pattern to test_gen
**Expected:** 1,605 → 300 lines (81% reduction)

### 10. memory/control_panel.py (1,420 lines) - LOW PRIORITY
**Structure:** 6 classes (already well-organized)
**Proposed Extraction:**
```
memory/control_panel/
├── __init__.py          - Main exports
├── auth.py              - RateLimiter, APIKeyAuth (129 lines)
├── stats.py             - MemoryStats (29 lines)
├── panel.py             - MemoryControlPanel (487 lines)
├── api.py               - MemoryAPIHandler (593 lines)
└── config.py            - ControlPanelConfig (10 lines)
```
**Expected:** 1,420 → ~200 lines (86% reduction)

## Summary

**Completed (2 files):**
- Total reduced: 2,779 → 1,118 lines (60% reduction)
- Tests generated: 161 new tests

**Planned (8 files):**
- Current total: 14,001 lines
- Target total: ~2,600 lines (81% reduction)
- Expected new tests: ~800 tests

**Overall Impact:**
- 16,780 lines → 3,718 lines (78% reduction)
- ~960 new tests generated
- All files <500 lines (enables automated test generation)

## Implementation Order

### Phase 1 (Complete)
1. ✅ long_term.py - Extracted types, encryption, storage
2. ✅ unified.py - Mixin composition

### Phase 2 (Immediate)
3. short_term.py - Extract optional features
4. core.py - Extract functional areas

### Phase 3 (Medium-term)
5. telemetry/cli.py - Split CLI commands
6. test_gen.py - Extract workflow phases
7. cli_meta_workflows.py - Group commands

### Phase 4 (Long-term)
8. telemetry.py - Group models
9. document_gen.py - Extract phases
10. control_panel.py - Separate classes

## Testing Strategy

**Current Approach:**
- Generate tests for completed refactorings immediately
- For pending files, generate tests as-is (all <2,500 lines, testable with 20k max_tokens)
- Re-generate after refactoring for better coverage

**Test Generation Status:**
- ✅ long_term extracted modules: 161 tests
- ✅ P0/P1 modules: 290 tests (base.py, execution_strategies.py, etc.)
- ⏳ Remaining 8 files: Generate immediately as-is

## Notes

- All refactorings use composition/extraction patterns
- Public APIs remain unchanged (backward compatibility)
- Mixins used for shared behavior
- Module extraction for independent features
- File size target: <500 lines per file
