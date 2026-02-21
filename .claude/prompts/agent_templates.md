# XML Agent Prompt Templates

**Purpose**: Reusable XML structures for spawning autonomous agents with clear requirements and verification steps.

**Usage**: Copy template, fill in bracketed sections, use in Task tool prompt parameter.

---

## Template 1: Bug Fix

Use when: Fixing specific bugs with known symptoms

```xml
<task type="bug_fix">
  <objective>[One sentence: what bug to fix]</objective>

  <context>
    <symptom>[Error message, test failure, or behavior]</symptom>
    <suspected_cause>[Hypothesis about root cause]</suspected_cause>
    <affected_files>[Files that likely need changes]</affected_files>
  </context>

  <requirements>
    <must_fix>
      [List specific bugs to resolve]
    </must_fix>

    <must_verify>
      [How to confirm fix works - commands to run]
    </must_verify>

    <must_not_break>
      [Existing functionality that must continue working]
    </must_not_break>
  </requirements>

  <verification>
    <command>[Exact command to run test suite]</command>
    <expected_result>[What "success" looks like]</expected_result>
    <evidence_required>Include test output in response</evidence_required>
  </verification>

  <success_criteria>
    <definition>
      Task is complete ONLY when:
      1. [Specific condition 1]
      2. [Specific condition 2]
      3. Test output documented in response
    </definition>
  </success_criteria>

  <constraints>
    - Do not declare "complete" without running tests
    - Do not modify files outside [scope]
    - If tests fail, document WHY and propose fixes
  </constraints>
</task>
```

**Example**:
```xml
<task type="bug_fix">
  <objective>Fix telemetry calculate_savings baseline cost calculation</objective>

  <context>
    <symptom>
      Test test_calculate_savings failing with assertion error.
      Expected savings differs from actual by ~$0.02.
    </symptom>
    <suspected_cause>
      Hardcoded baseline_cost = len(entries) * 0.015 in usage_tracker.py line 407.
      Should calculate dynamic average from PREMIUM tier entries.
    </suspected_cause>
    <affected_files>
      src/attune/telemetry/usage_tracker.py
    </affected_files>
  </context>

  <requirements>
    <must_fix>
      Replace hardcoded $0.015 with dynamic calculation using avg_premium_cost
    </must_fix>

    <must_verify>
      Run unit test: python -m pytest tests/unit/telemetry/test_usage_tracker.py::test_calculate_savings -v
    </must_verify>

    <must_not_break>
      Other 13 unit tests must continue passing
    </must_not_break>
  </requirements>

  <verification>
    <command>python -m pytest tests/unit/telemetry/ -v</command>
    <expected_result>14 passed, 0 failed</expected_result>
    <evidence_required>Include full test output in response</evidence_required>
  </verification>

  <success_criteria>
    <definition>
      Task is complete ONLY when:
      1. test_calculate_savings passes
      2. All 14 unit tests pass (no regressions)
      3. Test output shown in &lt;test_results&gt; section of response
    </definition>
  </success_criteria>

  <constraints>
    - Do not declare "complete" without running full test suite
    - Do not modify telemetry schema or other functions
    - If tests fail, explain root cause before proposing new fix
  </constraints>
</task>
```

---

## Template 2: Feature Implementation

Use when: Building new functionality with acceptance criteria

```xml
<task type="feature">
  <objective>[Feature to implement in one sentence]</objective>

  <context>
    <user_need>[Why this feature matters]</user_need>
    <existing_system>[How current system works]</existing_system>
    <integration_points>[Where feature plugs into existing code]</integration_points>
  </context>

  <requirements>
    <functional>
      [What the feature must do - user-visible behavior]
    </functional>

    <non_functional>
      [Performance, security, compatibility requirements]
    </non_functional>

    <integration>
      [How feature integrates with existing code]
    </integration>
  </requirements>

  <acceptance_criteria>
    <criteria id="1">[Specific testable condition]</criteria>
    <criteria id="2">[Specific testable condition]</criteria>
    <criteria id="3">[Specific testable condition]</criteria>
  </acceptance_criteria>

  <testing_strategy>
    <unit_tests>[What to test at unit level]</unit_tests>
    <integration_tests>[What to test at integration level]</integration_tests>
    <manual_tests>[What to test manually]</manual_tests>
  </testing_strategy>

  <verification>
    <command>[Test command 1]</command>
    <command>[Test command 2]</command>
    <expected_result>[Pass criteria]</expected_result>
  </verification>

  <success_criteria>
    <definition>
      Feature is complete ONLY when:
      1. All acceptance criteria met
      2. All tests passing (unit + integration)
      3. Documentation updated
      4. No health score regression
    </definition>
  </success_criteria>

  <constraints>
    - Follow existing code patterns in [module]
    - Do not introduce new dependencies without approval
    - Maintain backward compatibility
  </constraints>
</task>
```

**Example**:
```xml
<task type="feature">
  <objective>Implement privacy-first usage telemetry with JSON Lines storage</objective>

  <context>
    <user_need>
      Track workflow usage, costs, and tier routing effectiveness without
      compromising user privacy. Enable cost analysis and tier optimization.
    </user_need>
    <existing_system>
      BaseWorkflow class in src/attune/workflows/base.py calls LLMs via
      _call_llm() method. No usage tracking currently exists.
    </existing_system>
    <integration_points>
      - BaseWorkflow._call_llm() (add tracking call)
      - CLI (new telemetry subcommand)
      - UnifiedMemory (potential future integration)
    </integration_points>
  </context>

  <requirements>
    <functional>
      - Track: workflow name, stage, tier, model, provider, cost, tokens, cache hits, duration
      - Store: JSON Lines format in ~/.empathy/telemetry.jsonl
      - CLI: show, savings, compare, reset, export commands
      - Privacy: No prompts, responses, file paths, or PII tracked
    </functional>

    <non_functional>
      - Thread-safe: Multiple workflows can write concurrently
      - Atomic writes: Use tempfile + os.rename() pattern
      - Privacy: SHA256 hash user_id, never store raw email
      - Performance: <5ms overhead per LLM call
    </non_functional>

    <integration>
      - BaseWorkflow._call_llm() calls usage_tracker.track_usage()
      - CLI adds telemetry subcommand group
      - JSON Lines schema v1.0 with version field for future compatibility
    </integration>
  </requirements>

  <acceptance_criteria>
    <criteria id="1">
      Run code-review workflow → creates entries in telemetry.jsonl
    </criteria>
    <criteria id="2">
      CLI command "attune telemetry show" displays usage statistics
    </criteria>
    <criteria id="3">
      CLI command "attune telemetry savings" calculates tier routing savings
    </criteria>
    <criteria id="4">
      Concurrent workflows don't corrupt JSON Lines file (thread-safety test)
    </criteria>
    <criteria id="5">
      No prompts, file paths, or PII in telemetry.jsonl (privacy audit)
    </criteria>
  </acceptance_criteria>

  <testing_strategy>
    <unit_tests>
      - test_track_usage(): Verify entry creation and schema
      - test_calculate_savings(): Verify savings calculation math
      - test_thread_safety(): Concurrent writes don't corrupt file
      - test_privacy(): Verify no PII in entries
    </unit_tests>
    <integration_tests>
      - test_code_review_tracking(): Real workflow creates entries
      - test_security_audit_tracking(): Multi-stage workflow tracking
      - test_cli_commands(): CLI reads and displays telemetry correctly
    </integration_tests>
    <manual_tests>
      - Run 3 different workflows, inspect telemetry.jsonl format
      - Verify CLI output matches expectations
    </manual_tests>
  </testing_strategy>

  <verification>
    <command>python -m pytest tests/unit/telemetry/ -v</command>
    <command>python -m pytest tests/integration/test_telemetry_integration.py -v</command>
    <command>attune telemetry show</command>
    <expected_result>
      - 14/14 unit tests pass
      - 6/6 integration tests pass
      - CLI displays usage stats without errors
    </expected_result>
  </verification>

  <success_criteria>
    <definition>
      Feature is complete ONLY when:
      1. All acceptance criteria verified (5/5)
      2. All tests passing (14 unit + 6 integration)
      3. docs/specs/TELEMETRY_DESIGN.md updated with final schema
      4. Health score ≥73/100 (no regression)
      5. Manual test confirms real workflows create entries
    </definition>
  </success_criteria>

  <constraints>
    - Follow existing CLI pattern (Typer-based commands)
    - Use JSON Lines (not JSON array) for append-only compatibility
    - Do not track prompts, responses, or code content (privacy requirement)
    - Maintain backward compatibility (optional feature, disabled by default)
  </constraints>
</task>
```

---

## Template 3: Health Check Improvement

Use when: Improving code health score by fixing lint/type/test issues

```xml
<task type="health_check">
  <objective>Improve health score from [current] to [target]</objective>

  <context>
    <current_state>
      <score>[X/100]</score>
      <issue_count>[N issues]</issue_count>
      <breakdown>[Issue types and counts]</breakdown>
    </current_state>

    <priority_guidance>
      [User emphasis on specific issues or constraints]
    </priority_guidance>
  </context>

  <requirements>
    <must_fix priority="critical">
      [Issues that must be fixed - blockers]
    </must_fix>

    <should_fix priority="high">
      [Issues that should be fixed - important but not blocking]
    </should_fix>

    <may_fix priority="low">
      [Issues that are nice to fix - optional]
    </may_fix>

    <must_not_break>
      - All existing tests must pass
      - No functionality regression
      - No new dependencies introduced
    </must_not_break>
  </requirements>

  <verification>
    <command>empathy health</command>
    <command>python -m pytest tests/ -v</command>
    <command>ruff check .</command>
    <command>mypy src/attune/</command>
    <expected_result>
      - Health score ≥[target]/100
      - All tests passing
      - Ruff: 0 errors
      - Mypy: 0 type errors
    </expected_result>
  </verification>

  <success_criteria>
    <score_target>[target]/100</score_target>
    <no_regressions>
      All tests that passed before still pass.
      No new lint or type errors introduced.
    </no_regressions>
    <efficiency>
      Focus on high-impact fixes (many errors per file).
      Autofix where possible (ruff --fix, auto-remove unused vars).
    </efficiency>
  </success_criteria>

  <constraints>
    - Do not skip or disable linters to improve score artificially
    - Do not move files to excluded directories just to hide errors
    - If fix would break functionality, document and skip
    - Prioritize critical > high > low based on user guidance
  </constraints>
</task>
```

**Example**:
```xml
<task type="health_check">
  <objective>Improve health score from 58/100 to 73+/100</objective>

  <context>
    <current_state>
      <score>58/100</score>
      <issue_count>61 issues</issue_count>
      <breakdown>
        - 50 BLE001 (broad exception catching) in benchmark scripts
        - 8 mypy type errors in adapters/
        - 3 F841 (unused variables) in tests
      </breakdown>
    </current_state>

    <priority_guidance>
      User is very concerned: "I thought you'd fixed these..."
      Must fix today and republish 3.8.X
    </priority_guidance>
  </context>

  <requirements>
    <must_fix priority="critical">
      - Fix all 50 BLE001 errors (move benchmark scripts to benchmarks/ directory)
      - Fix all 8 mypy type errors in adapters/langchain_adapter.py
      - Update pyproject.toml ruff config to exclude benchmarks/
    </must_fix>

    <should_fix priority="high">
      - Auto-fix 3 F841 unused variable warnings
    </should_fix>

    <may_fix priority="low">
      - None (focus on critical path to 73+)
    </may_fix>

    <must_not_break>
      - All existing tests must pass
      - No functionality regression
      - Benchmark scripts must still run from new location
    </must_not_break>
  </requirements>

  <verification>
    <command>empathy health</command>
    <command>python -m pytest tests/ -v --tb=short</command>
    <command>ruff check . --exclude benchmarks/</command>
    <command>mypy src/attune/</command>
    <expected_result>
      - Health score ≥73/100 (+15 points)
      - All tests passing (no regressions)
      - Ruff: 0 errors in src/, tests/, scripts/
      - Mypy: 0 type errors
    </expected_result>
  </verification>

  <success_criteria>
    <score_target>73+/100</score_target>
    <no_regressions>
      All tests that passed before still pass.
      Benchmark scripts still executable from benchmarks/ directory.
    </no_regressions>
    <efficiency>
      Use ruff --fix to auto-fix F841 warnings.
      Move all benchmark_*.py, profile_*.py, test_*.py to benchmarks/
    </efficiency>
  </success_criteria>

  <constraints>
    - Do not disable BLE001 globally - only exclude benchmarks/ directory
    - Do not skip mypy type checking - fix type errors properly
    - Preserve benchmark script functionality (users may run them)
    - Keep test suite passing (no broken tests acceptable)
  </constraints>
</task>
```

---

## Template 4: Documentation Update

Use when: Updating docs, READMEs, or specifications

```xml
<task type="documentation">
  <objective>[What documentation to update]</objective>

  <context>
    <reason>[Why update is needed]</reason>
    <current_state>[What docs currently say]</current_state>
    <desired_state>[What docs should say]</desired_state>
  </context>

  <requirements>
    <must_update>
      [Files that must be updated]
    </must_update>

    <must_verify>
      [How to verify accuracy - links work, examples run, etc.]
    </must_verify>

    <consistency>
      [Other files that may need similar updates]
    </consistency>
  </requirements>

  <verification>
    <command>[Command to test examples, if applicable]</command>
    <manual_check>[Things to manually verify]</manual_check>
  </verification>

  <success_criteria>
    <definition>
      Documentation is complete ONLY when:
      1. All must_update files updated
      2. Links verified (no 404s)
      3. Examples tested (if applicable)
      4. Consistent with related docs
    </definition>
  </success_criteria>
</task>
```

---

## Template 5: Research / Investigation

Use when: Exploring codebase, understanding systems, or investigating bugs

```xml
<task type="research">
  <objective>[Question to answer or area to investigate]</objective>

  <context>
    <background>[Why this research is needed]</background>
    <known_info>[What we already know]</known_info>
    <unknown_info>[What we need to discover]</unknown_info>
  </context>

  <investigation_plan>
    <step id="1">[First thing to investigate]</step>
    <step id="2">[Second thing to investigate]</step>
    <step id="3">[Third thing to investigate]</step>
  </investigation_plan>

  <expected_deliverable>
    <format>[Report, diagram, file list, etc.]</format>
    <content>[What information should be included]</content>
  </expected_deliverable>

  <success_criteria>
    <definition>
      Research is complete ONLY when:
      1. All investigation steps completed
      2. Question answered OR "cannot determine" with reasoning
      3. Evidence cited (file paths, line numbers, command outputs)
      4. Recommendations provided (if applicable)
    </definition>
  </success_criteria>
</task>
```

**Example**:
```xml
<task type="research">
  <objective>Investigate why BaseWorkflow telemetry integration isn't triggering</objective>

  <context>
    <background>
      Telemetry unit tests pass (14/14) but integration tests fail (1/6).
      Suggests usage_tracker.track_usage() isn't being called in real workflows.
    </background>
    <known_info>
      - BaseWorkflow._call_llm() should call usage_tracker.track_usage()
      - Code appears correct in src/attune/workflows/base.py
      - Unit tests mock the tracking and pass
    </known_info>
    <unknown_info>
      - Is _call_llm() actually being invoked in real workflows?
      - Is there an import error silently failing?
      - Is telemetry disabled by config?
    </unknown_info>
  </context>

  <investigation_plan>
    <step id="1">
      Add debug logging to BaseWorkflow._call_llm() entry point.
      Run code-review workflow and check if log message appears.
    </step>
    <step id="2">
      Verify usage_tracker import succeeds (no ImportError).
      Check if track_usage() is defined and callable.
    </step>
    <step id="3">
      Inspect telemetry.jsonl after workflow run.
      Count entries: should be 4 for code-review workflow.
    </step>
    <step id="4">
      Review integration test setup vs real workflow initialization.
      Check if mock/fixture is missing in integration tests.
    </step>
  </investigation_plan>

  <expected_deliverable>
    <format>
      Structured report with &lt;findings&gt;, &lt;root_cause&gt;, &lt;recommendations&gt; sections
    </format>
    <content>
      - Evidence: Log outputs, file contents, test results
      - Root cause: Specific reason integration fails
      - Recommendations: Exact fix to apply
    </content>
  </expected_deliverable>

  <success_criteria>
    <definition>
      Research is complete ONLY when:
      1. All 4 investigation steps completed
      2. Root cause identified with evidence
      3. Recommendations include specific file/line changes
      4. Confidence level stated (high/medium/low)
    </definition>
  </success_criteria>
</task>
```

---

## Template 6: Refactoring

Use when: Improving code structure without changing behavior

```xml
<task type="refactoring">
  <objective>[What to refactor and why]</objective>

  <context>
    <current_problem>[Why current code is problematic]</current_problem>
    <desired_improvement>[What improvement refactoring provides]</desired_improvement>
    <constraints>[What cannot change - interfaces, behavior, etc.]</constraints>
  </context>

  <requirements>
    <must_preserve>
      - [Behavior that must not change]
      - [API compatibility that must be maintained]
      - [Tests that must still pass]
    </must_preserve>

    <must_improve>
      - [Specific quality metrics to improve]
      - [Code smells to remove]
      - [Patterns to introduce]
    </must_improve>
  </requirements>

  <verification>
    <command>[Test command to verify behavior unchanged]</command>
    <expected_result>All existing tests pass (no regressions)</expected_result>
    <quality_metric>[How to measure improvement - complexity, duplication, etc.]</quality_metric>
  </verification>

  <success_criteria>
    <definition>
      Refactoring is complete ONLY when:
      1. All must_improve goals achieved
      2. All must_preserve constraints satisfied
      3. All tests passing (100% no regressions)
      4. Quality metrics show improvement
    </definition>
  </success_criteria>

  <rollback_plan>
    [How to revert changes if something breaks]
  </rollback_plan>
</task>
```

---

## Agent Response Template

**All agents should structure responses using this XML format**:

```xml
<agent_report>
  <summary>
    [One paragraph: what was done]
  </summary>

  <changes_made>
    <file path="[absolute file path]">
      <change line="[line number or range]">
        [Description of change]
      </change>
      <rationale>
        [Why this change was necessary]
      </rationale>
    </file>
    <!-- Repeat for each modified file -->
  </changes_made>

  <test_results>
    <unit_tests>
      <command>[Command run]</command>
      <result>[X passed, Y failed]</result>
      <evidence>
        [Paste relevant test output]
      </evidence>
    </unit_tests>

    <integration_tests>
      <command>[Command run]</command>
      <result>[X passed, Y failed]</result>
      <evidence>
        [Paste relevant test output]
      </evidence>
    </integration_tests>

    <health_check>
      <command>empathy health</command>
      <result>Score: [X/100]</result>
    </health_check>
  </test_results>

  <verification_evidence>
    <manual_test>
      <description>[What was manually tested]</description>
      <result>[What happened]</result>
    </manual_test>
    <!-- Repeat for additional manual tests -->
  </verification_evidence>

  <status>
    <complete>[true/false]</complete>
    <confidence>[percentage]</confidence>
    <rationale>
      [Why work is complete OR why additional work needed]
    </rationale>
  </status>

  <recommendations>
    <next_steps>
      - [Action 1]
      - [Action 2]
      - [Action 3]
    </next_steps>

    <concerns>
      [Any concerns, edge cases, or risks to be aware of]
    </concerns>
  </recommendations>
</agent_report>
```

---

## Quick Reference

| Task Type | Use When | Key Sections |
|-----------|----------|--------------|
| bug_fix | Fixing specific bugs | context, must_fix, verification |
| feature | Building new functionality | acceptance_criteria, testing_strategy |
| health_check | Improving code quality | priority, score_target, no_regressions |
| documentation | Updating docs | must_update, links_work, consistency |
| research | Investigating issues | investigation_plan, evidence, confidence |
| refactoring | Improving code structure | must_preserve, must_improve, rollback_plan |

---

## Tips for Effective XML Prompts

1. **Be Specific**: "Fix telemetry bugs" → "Fix calculate_savings baseline calculation in line 407"
2. **Quantify Success**: "Improve health" → "Improve from 58/100 to 73+/100"
3. **Explicit Verification**: "Make sure it works" → "&lt;command&gt;python -m pytest tests/unit/telemetry/ -v&lt;/command&gt;"
4. **Quality Gates**: Always include constraints like "Do not declare complete without test evidence"
5. **Evidence Required**: Specify what proof agent must provide (test output, command results, file diffs)

---

*Templates version 1.0 - Created 2026-01-07 as part of XML Agent Communication Protocol*
