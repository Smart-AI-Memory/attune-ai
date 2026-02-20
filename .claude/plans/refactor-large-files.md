# Refactor Large Files

**Created:** 2026-02-20
**Source:** /brainstorm session
**Status:** In Progress

## Problem

76 files in src/attune/ exceed 500 lines. Phase 1
targeted the ~39 files over 600 lines. Phase 2 covers
the remaining 44 files in the 500-600 line range.

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

## Phase 1 Results

**Status:** Complete

- **39 files** analyzed (600+ lines)
- **15 files** split into focused modules
- **2 files** skipped (deprecated)
- **22 files** skipped (already cohesive or marginal gain)
- **15 new modules** created
- **All imports preserved** via re-exports

---

## Phase 2: Files 500-600 Lines (sorted by size)

| # | Lines | File | Status |
|---|-------|------|--------|
| 1 | 596 | src/attune/workflows/secure_release.py | skip (cohesive workflow) |
| 2 | 591 | src/attune/workflows/bug_predict.py | skip (already split into sub-modules) |
| 3 | 590 | src/attune/workflows/test_maintenance_cli.py | skip (cohesive CLI module) |
| 4 | 589 | src/attune/models/telemetry/analytics.py | skip (single cohesive class) |
| 5 | 588 | src/attune/config.py | skip (cohesive config; path validation tightly coupled) |
| 6 | 583 | src/attune/memory/summary_index.py | skip (two tightly-coupled classes) |
| 7 | 582 | src/attune/telemetry/cli_core.py | skip (cohesive CLI commands) |
| 8 | 579 | src/attune/trust/circuit_breaker.py | skip (integrated trust system) |
| 9 | 577 | src/attune/models/telemetry/storage.py | skip (single cohesive class) |
| 10 | 577 | src/attune/levels.py | skip (integrated empathy levels) |
| 11 | 576 | src/attune/workflows/__init__.py | skip (re-export file) |
| 12 | 575 | src/attune/telemetry/feedback_loop.py | done |
| 13 | 570 | src/attune/memory/graph.py | skip (single cohesive class) |
| 14 | 569 | src/attune/meta_workflows/models.py | skip (pure data models, 13 callers) |
| 15 | 569 | src/attune/memory/redis_bootstrap.py | skip (cohesive bootstrap module) |
| 16 | 567 | src/attune/workflows/refactor_plan.py | skip (single workflow class) |
| 17 | 567 | src/attune/socratic/mcp_server.py | skip (single cohesive server class) |
| 18 | 567 | src/attune/meta_workflows/builtin_templates.py | skip (data/constants only) |
| 19 | 565 | src/attune/learning/storage.py | skip (cohesive model + manager pair) |
| 20 | 564 | src/attune/persistence.py | done |
| 21 | 558 | src/attune/agent_factory/factory.py | skip (single factory class) |
| 22 | 556 | src/attune/telemetry/approval_gates.py | skip (borderline; data models small) |
| 23 | 551 | src/attune/socratic/explainer.py | skip (types already in explainer_types.py) |
| 24 | 551 | src/attune/dashboard/standalone_server.py | skip (single cohesive handler) |
| 25 | 550 | src/attune/wizards/base.py | done |
| 26 | 548 | src/attune/orchestration/tools/testing.py | done |
| 27 | 548 | src/attune/cli_commands/telemetry_commands.py | skip (cohesive CLI functions) |
| 28 | 542 | src/attune/pattern_library.py | skip (single cohesive class) |
| 29 | 541 | src/attune/workflows/history.py | skip (single cohesive class) |
| 30 | 533 | src/attune/socratic/blueprint.py | skip (well-organized blueprint types) |
| 31 | 531 | src/attune/workflows/tier_tracking.py | pending (dataclasses extractable) |
| 32 | 530 | src/attune/workflows/keyboard_shortcuts/workflow.py | skip (single cohesive workflow) |
| 33 | 528 | src/attune/orchestration/config_store.py | pending (duplicate _validate_file_path) |
| 34 | 527 | src/attune/trust_building.py | skip (single-purpose class) |
| 35 | 526 | src/attune/workflows/test_lifecycle.py | skip (cohesive lifecycle manager) |
| 36 | 520 | src/attune/workflows/progressive/reports.py | skip (pure utility functions) |
| 37 | 517 | src/attune/workflows/dependency_check.py | skip (already split into 6 sub-modules) |
| 38 | 516 | src/attune/learning/extractor.py | pending (extraction vs. categorization split) |
| 39 | 515 | src/attune/dashboard/app.py | pending (models + routes + manager mixed) |
| 40 | 509 | src/attune/workflows/progressive/test_gen.py | skip (single cohesive class) |
| 41 | 507 | src/attune/socratic/llm_analyzer.py | pending (data classes + analyzer + mock) |
| 42 | 504 | src/attune/project_index/models.py | skip (pure data models) |
| 43 | 504 | src/attune/monitoring/engine.py | skip (single cohesive class) |
| 44 | 501 | src/attune/telemetry/commands/dashboard_file_tests.py | skip (single command function) |

## Phase 2 Summary

- **44 files** assessed (500-600 lines)
- **11 files** identified for refactoring (pending)
- **33 files** skipped (already cohesive or marginal gain)

### Refactoring Candidates (11 files)

| # | File | Split Strategy |
| --- | ------ | ---------------- |
| 1 | telemetry/feedback_loop.py | Extract data models (enum + 3 dataclasses) to feedback_models.py |
| 2 | meta_workflows/models.py | Split into form_models.py, agent_models.py, result_models.py |
| 3 | persistence.py | Split into pattern_persistence.py, state_manager.py, metrics_collector.py |
| 4 | socratic/explainer.py | Separate WorkflowExplainer from LLMExplanationGenerator |
| 5 | wizards/base.py | Extract enums + dataclasses to wizards/_types.py |
| 6 | orchestration/tools/testing.py | Split 3 analyzer classes into coverage.py, generators.py, validators.py |
| 7 | workflows/tier_tracking.py | Extract dataclasses to tier_models.py |
| 8 | orchestration/config_store.py | Remove duplicate _validate_file_path, import from attune.config |
| 9 | learning/extractor.py | Split PatternExtractor from PatternCategorizer |
| 10 | dashboard/app.py | Extract models to dashboard/models.py, ConnectionManager to dashboard/connections.py |
| 11 | socratic/llm_analyzer.py | Extract result types to llm_types.py, MockLLMExecutor to testing |
