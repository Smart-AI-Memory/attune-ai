# Agent SDK Code Review Workflow

**Created:** 2026-03-08
**Source:** /brainstorm session

## Problem

The current `CodeReviewWorkflow` uses a rigid multi-stage
pipeline (classify, scan, perf_check, architect_review,
etc.) with predefined tier routing. It can't autonomously
explore the codebase or adapt its review strategy based on
what it finds. Replacing it with an Agent SDK-powered
workflow will produce more thorough findings by letting
Claude explore freely, while running on the subscription
(no API credits).

## Goals

- More thorough findings (primary)
- Faster execution (fewer sequential stages)
- Better output formatting
- Runs on Claude Code subscription (Agent SDK)
- Integrates with existing `WorkflowResult` structure
- Testable side-by-side against current workflow

## End State

A new `AgentCodeReviewWorkflow` that:

1. Uses `claude_agent_sdk.query()` with subagents
2. Returns a standard `WorkflowResult`
3. Can be A/B tested against `CodeReviewWorkflow`
4. Replaces the old workflow once proven better

## Task Prompts

Below are self-contained XML task specs for implementation.

---

### Task 1: Agent SDK Code Review Workflow Class

```xml
<task id="1" name="agent-sdk-review-workflow">
  <objective>
    Create a new AgentCodeReviewWorkflow that uses the
    Claude Agent SDK to perform autonomous code review,
    replacing the rigid multi-stage pipeline with
    subagent-based exploration.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/code_review.py">
      Current CodeReviewWorkflow uses 9 sequential stages
      with mixin classes (ClassifyMixin, ScanMixin,
      ArchitectMixin, CrewMixin, CodeReviewAnalysisMixin).
      Each stage has a fixed ModelTier assignment.
    </existing-code>
    <existing-code path="src/attune/workflows/data_classes.py">
      WorkflowResult dataclass with fields: success, stages,
      final_output, cost_report, started_at, completed_at,
      total_duration_ms, provider, error, metadata, summary,
      suggestions.
    </existing-code>
    <existing-code path="src/attune/agents/sdk/sdk_agent.py">
      SDKAgent wraps claude_agent_sdk.query() with tier
      escalation and heartbeat. Has SDKExecutionMode.FULL_SDK
      for delegating entire lifecycle to SDK.
    </existing-code>
    <existing-code path="src/attune/agents/sdk/sdk_team.py">
      SDKAgentTeam composes SDKAgent instances for
      parallel/sequential execution with QualityGates.
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/code_review_agent_sdk.py">
      AgentCodeReviewWorkflow class that:

      1. Inherits from BaseWorkflow
      2. Uses claude_agent_sdk.query() with subagents:
         - "security-reviewer": finds security vulns
           (eval, injection, path traversal, secrets)
         - "quality-reviewer": code quality, complexity,
           duplication, naming, error handling
         - "perf-reviewer": performance issues, N+1,
           unnecessary copies, blocking I/O
         - "architect-reviewer": design patterns,
           coupling, SOLID violations, API design
      3. Main agent orchestrates subagents and synthesizes
         a unified review report
      4. Returns WorkflowResult with:
         - stages populated from subagent results
         - final_output as structured review report
         - summary with overall assessment
         - suggestions as NextAction list
      5. Uses ClaudeAgentOptions with:
         - cwd set to project root
         - allowed_tools: Read, Glob, Grep, Agent
         - permission_mode: "default"
         - max_turns: reasonable limit (e.g. 20)
      6. Accepts input: path (str), focus (optional list
         of areas), depth ("quick"|"standard"|"deep")

      Key design decisions:
      - Use AgentDefinition for each subagent with
        focused system prompts
      - Parse ResultMessage output into structured
        findings (security, quality, perf, architecture)
      - Map findings to WorkflowStage objects for
        compatibility with existing result handling
      - Use structured output or JSON parsing for
        consistent result format
    </file>
  </files-to-create>

  <validation>
    <check>
      Import succeeds:
      from attune.workflows.code_review_agent_sdk
        import AgentCodeReviewWorkflow
    </check>
    <check>
      Class has name="code-review-sdk" attribute
    </check>
    <check>
      execute() returns a valid WorkflowResult
    </check>
    <check>
      Subagents are defined with appropriate tools
      and focused prompts
    </check>
  </validation>

  <risks>
    <risk severity="medium">
      Agent SDK requires claude-code CLI installed.
      Add graceful ImportError handling with clear
      message.
    </risk>
    <risk severity="low">
      Subagent output parsing may be brittle. Use
      structured output format or robust JSON extraction.
    </risk>
  </risks>
</task>
```

---

### Task 2: Result Adapter

```xml
<task id="2" name="result-adapter">
  <objective>
    Create an adapter that converts Agent SDK
    ResultMessage output into WorkflowResult, bridging
    the Agent SDK world with attune's workflow system.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/data_classes.py">
      WorkflowResult requires: success, stages (list of
      WorkflowStage), final_output, cost_report
      (CostReport), started_at, completed_at,
      total_duration_ms, summary, suggestions.
    </existing-code>
    <existing-code path="src/attune/agents/sdk/sdk_models.py">
      SDKAgentResult has: agent_id, role, success,
      findings, score, confidence, cost,
      execution_time_ms, error.
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/agent_sdk_adapter.py">
      AgentSDKResultAdapter class with:

      1. from_agent_result(result_text, subagent_results,
         timing, metadata) -> WorkflowResult
      2. Maps each subagent's findings to a WorkflowStage
      3. Builds CostReport (subscription-based, so cost
         fields can be zero or estimated)
      4. Extracts summary and suggestions from the main
         agent's synthesized output
      5. Parses structured findings into the final_output
         dict with keys: security, quality, performance,
         architecture
    </file>
  </files-to-create>

  <validation>
    <check>
      Adapter produces valid WorkflowResult from
      sample agent output
    </check>
    <check>
      stages list has one entry per subagent
    </check>
    <check>
      CostReport is valid (even with zero costs)
    </check>
  </validation>

  <risks>
    <risk severity="medium">
      Agent output format may vary. Adapter needs
      fallback parsing for unstructured text.
    </risk>
  </risks>
</task>
```

---

### Task 3: Registry Integration

```xml
<task id="3" name="registry-integration">
  <objective>
    Register AgentCodeReviewWorkflow in the workflow
    registry so it can be invoked via CLI and compared
    against the existing code-review workflow.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/__init__.py">
      _DEFAULT_WORKFLOW_NAMES dict maps workflow names
      to class names. get_workflow() lazy-loads by name.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/__init__.py">
      <change location="_DEFAULT_WORKFLOW_NAMES dict">
        BEFORE: no entry for code-review-sdk
        AFTER: add "code-review-sdk":
          "AgentCodeReviewWorkflow" entry
      </change>
      <change location="lazy import mapping">
        BEFORE: no import path for AgentCodeReviewWorkflow
        AFTER: add mapping to
          attune.workflows.code_review_agent_sdk
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>
      get_workflow("code-review-sdk") returns
      AgentCodeReviewWorkflow class
    </check>
    <check>
      list_workflows() includes code-review-sdk
    </check>
    <check>
      CLI invocation works:
      attune workflow run code-review-sdk
    </check>
  </validation>

  <risks>
    <risk severity="low">
      Name collision with existing workflows. Using
      "code-review-sdk" suffix avoids this.
    </risk>
  </risks>
</task>
```

---

### Task 4: A/B Comparison Harness

```xml
<task id="4" name="ab-comparison">
  <objective>
    Create a comparison script that runs both the old
    CodeReviewWorkflow and new AgentCodeReviewWorkflow
    on the same codebase and produces a side-by-side
    report of findings, speed, and thoroughness.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/code_review.py">
      CodeReviewWorkflow (current, stage-based)
    </existing-code>
    <dependency>Task 1 and Task 2 completed</dependency>
  </context>

  <files-to-create>
    <file path="scripts/compare_code_review.py">
      Async script that:

      1. Takes a --path argument (default: src/attune/)
      2. Runs CodeReviewWorkflow.execute(path=path)
      3. Runs AgentCodeReviewWorkflow.execute(path=path)
      4. Compares results:
         - Total findings count
         - Findings by category (security, quality,
           perf, architecture)
         - Unique findings in each (what one caught
           that the other missed)
         - Execution time
         - Output quality (structured vs unstructured)
      5. Prints markdown comparison table
      6. Saves results to
         .claude/plans/code-review-comparison.md
    </file>
  </files-to-create>

  <validation>
    <check>
      Script runs without errors on src/attune/
    </check>
    <check>
      Comparison output clearly shows differences
    </check>
    <check>
      Both workflows return valid WorkflowResult
    </check>
  </validation>

  <risks>
    <risk severity="low">
      Agent SDK workflow may be slower due to
      autonomous exploration. Track timing separately.
    </risk>
  </risks>
</task>
```

---

### Task 5: Tests

```xml
<task id="5" name="tests">
  <objective>
    Write behavioral tests for the new workflow and
    adapter, ensuring they integrate correctly with
    the existing workflow system.
  </objective>

  <context>
    <dependency>Tasks 1-3 completed</dependency>
    <existing-code path="tests/unit/">
      Existing test patterns use pytest, tmp_path,
      unittest.mock. Agent SDK calls should be mocked
      since they require the CLI.
    </existing-code>
  </context>

  <files-to-create>
    <file path="tests/unit/workflows/test_code_review_agent_sdk.py">
      Tests for AgentCodeReviewWorkflow:
      1. test_workflow_has_correct_attributes
         (name, description)
      2. test_execute_returns_workflow_result
         (mock agent SDK, verify result structure)
      3. test_subagents_are_defined
         (security, quality, perf, architect)
      4. test_handles_agent_sdk_not_installed
         (graceful ImportError)
      5. test_depth_parameter_affects_max_turns
         (quick=10, standard=20, deep=40)
    </file>
    <file path="tests/unit/workflows/test_agent_sdk_adapter.py">
      Tests for AgentSDKResultAdapter:
      1. test_converts_agent_output_to_workflow_result
      2. test_maps_subagent_findings_to_stages
      3. test_handles_empty_findings
      4. test_handles_malformed_agent_output
      5. test_cost_report_valid_for_subscription
    </file>
  </files-to-create>

  <validation>
    <check>pytest tests/unit/workflows/test_code_review_agent_sdk.py passes</check>
    <check>pytest tests/unit/workflows/test_agent_sdk_adapter.py passes</check>
    <check>All tests mock the Agent SDK (no real CLI calls)</check>
  </validation>

  <risks>
    <risk severity="low">
      Mocking claude_agent_sdk.query() requires
      matching the async iterator interface.
    </risk>
  </risks>
</task>
```

## Execution Order

1. **Task 2** — Result adapter (no dependencies)
2. **Task 1** — Workflow class (uses adapter)
3. **Task 3** — Registry integration
4. **Task 5** — Tests (validates 1-3)
5. **Task 4** — A/B comparison (validates everything)

## Open Questions

- Should `depth="deep"` also increase the number of
  subagents or just `max_turns`?
- Should the workflow support a `focus` parameter to
  limit review to specific areas (e.g., security only)?
- How should we handle the case where Agent SDK is not
  installed? Skip gracefully or error?
