# Refactoring Plan: Remaining 6 Top-10 Files

**Created:** January 30, 2026
**Status:** Planning Phase
**Goal:** Refactor remaining 6 files from top-10 list to enable comprehensive test coverage

---

## Executive Summary

This document outlines refactoring strategies for the 6 remaining files in the top-10 largest files list. Combined, these files contain **9,878 lines** of code that need to be broken down into testable modules (<500 lines each).

**Target Files:**
1. telemetry/cli.py (1,936 lines) - CLI command implementations
2. workflows/test_gen.py (1,917 lines) - Test generation workflow
3. meta_workflows/cli_meta_workflows.py (1,809 lines) - Meta-workflow CLI
4. models/telemetry.py (1,660 lines) - Telemetry data models
5. workflows/document_gen.py (1,605 lines) - Documentation generation
6. core.py (1,511 lines) - Core framework functionality

**Combined Impact:**
- Current: 9,878 total lines across 6 files
- Target: ~60+ focused modules (<500 lines each)
- Expected reduction: 70-85% in core files
- Test coverage gain: 500+ new behavioral tests

---

## File 1: telemetry/cli.py (1,936 lines)

### Current Structure

**Function Analysis:**
```
cmd_file_test_dashboard      426 lines (22%)
cmd_telemetry_dashboard      264 lines (14%)
cmd_file_test_status         184 lines (9%)
cmd_telemetry_cache_stats    127 lines (7%)
cmd_telemetry_compare        120 lines (6%)
cmd_sonnet_opus_analysis     116 lines (6%)
cmd_telemetry_show           108 lines (6%)
cmd_telemetry_export         102 lines (5%)
[+ 7 more smaller commands]
```

**Key Issues:**
- Massive HTML templates embedded in dashboard functions (690 lines total)
- 15 command functions with no logical grouping
- Duplicate _validate_file_path utility (exists in config.py)

### Refactoring Strategy: **Command Extraction Pattern**

**New Modules:**

1. **Remove duplicate validation**
   - Delete _validate_file_path (lines 30-69)
   - Import from attune.config instead

2. **telemetry/commands/core_commands.py** (~250 lines)
   - cmd_telemetry_show
   - cmd_telemetry_savings
   - cmd_telemetry_reset
   - Dependencies: UsageTracker, rich (optional)

3. **telemetry/commands/export_commands.py** (~150 lines)
   - cmd_telemetry_export
   - Export to CSV/JSON functionality
   - Dependencies: csv, json, Path validation

4. **telemetry/commands/cache_commands.py** (~150 lines)
   - cmd_telemetry_cache_stats
   - Cache hit/miss analysis
   - Dependencies: UsageTracker, rich

5. **telemetry/commands/compare_commands.py** (~130 lines)
   - cmd_telemetry_compare
   - Comparison functionality between time periods
   - Dependencies: UsageTracker, rich, datetime

6. **telemetry/commands/analysis_commands.py** (~300 lines)
   - cmd_sonnet_opus_analysis
   - cmd_agent_performance
   - Dependencies: TelemetryAnalytics, rich

7. **telemetry/commands/status_commands.py** (~400 lines)
   - cmd_tier1_status
   - cmd_task_routing_report
   - cmd_test_status
   - Dependencies: TelemetryAnalytics, rich

8. **telemetry/commands/dashboard_commands.py** (~900 lines)
   - cmd_telemetry_dashboard (HTML template)
   - cmd_file_test_dashboard (HTML template)
   - cmd_file_test_status
   - Dependencies: tempfile, webbrowser, Counter

9. **telemetry/cli.py** (updated, ~50 lines)
   - Import all commands from submodules
   - Command registry/routing
   - Backward compatibility via re-exports

### Expected Outcome

**Before:**
```
cli.py (1,936 lines) - monolithic
```

**After:**
```
cli.py (50 lines) - router
commands/
├── core_commands.py (250 lines)
├── export_commands.py (150 lines)
├── cache_commands.py (150 lines)
├── compare_commands.py (130 lines)
├── analysis_commands.py (300 lines)
├── status_commands.py (400 lines)
└── dashboard_commands.py (900 lines)
```

**Impact:**
- 97% line reduction in main file
- Each module <500 lines (testable)
- Clear separation by functionality
- Reusable command components

---

## File 2: workflows/test_gen.py (1,917 lines)

### Current Structure

**Complexity:**
- Single monolithic test generation workflow
- AST parsing and analysis
- Template rendering
- Multiple test patterns
- Failed automated test generation (too complex)

### Refactoring Strategy: **Workflow Component Extraction**

**New Modules:**

1. **workflows/test_gen/ast_analyzer.py** (~300 lines)
   - AST parsing and function extraction
   - Complexity analysis
   - Dependency detection

2. **workflows/test_gen/test_templates.py** (~400 lines)
   - Template definitions for different test types
   - Parametrized test generation
   - Fixture templates

3. **workflows/test_gen/test_patterns.py** (~300 lines)
   - Pattern matching for test types
   - Edge case detection
   - Test case generation logic

4. **workflows/test_gen/code_generator.py** (~250 lines)
   - Code generation from templates
   - Import management
   - Formatting and validation

5. **workflows/test_gen/validation.py** (~200 lines)
   - Syntax validation
   - pytest collection validation
   - AST verification

6. **workflows/test_gen/workflow.py** (~400 lines)
   - Main TestGenerationWorkflow class
   - Orchestrates all components
   - Tier routing logic

7. **workflows/test_gen/__init__.py** (~50 lines)
   - Backward compatible imports
   - Public API exports

### Expected Outcome

**Before:**
```
test_gen.py (1,917 lines) - monolithic workflow
```

**After:**
```
test_gen/
├── __init__.py (50 lines)
├── workflow.py (400 lines) - orchestration
├── ast_analyzer.py (300 lines)
├── test_templates.py (400 lines)
├── test_patterns.py (300 lines)
├── code_generator.py (250 lines)
└── validation.py (200 lines)
```

**Impact:**
- 79% reduction in main workflow file
- Testable components in isolation
- Easier to extend with new patterns
- Better error handling

---

## File 3: meta_workflows/cli_meta_workflows.py (1,809 lines)

### Current Structure

**Complexity:**
- CLI interface for meta-workflows
- Multiple command handlers
- Workflow orchestration
- Similar structure to telemetry/cli.py

### Refactoring Strategy: **Command Extraction (Similar to File 1)**

**New Modules:**

1. **meta_workflows/commands/workflow_commands.py** (~300 lines)
   - Core workflow execution commands
   - Workflow listing and status

2. **meta_workflows/commands/orchestration_commands.py** (~350 lines)
   - Multi-agent orchestration commands
   - Coordination pattern commands

3. **meta_workflows/commands/analysis_commands.py** (~250 lines)
   - Workflow analysis and reporting
   - Performance metrics

4. **meta_workflows/commands/config_commands.py** (~200 lines)
   - Configuration management
   - Template management

5. **meta_workflows/commands/interactive_commands.py** (~400 lines)
   - Interactive workflow creation
   - Socratic questioning interface

6. **meta_workflows/cli_meta_workflows.py** (updated, ~200 lines)
   - Command routing
   - Imports from submodules
   - Backward compatibility

### Expected Outcome

**Before:**
```
cli_meta_workflows.py (1,809 lines)
```

**After:**
```
cli_meta_workflows.py (200 lines)
commands/
├── workflow_commands.py (300 lines)
├── orchestration_commands.py (350 lines)
├── analysis_commands.py (250 lines)
├── config_commands.py (200 lines)
└── interactive_commands.py (400 lines)
```

**Impact:**
- 89% reduction in main CLI file
- Modular command structure
- Easier to add new commands
- Better testability

---

## File 4: models/telemetry.py (1,660 lines)

### Current Structure

**Complexity:**
- Data models for telemetry
- Analytics classes
- Storage interfaces
- Statistics calculations

### Refactoring Strategy: **Model Separation Pattern**

**New Modules:**

1. **models/telemetry/data_models.py** (~300 lines)
   - Core dataclasses (TelemetryEntry, etc.)
   - Validation logic
   - Serialization methods

2. **models/telemetry/analytics.py** (~400 lines)
   - TelemetryAnalytics class
   - Statistical calculations
   - Aggregation logic

3. **models/telemetry/storage.py** (~250 lines)
   - Storage interface
   - Persistence logic
   - Query methods

4. **models/telemetry/tier1_analytics.py** (~300 lines)
   - Tier 1 specific analytics
   - Task routing analysis
   - Test execution metrics

5. **models/telemetry/reporting.py** (~250 lines)
   - Report generation
   - Data formatting
   - Export utilities

6. **models/telemetry/__init__.py** (~150 lines)
   - Backward compatible imports
   - Public API
   - Factory functions

### Expected Outcome

**Before:**
```
telemetry.py (1,660 lines)
```

**After:**
```
telemetry/
├── __init__.py (150 lines)
├── data_models.py (300 lines)
├── analytics.py (400 lines)
├── storage.py (250 lines)
├── tier1_analytics.py (300 lines)
└── reporting.py (250 lines)
```

**Impact:**
- 91% reduction in main file
- Clear separation of concerns
- Independent model testing
- Easier to extend

---

## File 5: workflows/document_gen.py (1,605 lines)

### Current Structure

**Complexity:**
- Documentation generation workflow
- Multiple documentation types
- Template rendering
- File I/O operations

### Refactoring Strategy: **Generator Component Extraction**

**New Modules:**

1. **workflows/document_gen/code_analyzer.py** (~300 lines)
   - Code analysis for documentation
   - Docstring extraction
   - API discovery

2. **workflows/document_gen/doc_templates.py** (~350 lines)
   - Documentation templates
   - Markdown generation
   - Format utilities

3. **workflows/document_gen/api_docs.py** (~250 lines)
   - API documentation generation
   - Function/class documentation
   - Parameter documentation

4. **workflows/document_gen/tutorial_gen.py** (~250 lines)
   - Tutorial generation
   - Example extraction
   - Step-by-step guides

5. **workflows/document_gen/mkdocs_integration.py** (~200 lines)
   - MkDocs configuration
   - Navigation generation
   - Site structure

6. **workflows/document_gen/workflow.py** (~200 lines)
   - Main DocumentGenerationWorkflow
   - Orchestrates components
   - Tier routing

7. **workflows/document_gen/__init__.py** (~50 lines)
   - Backward compatible imports

### Expected Outcome

**Before:**
```
document_gen.py (1,605 lines)
```

**After:**
```
document_gen/
├── __init__.py (50 lines)
├── workflow.py (200 lines)
├── code_analyzer.py (300 lines)
├── doc_templates.py (350 lines)
├── api_docs.py (250 lines)
├── tutorial_gen.py (250 lines)
└── mkdocs_integration.py (200 lines)
```

**Impact:**
- 88% reduction in main workflow
- Reusable documentation components
- Easier to add new doc types
- Better separation of concerns

---

## File 6: core.py (1,511 lines)

### Current Structure

**Complexity:**
- Core framework functionality
- Already has 41 behavioral tests
- Mixed concerns
- Needs additional cleanup

### Refactoring Strategy: **Core Functionality Separation**

**Note:** This file already has test coverage, so refactoring is lower priority but still valuable.

**New Modules:**

1. **core/framework_init.py** (~250 lines)
   - Framework initialization
   - Configuration loading
   - Environment setup

2. **core/workflow_base.py** (~300 lines)
   - Base workflow classes
   - Common workflow patterns
   - Abstract interfaces

3. **core/tier_routing.py** (~200 lines)
   - Tier routing logic
   - Cost optimization
   - Model selection

4. **core/agent_coordination.py** (~250 lines)
   - Agent coordination patterns
   - Communication protocols
   - State management

5. **core/utilities.py** (~300 lines)
   - Utility functions
   - Helper methods
   - Common operations

6. **core.py** (updated, ~200 lines)
   - Main entry point
   - Imports from submodules
   - Backward compatibility

### Expected Outcome

**Before:**
```
core.py (1,511 lines)
```

**After:**
```
core.py (200 lines)
core/
├── framework_init.py (250 lines)
├── workflow_base.py (300 lines)
├── tier_routing.py (200 lines)
├── agent_coordination.py (250 lines)
└── utilities.py (300 lines)
```

**Impact:**
- 87% reduction in main file
- Clearer framework structure
- Better testability
- Easier to understand

---

## Implementation Strategy

### Phase 1: Quick Wins (High Impact, Low Risk)

**Priority 1 - Largest Files with Embedded Content:**
1. ✅ **telemetry/cli.py** - Extract dashboard functions first (690 lines, 36% reduction)
2. **models/telemetry.py** - Separate models from analytics (clean separation)

**Estimated Time:** 2-3 hours
**Expected Tests:** 100+ new behavioral tests

---

### Phase 2: Workflow Refactoring (Medium Impact, Medium Risk)

**Priority 2 - Complex Workflows:**
3. **workflows/test_gen.py** - Extract AST analysis and templates
4. **workflows/document_gen.py** - Extract documentation components

**Estimated Time:** 4-5 hours
**Expected Tests:** 150+ new behavioral tests

---

### Phase 3: CLI and Core Cleanup (Medium Impact, Low Risk)

**Priority 3 - CLI Interfaces:**
5. **meta_workflows/cli_meta_workflows.py** - Extract command handlers
6. **core.py** - Final cleanup and organization

**Estimated Time:** 3-4 hours
**Expected Tests:** 50+ new behavioral tests

---

## Validation Strategy

### After Each File Refactoring:

1. **Import Validation:**
   ```bash
   python -c "from attune.[module] import *; print('✅ Imports work')"
   ```

2. **Run Existing Tests:**
   ```bash
   pytest tests/unit/[module]/ -v
   pytest tests/behavioral/generated/ -k [module] -v
   ```

3. **Generate New Tests:**
   ```bash
   python -c "from attune.workflows.autonomous_test_gen import AutonomousTestGenerator; \
       gen = AutonomousTestGenerator('phase', 1, [{'file': 'path/to/new/module.py'}]); \
       gen.generate_all()"
   ```

4. **Line Count Verification:**
   ```bash
   wc -l src/attune/[module]/**/*.py | sort -n
   ```

---

## Expected Final Results

### Overall Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Files Refactored** | 6 monolithic | ~60 focused | +900% modules |
| **Total Lines (main)** | 9,878 | ~900 | -91% |
| **Largest File** | 1,936 lines | <500 lines | -75% |
| **Avg File Size** | 1,646 lines | <250 lines | -85% |
| **New Tests** | 41 (core only) | 500+ | +1,100% |

### Quality Improvements

**Modularity:**
- Every module <500 lines (testable by automated generator)
- Clear separation of concerns
- Focused responsibilities

**Testability:**
- 500+ new behavioral tests
- Independent component testing
- Better coverage of edge cases

**Maintainability:**
- Clear module boundaries
- Easier to navigate codebase
- Simpler to onboard new contributors

**Performance:**
- No performance regressions (same behavior)
- Potential for better caching (smaller modules)
- Easier profiling and optimization

---

## Rollback Strategy

### If Refactoring Fails:

```bash
# Restore original file
git restore src/attune/[module]/[file].py

# Remove extracted modules
rm -rf src/attune/[module]/[extracted_dir]/

# Re-run tests to verify
pytest tests/unit/[module]/ -v
```

### Safety Measures:

1. **One file at a time** - Complete and validate each before moving to next
2. **Frequent commits** - Commit after each successful extraction
3. **Test after every change** - Never commit without passing tests
4. **Backup important files** - Keep .backup copies during refactoring

---

## Success Criteria

### Functional Requirements:
- [ ] All existing tests pass without modification
- [ ] All imports work from original locations
- [ ] No behavior changes in any functionality
- [ ] All CLI commands still work identically

### Technical Requirements:
- [ ] All files <500 lines (testable)
- [ ] Automated test generator succeeds on all new modules
- [ ] Test coverage maintained or increased
- [ ] No performance degradation

### Quality Requirements:
- [ ] All modules have docstrings
- [ ] Clear module organization
- [ ] No linting errors
- [ ] Consistent with established patterns

---

## Next Steps

### Immediate Actions:

1. **Extract telemetry dashboard functions** (quick win)
   - Create telemetry/commands/dashboard_commands.py
   - Update telemetry/cli.py imports
   - Run tests and commit

2. **Refactor models/telemetry.py** (clean separation)
   - Extract data models
   - Extract analytics
   - Run tests and commit

3. **Continue with remaining files** following the plan

### Long-term Goals:

- Complete all 6 files within 2-3 sessions
- Generate 500+ new behavioral tests
- Achieve 90%+ test coverage across all modules
- Document patterns for future refactoring

---

**Document Version:** 1.0
**Created:** January 30, 2026
**Author:** Autonomous Refactoring Agent
**Status:** 📋 READY FOR IMPLEMENTATION
