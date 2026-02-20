# Refactor Large Files (600+ Lines)

**Created:** 2026-02-20
**Source:** /brainstorm session
**Status:** In Progress

## Problem

76 files in src/attune/ exceed 500 lines. This plan
targets the ~39 files over 600 lines for splitting into
focused modules based on natural groupings.

## Approach

For each file, two phases:

1. **Plan** (Opus): Analyze the file, identify natural
   groupings, write a split plan
2. **Execute** (Sonnet/Opus): Split the file, update
   imports, commit

Safety: one git commit per file, plans saved to disk
for resumability.

## Files to Refactor (sorted by size, descending)

| # | Lines | File | Status |
|---|-------|------|--------|
| 1 | 842 | src/attune/workflows/test_maintenance_crew.py | skipped (deprecated) |
| 2 | 753 | src/attune/orchestration/agent_templates.py | done |
| 3 | 752 | src/attune/workflows/document_gen/workflow.py | done |
| 4 | 741 | src/attune/socratic/embeddings.py | done |
| 5 | 738 | src/attune/meta_workflows/pattern_learner.py | done |
| 6 | 734 | src/attune/workflows/code_review_pipeline.py | skipped (deprecated v5.3.0) |
| 7 | 732 | src/attune/socratic/generator.py | done |
| 8 | 730 | src/attune/workflows/base.py | done |
| 9 | 730 | src/attune/socratic/success.py | done |
| 10 | 723 | src/attune/workflows/progressive/orchestrator.py | done |
| 11 | 718 | src/attune/workflows/refactor_plan.py | done |
| 12 | 712 | src/attune/telemetry/commands/dashboard_commands.py | done |
| 13 | 712 | src/attune/memory/short_term/facade.py | skipped (pure facade) |
| 14 | 703 | src/attune/socratic/cli.py | done |
| 15 | 702 | src/attune/socratic/mcp_server.py | done |
| 16 | 696 | src/attune/orchestration/pattern_learner.py | done |
| 17 | 694 | src/attune/workflows/progressive/workflow.py | skipped (cohesive class) |
| 18 | 693 | src/attune/workflows/documentation_orchestrator.py | skipped (already uses mixins) |
| 19 | 682 | src/attune/socratic/explainer.py | done |
| 20 | 680 | src/attune/workflows/config.py | skipped (cohesive config class) |
| 21 | 678 | src/attune/memory/security/secrets_detector.py | done |
| 22 | 673 | src/attune/workflows/test_gen/workflow.py | skipped (cohesive workflow) |
| 23 | 671 | src/attune/socratic/storage.py | done |
| 24 | 667 | src/attune/project_index/index.py | skipped (cohesive index class) |
| 25 | 657 | src/attune/workflows/code_review_analysis_mixin.py | done |
| 26 | 655 | src/attune/models/cli.py | skipped (marginal gain ~80 lines) |
| 27 | 654 | src/attune/workflows/seo_optimization.py | skipped (cohesive workflow) |
| 28 | 649 | src/attune/workflows/autonomous_test_gen.py | skipped (cohesive workflow) |
| 29 | 640 | src/attune/memory/security/pii_scrubber.py | skipped (cohesive class) |
| 30 | 637 | src/attune/socratic/llm_analyzer.py | done |
| 31 | 630 | src/attune/cost_tracker.py | skipped (marginal gain ~60 lines) |
| 32 | 629 | src/attune/socratic/forms.py | done |
| 33 | 627 | src/attune/workflows/test_maintenance.py | skipped (cohesive workflow class) |
| 34 | 623 | src/attune/workflows/orchestrated_release_prep.py | skipped (deprecated, removing in v6.0) |
| 35 | 622 | src/attune/workflows/test_runner.py | done |
| 36 | 619 | src/attune/socratic/collaboration.py | skipped (already split across 3 sibling modules) |
| 37 | 610 | src/attune/agent_factory/crews/refactoring/crew.py | skipped (uses composition with 4 siblings) |
| 38 | 605 | src/attune/telemetry/usage_tracker.py | skipped (single-responsibility singleton) |
| 39 | 602 | src/attune/orchestration/execution_strategies.py | done |

## Results Summary

**Status:** Complete

- **39 files** analyzed
- **15 files** split into focused modules
- **2 files** skipped (deprecated)
- **22 files** skipped (already cohesive or marginal gain)
- **15 new modules** created
- **All imports preserved** via re-exports
