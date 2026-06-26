# Plan: spec-gate-real-review

Execution plan for `docs/specs/spec-gate-real-review/`. Tasks are
ordered: the gate rewire (T1) must land before any deletion so no
live code references the dead engine at removal time.

---

<task id="1" name="rewire-quality-gate">
  <objective>
    Replace the fake StubAgent-backed quality gate with real review:
    _run_quality_gate calls CodeReviewWorkflow + SecurityAuditWorkflow
    directly, gates on their actual scores, and fails closed on error.
  </objective>

  <context>
    <existing-code path="src/attune/pipeline/orchestrator.py">
      _run_quality_gate (line ~225) currently builds a DynamicTeam via
      DynamicTeamBuilder().build_from_plan(plan) and calls
      team.execute(). The plan dict names code_reviewer +
      security_auditor with parallel strategy and 70.0 thresholds.
      run_gates_for_task wraps it in try/except (fails closed already).
    </existing-code>
    <existing-code path="src/attune/workflows/__init__.py">
      "code-review" -> CodeReviewWorkflow (.code_review),
      "security-audit" -> SecurityAuditWorkflow (.security_audit).
      Both are live BaseWorkflow subclasses returning a score.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/pipeline/orchestrator.py">
      <change location="_run_quality_gate + module docstring + imports">
        BEFORE: import DynamicTeamBuilder; build_from_plan; team.execute()
        AFTER: instantiate CodeReviewWorkflow() and SecurityAuditWorkflow(),
        run both on target_files (asyncio.gather), read real scores,
        apply 70.0 thresholds, return (passed, details, cost). Remove
        the DynamicTeamBuilder import and the "DynamicTeam, WorkflowComposer"
        line from the module docstring. On any review exception, return
        (False, {"error": ...}, 0.0) — fail closed.
      </change>
    </file>
    <file path="tests/unit/pipeline/test_orchestrator.py">
      <change location="gate tests">
        Update tests that assumed team/StubAgent backing. Add: bad-score
        task -> gate fails; review raises -> gate fails closed (not pass).
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>DOGFOOD (R1): run /spec gate on a task with a deliberately bad file; gate fails with real score &lt; 70 — not a mocked pass.</check>
    <check>R2: monkeypatch a review workflow to raise; gate returns not-passed.</check>
    <check>grep -n "DynamicTeam" src/attune/pipeline/orchestrator.py is empty.</check>
    <check>/spec of a trivial good task still completes (R5).</check>
  </validation>

  <risks>
    <risk severity="medium">Review workflows may need an API key / tier routing; ensure gate degrades sanely (fail-closed) when unavailable rather than crashing the pipeline.</risk>
  </risks>
</task>

---

<task id="2" name="tag-and-remove-orchestration-engine">
  <objective>
    Tag pre-removal state, then delete the dead orchestration engine
    modules and prune the package's public surface.
  </objective>

  <context>
    <existing-code path="src/attune/orchestration/__init__.py">
      Exports DynamicTeam, DynamicTeamBuilder, DynamicTeamResult,
      TeamSpecification, TeamStore, WorkflowAgentAdapter,
      WorkflowComposer, MetaOrchestrator, ExecutionPlan,
      CompositionPattern, TaskComplexity/Domain/Requirements — all dead
      per decisions.md D2. KEEP: agent_templates exports,
      ExecutionStrategy/get_strategy/concrete strategies.
    </existing-code>
  </context>

  <files-to-create>
    <file path="(git tag)">
      archive/spec-gate-real-review-pre-removal pushed before deletion.
    </file>
  </files-to-modify>

  <files-to-modify>
    <file path="DELETE">
      orchestration/agent_models.py (StubAgent — verify AgentLike/SDKAgentResult/SDKExecutionMode have no live consumer; keep what does),
      dynamic_team.py, team_builder.py, workflow_composer.py,
      workflow_agent_adapter.py, meta_orchestrator.py, meta_orch_analysis.py,
      meta_orch_estimation.py, meta_orch_interactive.py, team_store.py
      (verify each at removal time via grep for live caller).
    </file>
    <file path="src/attune/orchestration/__init__.py">
      Remove the dead exports; keep agent_templates + strategies.
    </file>
    <file path="DELETE tests">
      test_dynamic_team.py, test_team_builder.py, test_workflow_composer.py,
      test_workflow_agent_adapter.py, test_meta_orchestrator.py,
      test_meta_orch_interactive.py, test_meta_orchestrator_interactive.py.
      Update test_registry_coverage.py note + test_critical_workflows_smoke.py
      StubAgent fixture.
    </file>
  </files-to-modify>

  <validation>
    <check>R3: grep -rn "StubAgent\|DynamicTeam\|WorkflowComposer\|WorkflowAgentAdapter" src/ is empty.</check>
    <check>R6: python -c "import attune.orchestration" succeeds.</check>
    <check>R4: health-check workflow runs end-to-end (strategies survived).</check>
  </validation>

  <risks>
    <risk severity="high">agent_models.py also defines AgentLike/SDKAgentResult/SDKExecutionMode — grep for live consumers before deleting the file; extract survivors if any.</risk>
  </risks>
</task>

---

<task id="3" name="remove-multi-agent-mixin">
  <objective>
    Remove the dead MultiAgentMixin and the workflows/base.py
    multi-agent params it was the only consumer of.
  </objective>
  <files-to-modify>
    <file path="DELETE">src/attune/workflows/multi_agent_mixin.py + tests/unit/workflows/test_multi_agent_mixin.py</file>
    <file path="src/attune/workflows/base.py">
      <change location="multi_agent_configs param + Phase-4 wiring (lines ~259, ~334)">
        Remove multi_agent_configs and the DynamicTeam integration block.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>grep -rn "MultiAgentMixin\|multi_agent_config" src/ tests/ is empty.</check>
    <check>workflows/base.py imports clean; workflow suite green.</check>
  </validation>
</task>

---

<task id="4" name="remove-dead-decompose-llm-path">
  <objective>
    Remove TaskDecomposer.decompose() dead LLM path (the _call_llm
    signature-drift bug) while KEEPING the live _parse_tasks_from_xml
    parser used by spec_reader. Handle internal_workflow.py the same way.
  </objective>
  <context>
    <existing-code path="src/attune/wizards/decomposer.py">
      decompose() at ~225 calls self._workflow._call_llm(prompt,
      ModelTier.CAPABLE, "decompose") — dead, drifted signature.
      _parse_tasks_from_xml is LIVE via pipeline/spec_reader.py.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/wizards/decomposer.py">
      <change location="decompose()">Remove the dead LLM path; keep the parser. Verify spec_reader still imports cleanly.</change>
    </file>
    <file path="src/attune/wizards/internal_workflow.py">
      <change location="_call_llm site">Classify caller; remove if dead, keep if live.</change>
    </file>
  </files-to-modify>
  <validation>
    <check>pipeline/spec_reader.py still parses an XML spec (parser intact).</check>
    <check>grep for live callers of decompose() is empty before removal.</check>
  </validation>
</task>

---

<task id="5" name="docs-changelog-release">
  <objective>
    Regenerate/prune help docs that reference removed symbols, add
    CHANGELOG entry, bump version (breaking removal of public
    orchestration symbols), finalize decisions.md.
  </objective>
  <files-to-modify>
    <file path="plugin/help/generated/tasks/orchestration.md + quickstarts/orchestration.md">
      Regenerate or remove DynamicTeam/WorkflowComposer examples.
    </file>
    <file path="CHANGELOG.md">Breaking: removed dead DynamicTeam engine; /spec gates now perform real review.</file>
    <file path="docs/specs/spec-gate-real-review/decisions.md">Add D-FINAL with shipped PR refs.</file>
  </files-to-modify>
  <validation>
    <check>grep -rn "DynamicTeam\|StubAgent" plugin/ docs/ returns only this spec's own files.</check>
    <check>Required CI green (pre-commit, lint, code-quality, coverage, platform-compat, test 3.12, CodeQL, default-install-smoke).</check>
  </validation>
</task>
