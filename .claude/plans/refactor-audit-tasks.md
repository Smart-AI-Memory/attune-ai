# Refactoring Audit — Task Prompts

**Created:** 2026-02-20
**Source:** /brainstorm session
**Scope:** 48 files split into ~165 new modules across
19 commits

## Overview

Five parallel audit tasks covering functional correctness
and structural quality of the large-file refactoring
effort. Tasks 1-4 can run concurrently. Task 5 runs
after tests complete.

---

## Task 1: Agent Factory & Orchestration Audit

```xml
<task id="audit-1" name="agent-factory-orchestration">
  <objective>
    Audit all file splits in agent_factory/crews/ and
    orchestration/ for import integrity, re-export
    correctness, and structural coherence.
  </objective>

  <scope>
    <group name="agent_factory/crews">
      <split original="agent_factory/crews/code_review.py"
             type="converted-to-package">
        <new>code_review/__init__.py</new>
        <new>code_review/config.py</new>
        <new>code_review/crew.py</new>
        <new>code_review/models.py</new>
        <new>code_review/parser.py</new>
      </split>
      <split original="agent_factory/crews/health_check.py"
             type="converted-to-package">
        <new>health_check/__init__.py</new>
        <new>health_check/analyzers.py</new>
        <new>health_check/checkers.py</new>
        <new>health_check/config.py</new>
        <new>health_check/crew.py</new>
        <new>health_check/models.py</new>
      </split>
      <split original="agent_factory/crews/refactoring.py"
             type="converted-to-package">
        <new>refactoring/__init__.py</new>
        <new>refactoring/checkpoints.py</new>
        <new>refactoring/config.py</new>
        <new>refactoring/crew.py</new>
        <new>refactoring/types.py</new>
        <new>refactoring/user_profiles.py</new>
      </split>
      <split original="agent_factory/crews/security_audit.py"
             type="converted-to-package">
        <new>security_audit/__init__.py</new>
        <new>security_audit/config.py</new>
        <new>security_audit/crew.py</new>
        <new>security_audit/models.py</new>
        <new>security_audit/parsers.py</new>
        <new>security_audit/prompts.py</new>
      </split>
    </group>
    <group name="orchestration">
      <split original="orchestration/agent_templates.py"
             type="converted-to-package">
        <new>agent_templates/__init__.py</new>
        <new>agent_templates/builtin_templates.py</new>
        <new>agent_templates/models.py</new>
        <new>agent_templates/registry.py</new>
      </split>
      <split original="orchestration/pattern_learner.py"
             type="sibling-module">
        <new>orchestration/pattern_learner_models.py</new>
      </split>
      <split original="orchestration/execution_strategies.py"
             type="sub-package">
        <new>orchestration/_strategies/advanced_strategies.py</new>
      </split>
    </group>
  </scope>

  <checks>
    <check id="1.1" name="import-integrity">
      Grep the entire codebase for imports from the
      original module paths. Verify each resolves
      correctly via __init__.py re-exports.
      Command: grep -r "from attune.agent_factory.crews.code_review import"
      and similar for each split.
    </check>
    <check id="1.2" name="re-export-completeness">
      For each __init__.py in converted packages, verify
      every public symbol from the original file is
      re-exported. Compare __all__ or import list against
      the original file's public API.
    </check>
    <check id="1.3" name="no-dead-code">
      Check that no functions or classes were duplicated
      across the new modules. Look for identical function
      signatures in sibling files.
    </check>
    <check id="1.4" name="module-naming">
      Verify new module names are descriptive and follow
      project conventions (snake_case, matches content).
    </check>
    <check id="1.5" name="no-circular-imports">
      Check for circular import chains between the new
      sibling modules. Run:
      python -c "from attune.agent_factory.crews.code_review import *"
    </check>
  </checks>

  <validation>
    <pass-criteria>
      All imports resolve. No duplicate symbols.
      No circular imports. Names are clear.
    </pass-criteria>
    <output>
      Markdown table: file | check | status | notes
    </output>
  </validation>
</task>
```

---

## Task 2: Socratic Module Audit

```xml
<task id="audit-2" name="socratic-modules">
  <objective>
    Audit all file splits in src/attune/socratic/ for
    import integrity, re-export correctness, dead code,
    and structural coherence. This is the largest group
    (~15 original files split).
  </objective>

  <scope>
    <split original="socratic/embeddings.py"
           type="converted-to-package">
      <new>embeddings/__init__.py</new>
      <new>embeddings/matcher.py</new>
      <new>embeddings/models.py</new>
      <new>embeddings/providers.py</new>
      <new>embeddings/store.py</new>
    </split>
    <split original="socratic/ab_testing.py"
           type="converted-to-package">
      <new>ab_testing/__init__.py</new>
      <new>ab_testing/allocator.py</new>
      <new>ab_testing/manager.py</new>
      <new>ab_testing/models.py</new>
      <new>ab_testing/statistics.py</new>
      <new>ab_testing/workflow_tester.py</new>
    </split>
    <split original="socratic/generator.py"
           type="sibling-module">
      <new>socratic/generated_workflow.py</new>
      <new>socratic/generator_registry.py</new>
    </split>
    <split original="socratic/success.py"
           type="sibling-module">
      <new>socratic/success_models.py</new>
      <new>socratic/success_templates.py</new>
    </split>
    <split original="socratic/cli.py"
           type="sibling-module">
      <new>socratic/cli_console.py</new>
    </split>
    <split original="socratic/mcp_server.py"
           type="sibling-module">
      <new>socratic/mcp_tools.py</new>
    </split>
    <split original="socratic/explainer.py"
           type="sibling-module">
      <new>socratic/explainer_types.py</new>
    </split>
    <split original="socratic/llm_analyzer.py"
           type="sibling-module">
      <new>socratic/llm_analyzer_prompts.py</new>
    </split>
    <split original="socratic/forms.py"
           type="sibling-module">
      <new>socratic/form_builders.py</new>
    </split>
    <split original="socratic/storage.py"
           type="sibling-module">
      <new>socratic/sqlite_storage.py</new>
    </split>
    <split original="socratic/domain_templates.py"
           type="sibling-module">
      <new>socratic/agent_templates.py</new>
      <new>socratic/api_helpers.py</new>
      <new>socratic/assets.py</new>
      <new>socratic/domain_models.py</new>
      <new>socratic/domain_registry.py</new>
    </split>
    <split original="socratic/web_ui.py"
           type="sibling-module">
      <new>socratic/html_renderer.py</new>
      <new>socratic/react_schemas.py</new>
      <new>socratic/workflow_templates.py</new>
    </split>
    <split original="socratic/visual_editor.py"
           type="sibling-module">
      <new>socratic/ascii_visualizer.py</new>
      <new>socratic/editor_models.py</new>
      <new>socratic/react_editor.py</new>
      <new>socratic/workflow_visualizer.py</new>
    </split>
    <split original="socratic/engine.py"
           type="sibling-module">
      <new>socratic/domain.py</new>
      <new>socratic/questions.py</new>
    </split>
    <split original="socratic/feedback.py"
           type="sibling-module">
      <new>socratic/adaptive_generator.py</new>
      <new>socratic/feedback_collector.py</new>
      <new>socratic/feedback_models.py</new>
    </split>
  </scope>

  <checks>
    <check id="2.1" name="import-integrity">
      For each split, grep codebase for imports from the
      original module. Verify they resolve. Pay special
      attention to embeddings/ and ab_testing/ which
      changed from module to package.
    </check>
    <check id="2.2" name="re-export-completeness">
      For package conversions (embeddings, ab_testing),
      verify __init__.py re-exports all public symbols.
      For sibling splits, verify the parent module
      imports from the new sibling.
    </check>
    <check id="2.3" name="no-dead-code">
      Check for duplicated functions across sibling
      modules. domain_templates.py split into 5 files —
      verify no overlap.
    </check>
    <check id="2.4" name="naming-consistency">
      Verify module names match content. Flag any
      ambiguous names (e.g., does "domain.py" vs
      "domain_models.py" vs "domain_registry.py" have
      clear boundaries?).
    </check>
    <check id="2.5" name="circular-imports">
      Test: python -c "from attune.socratic.embeddings import *"
      and similar for each package conversion.
    </check>
  </checks>

  <risks>
    <risk severity="medium">
      socratic/agent_templates.py name collision with
      orchestration/agent_templates/ package. Verify
      these are distinct and no import confusion.
    </risk>
    <risk severity="low">
      domain_templates split into 5 files may have
      created unclear boundaries. Review if
      domain_models vs domain_registry separation
      is clean.
    </risk>
  </risks>

  <validation>
    <pass-criteria>
      All imports resolve. No duplicates. Package
      conversions re-export completely. No naming
      collisions.
    </pass-criteria>
    <output>
      Markdown table: file | check | status | notes
    </output>
  </validation>
</task>
```

---

## Task 3: Workflows Audit

```xml
<task id="audit-3" name="workflow-modules">
  <objective>
    Audit all file splits in src/attune/workflows/ for
    import integrity, re-export correctness, dead code,
    and structural coherence.
  </objective>

  <scope>
    <split original="workflows/code_review.py"
           type="sibling-module">
      <new>workflows/code_review_architect.py</new>
      <new>workflows/code_review_classify.py</new>
      <new>workflows/code_review_crew_mixin.py</new>
      <new>workflows/code_review_scan.py</new>
    </split>
    <split original="workflows/document_gen/workflow.py"
           type="sibling-module">
      <new>document_gen/outline_stage.py</new>
      <new>document_gen/polish_stage.py</new>
      <new>document_gen/write_stage.py</new>
    </split>
    <split original="workflows/base.py"
           type="sibling-module">
      <new>workflows/context_proxy_mixin.py</new>
    </split>
    <split original="workflows/progressive/orchestrator.py"
           type="sibling-module">
      <new>progressive/orchestrator_prompts.py</new>
    </split>
    <split original="workflows/refactor_plan.py"
           type="sibling-module">
      <new>workflows/refactor_plan_report.py</new>
    </split>
    <split original="workflows/test_runner.py"
           type="sibling-module">
      <new>workflows/test_runner_helpers.py</new>
    </split>
    <split original="workflows/code_review_analysis_mixin.py"
           type="sibling-module">
      <new>workflows/code_review_analysis_helpers.py</new>
    </split>
    <split original="workflows/release_prep.py"
           type="sibling-module">
      <new>workflows/release_prep_approve.py</new>
      <new>workflows/release_prep_report.py</new>
      <new>workflows/release_prep_stages.py</new>
    </split>
    <split original="workflows/execution_mixin.py"
           type="sibling-module">
      <new>workflows/execution_finalize.py</new>
      <new>workflows/execution_standard.py</new>
      <new>workflows/execution_tier_fallback.py</new>
    </split>
    <split original="workflows/manage_documentation.py"
           type="sibling-module">
      <new>workflows/doc_crew_execution.py</new>
      <new>workflows/doc_crew_models.py</new>
      <new>workflows/doc_crew_report.py</new>
    </split>
    <split original="workflows/pr_review.py"
           type="sibling-module">
      <new>workflows/pr_review_analysis.py</new>
      <new>workflows/pr_review_formatting.py</new>
      <new>workflows/pr_review_models.py</new>
    </split>
    <split original="workflows/progress.py"
           type="sibling-module">
      <new>workflows/progress_models.py</new>
      <new>workflows/progress_reporters.py</new>
    </split>
    <split original="workflows/perf_audit.py"
           type="sibling-module">
      <new>workflows/perf_audit_optimize_mixin.py</new>
      <new>workflows/perf_audit_patterns.py</new>
      <new>workflows/perf_audit_report.py</new>
      <new>workflows/perf_audit_stages_mixin.py</new>
    </split>
    <split original="workflows/security_audit.py"
           type="sibling-module">
      <new>workflows/security_audit_stages.py</new>
      <new>workflows/security_audit_triage.py</new>
    </split>
    <split original="workflows/orchestrated_health_check.py"
           type="sibling-module">
      <new>workflows/health_check_models.py</new>
      <new>workflows/health_check_scoring.py</new>
      <new>workflows/health_check_tracking.py</new>
    </split>
  </scope>

  <checks>
    <check id="3.1" name="import-integrity">
      Grep for imports from each original module path.
      Verify they still resolve. Pay attention to
      code_review.py which was split into 4 sibling
      files — ensure the main module imports from them.
    </check>
    <check id="3.2" name="mixin-wiring">
      Several splits created mixins (context_proxy_mixin,
      code_review_crew_mixin, perf_audit_optimize_mixin,
      etc). Verify the parent class inherits from the
      mixin and the mixin's methods are accessible.
    </check>
    <check id="3.3" name="no-dead-code">
      Check that extracted helpers/stages aren't also
      still defined in the parent file. Common mistake
      with copy-then-delete refactoring.
    </check>
    <check id="3.4" name="naming-conventions">
      workflows/ uses several naming patterns:
      - {name}_mixin.py (mixins)
      - {name}_helpers.py (utility functions)
      - {name}_models.py (data classes)
      - {name}_report.py (formatting)
      - {name}_stages.py (pipeline stages)
      Verify consistency. Flag files that break pattern.
    </check>
  </checks>

  <risks>
    <risk severity="medium">
      base.py split — context_proxy_mixin.py is used
      by many workflows. Verify the mixin is imported
      and mixed in correctly in base.py.
    </risk>
    <risk severity="medium">
      execution_mixin.py split into 3 files. This is
      core execution logic — verify the fallback chain
      (standard -> tier_fallback -> finalize) is intact.
    </risk>
  </risks>

  <validation>
    <pass-criteria>
      All workflow imports resolve. Mixin inheritance
      chains are correct. No duplicated methods.
      Naming is consistent.
    </pass-criteria>
    <output>
      Markdown table: file | check | status | notes
    </output>
  </validation>
</task>
```

---

## Task 4: Memory, Infrastructure & Misc Audit

```xml
<task id="audit-4" name="memory-infrastructure">
  <objective>
    Audit all file splits in memory/, mcp/, monitoring/,
    models/, meta_workflows/, and top-level modules for
    import integrity and structural coherence.
  </objective>

  <scope>
    <group name="memory">
      <split original="memory/long_term.py"
             type="sibling-module">
        <new>memory/long_term_classification.py</new>
        <new>memory/long_term_integration.py</new>
        <new>memory/long_term_operations.py</new>
        <new>memory/long_term_pipelines.py</new>
      </split>
      <split original="memory/security/audit_logger.py"
             type="sibling-module">
        <new>memory/security/events.py</new>
        <new>memory/security/log_methods.py</new>
        <new>memory/security/query.py</new>
        <new>memory/security/reports.py</new>
      </split>
      <split original="memory/security/secrets_detector.py"
             type="sibling-module">
        <new>memory/security/secrets_types.py</new>
      </split>
      <split original="memory/file_session.py"
             type="sibling-module">
        <new>memory/file_session_models.py</new>
        <new>memory/file_session_patterns.py</new>
        <new>memory/file_session_persistence.py</new>
      </split>
      <split original="memory/cross_session.py"
             type="converted-to-package">
        <new>cross_session/__init__.py</new>
        <new>cross_session/conflicts.py</new>
        <new>cross_session/coordinator.py</new>
        <new>cross_session/models.py</new>
        <new>cross_session/service.py</new>
      </split>
    </group>
    <group name="mcp">
      <split original="mcp/server.py"
             type="sub-package">
        <new>mcp/handlers/__init__.py</new>
        <new>mcp/handlers/auth_handlers.py</new>
        <new>mcp/handlers/context_handlers.py</new>
        <new>mcp/handlers/memory_handlers.py</new>
        <new>mcp/handlers/telemetry_handlers.py</new>
        <new>mcp/handlers/workflow_handlers.py</new>
        <new>mcp/prompts.py</new>
        <new>mcp/request_handler.py</new>
      </split>
    </group>
    <group name="monitoring">
      <split original="monitoring/alerts.py"
             type="sibling-module">
        <new>monitoring/engine.py</new>
        <new>monitoring/metrics.py</new>
        <new>monitoring/models.py</new>
        <new>monitoring/notifications.py</new>
        <new>monitoring/validators.py</new>
      </split>
    </group>
    <group name="models">
      <split original="models/fallback.py"
             type="sibling-module">
        <new>models/circuit_breaker.py</new>
        <new>models/fallback_policy.py</new>
        <new>models/resilient_executor.py</new>
        <new>models/retry.py</new>
        <new>models/tier_helper.py</new>
      </split>
    </group>
    <group name="meta_workflows">
      <split original="meta_workflows/workflow.py"
             type="sibling-module">
        <new>meta_workflows/llm_execution.py</new>
        <new>meta_workflows/prompt_builder.py</new>
        <new>meta_workflows/report_generator.py</new>
      </split>
      <split original="meta_workflows/pattern_learner.py"
             type="sibling-module">
        <new>meta_workflows/pattern_memory.py</new>
        <new>meta_workflows/pattern_reporting.py</new>
      </split>
    </group>
    <group name="top-level-modules">
      <split original="coordination.py"
             type="converted-to-package">
        <new>coordination/__init__.py</new>
        <new>coordination/agent_coordinator.py</new>
        <new>coordination/conflict_resolution.py</new>
        <new>coordination/team_session.py</new>
      </split>
      <split original="redis_memory.py"
             type="sibling-module">
        <new>redis_memory_coordination.py</new>
        <new>redis_memory_models.py</new>
        <new>redis_memory_patterns.py</new>
        <new>redis_memory_storage.py</new>
      </split>
      <split original="socratic_router.py"
             type="sibling-module">
        <new>socratic_router_discovery.py</new>
        <new>socratic_router_models.py</new>
        <new>socratic_router_patterns.py</new>
      </split>
      <split original="templates.py"
             type="sibling-module">
        <new>template_defs_basic.py</new>
        <new>template_defs_web.py</new>
        <new>template_engine.py</new>
      </split>
      <split original="workflow_commands.py"
             type="sibling-module">
        <new>_workflow_helpers.py</new>
        <new>workflow_fixall.py</new>
        <new>workflow_learn.py</new>
        <new>workflow_morning.py</new>
        <new>workflow_ship.py</new>
      </split>
      <split original="llm/core.py"
             type="sibling-module">
        <new>llm/interaction.py</new>
        <new>llm/security.py</new>
      </split>
      <split original="project_index/scanner.py"
             type="sibling-module">
        <new>project_index/code_metrics.py</new>
        <new>project_index/dependency_analysis.py</new>
        <new>project_index/file_analysis.py</new>
      </split>
      <split original="telemetry/commands/dashboard_commands.py"
             type="sibling-module">
        <new>telemetry/commands/dashboard_file_tests.py</new>
        <new>telemetry/commands/dashboard_telemetry.py</new>
      </split>
    </group>
  </scope>

  <checks>
    <check id="4.1" name="import-integrity">
      Grep for imports from each original path. Verify
      they resolve. High-risk: coordination.py and
      cross_session.py changed from module to package.
    </check>
    <check id="4.2" name="re-export-completeness">
      Check __init__.py files for coordination/ and
      cross_session/ packages. Verify all public symbols
      are re-exported.
    </check>
    <check id="4.3" name="mcp-handler-registration">
      mcp/server.py was split into a handlers/ package.
      Verify all handlers are registered in the server
      and the handler dispatch still works.
    </check>
    <check id="4.4" name="models-fallback-chain">
      models/fallback.py split into 5 files including
      circuit_breaker, retry, resilient_executor. Verify
      the resilience chain (retry -> circuit_breaker ->
      fallback_policy) is wired correctly.
    </check>
    <check id="4.5" name="no-dead-code">
      Check for duplicated definitions across sibling
      modules. Especially workflow_commands.py which
      split into 5 files.
    </check>
  </checks>

  <risks>
    <risk severity="high">
      models/fallback.py is core infrastructure for
      LLM resilience. The split into 5 files must
      preserve the exact retry/circuit-breaker/fallback
      behavior.
    </risk>
    <risk severity="medium">
      mcp/server.py handler registration — if any
      handler isn't imported in the new structure,
      MCP tools will silently disappear.
    </risk>
  </risks>

  <validation>
    <pass-criteria>
      All imports resolve. Package conversions re-export
      completely. MCP handlers all registered. Fallback
      chain intact.
    </pass-criteria>
    <output>
      Markdown table: file | check | status | notes
    </output>
  </validation>
</task>
```

---

## Task 5: Cross-Cutting Validation

```xml
<task id="audit-5" name="cross-cutting-validation">
  <objective>
    Run cross-cutting checks that span all splits:
    test suite health, coverage delta, unused re-exports,
    and modified test file correctness.
  </objective>

  <depends-on>Tasks 1-4 (or run independently after
  test suite completes)</depends-on>

  <checks>
    <check id="5.1" name="test-suite-passes">
      Run: pytest tests/ -x --tb=short
      All tests must pass. If failures, categorize as:
      - Import error (broken by split)
      - Assertion error (behavior changed)
      - Other
    </check>
    <check id="5.2" name="coverage-delta">
      Run: pytest --cov=src/attune --cov-report=term-missing
      Compare against baseline (80% minimum). Flag any
      modules where coverage dropped significantly.
    </check>
    <check id="5.3" name="modified-test-files">
      Review each modified test file from git status:
      - tests/unit/progressive/test_workflow.py
      - tests/unit/progressive/test_workflow_integration.py
      - tests/unit/security/test_security_remediation.py
      - tests/unit/socratic/test_llm_analyzer.py
      - tests/unit/test_coverage_batch10.py
      - tests/unit/workflows/test_dependency_check.py
      For each: verify import paths updated correctly,
      no test logic changed (only imports), no tests
      removed.
    </check>
    <check id="5.4" name="unused-re-exports">
      For each __init__.py that re-exports symbols from
      sub-modules, grep codebase for imports using the
      old path. If nothing imports via the old path,
      the re-export may be unnecessary (or external
      consumers may need it — flag for review).
    </check>
    <check id="5.5" name="import-smoke-test">
      Run a bulk import check:
      python -c "
      import attune.agent_factory.crews.code_review
      import attune.agent_factory.crews.health_check
      import attune.agent_factory.crews.security_audit
      import attune.socratic.embeddings
      import attune.socratic.ab_testing
      import attune.coordination
      import attune.memory.cross_session
      import attune.orchestration.agent_templates
      print('All package imports OK')
      "
    </check>
  </checks>

  <validation>
    <pass-criteria>
      Tests pass. Coverage >= 80%. Modified test files
      only have import changes. Smoke test succeeds.
    </pass-criteria>
    <output>
      Summary report:
      - Test results: X passed, Y failed
      - Coverage: X% (delta from baseline)
      - Modified tests: all import-only changes (Y/N)
      - Smoke test: pass/fail
      - Unused re-exports: list
    </output>
  </validation>
</task>
```

---

## Execution Guide

| Task | Agent Type | Parallelizable | Est. Time |
|------|-----------|---------------|-----------|
| 1 | Explore | Yes | 5-10 min |
| 2 | Explore | Yes | 10-15 min |
| 3 | Explore | Yes | 10-15 min |
| 4 | Explore | Yes | 10-15 min |
| 5 | Bash | After tests | 5-10 min |

**Run tasks 1-4 in parallel**, then task 5 after the
test suite finishes.

**To execute all:**

```
# In Claude Code, run each as a subagent:
# Task tool with subagent_type=Explore for tasks 1-4
# Task tool with subagent_type=Bash for task 5
```

## Output Format

Each task should produce a summary table:

```markdown
## Audit Results: {Task Name}

**Score:** X/Y checks passed

| Check | Status | Notes |
|-------|--------|-------|
| import-integrity | pass | All N imports resolve |
| re-export-completeness | pass | __init__.py complete |
| ... | ... | ... |

### Issues Found
- [file.py:123](path#L123) — Description

### False Positives
| Pattern | Why Not a Problem |
|---------|-------------------|
| ... | ... |
```
