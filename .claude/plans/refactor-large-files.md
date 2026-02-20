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
| 2 | 753 | src/attune/orchestration/agent_templates.py | pending |
| 3 | 752 | src/attune/workflows/document_gen/workflow.py | pending |
| 4 | 741 | src/attune/socratic/embeddings.py | pending |
| 5 | 738 | src/attune/meta_workflows/pattern_learner.py | pending |
| 6 | 734 | src/attune/workflows/code_review_pipeline.py | pending |
| 7 | 732 | src/attune/socratic/generator.py | pending |
| 8 | 730 | src/attune/workflows/base.py | pending |
| 9 | 730 | src/attune/socratic/success.py | pending |
| 10 | 723 | src/attune/workflows/progressive/orchestrator.py | pending |
| 11 | 718 | src/attune/workflows/refactor_plan.py | pending |
| 12 | 712 | src/attune/telemetry/commands/dashboard_commands.py | pending |
| 13 | 712 | src/attune/memory/short_term/facade.py | pending |
| 14 | 703 | src/attune/socratic/cli.py | pending |
| 15 | 702 | src/attune/socratic/mcp_server.py | pending |
| 16 | 696 | src/attune/orchestration/pattern_learner.py | pending |
| 17 | 694 | src/attune/workflows/progressive/workflow.py | pending |
| 18 | 693 | src/attune/workflows/documentation_orchestrator.py | pending |
| 19 | 682 | src/attune/socratic/explainer.py | pending |
| 20 | 680 | src/attune/workflows/config.py | pending |
| 21 | 678 | src/attune/memory/security/secrets_detector.py | pending |
| 22 | 673 | src/attune/workflows/test_gen/workflow.py | pending |
| 23 | 671 | src/attune/socratic/storage.py | pending |
| 24 | 667 | src/attune/project_index/index.py | pending |
| 25 | 657 | src/attune/workflows/code_review_analysis_mixin.py | pending |
| 26 | 655 | src/attune/models/cli.py | pending |
| 27 | 654 | src/attune/workflows/seo_optimization.py | pending |
| 28 | 649 | src/attune/workflows/autonomous_test_gen.py | pending |
| 29 | 640 | src/attune/memory/security/pii_scrubber.py | pending |
| 30 | 637 | src/attune/socratic/llm_analyzer.py | pending |
| 31 | 630 | src/attune/cost_tracker.py | pending |
| 32 | 629 | src/attune/socratic/forms.py | pending |
| 33 | 627 | src/attune/workflows/test_maintenance.py | pending |
| 34 | 623 | src/attune/workflows/orchestrated_release_prep.py | pending |
| 35 | 622 | src/attune/workflows/test_runner.py | pending |
| 36 | 619 | src/attune/socratic/collaboration.py | pending |
| 37 | 610 | src/attune/agent_factory/crews/refactoring/crew.py | pending |
| 38 | 605 | src/attune/telemetry/usage_tracker.py | pending |
| 39 | 602 | src/attune/orchestration/execution_strategies.py | pending |

## Splitting Principles

- Group by natural responsibility (functions/classes that
  work together stay together)
- Preserve public API via `__init__.py` re-exports
- Keep import paths working for external consumers
- Target: each new module under ~300 lines where possible

## Resumability

If interrupted, check this file for the last "done" status
in the table above, and continue from the next pending
file. Each file also gets an individual plan saved at:

```
.claude/plans/splits/{filename}.md
```

## Next Steps

- [ ] Begin Phase 1+2 for file #1
- [ ] Update status in this table as each file completes
