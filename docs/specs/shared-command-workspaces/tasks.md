# Shared Command Workspaces — Tasks

**Status:** completed (2026-09-01) — Tasks 1–9 accepted; no current task.

## Task 1 — Characterize the contract and name the extraction boundary

```xml
<task id="1" name="characterize-workspace-contract">
  <objective>
    Pin the existing attune-forms workspace schema and every Fix authority
    invariant, then define the smallest adapter/host protocol that fits Fix,
    Roundtable, and Spec without command-domain fields in the core.
  </objective>
  <files-to-modify>
    <file path="tests/unit/elicitation/test_fix_workspace.py">
      Add characterization for canonical rebuilding, altered binding,
      concurrent confirmation, terminal mutation, and fallback parity.
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="tests/unit/elicitation/test_command_workspace_contract.py">
      Protocol contract tests using minimal fake adapters representing Fix,
      nested Roundtable, and iterative Spec shapes.
    </file>
  </files-to-create>
  <validation>
    <check>Existing Fix suite passes unchanged before extraction.</check>
    <check>Contract tests prove phase names do not imply transitions.</check>
    <check>No production module is added until the tests fail for the named gap.</check>
  </validation>
</task>
```

## Task 2 — Shared host runtime and Fix compatibility migration

```xml
<task id="2" name="shared-host-and-fix-adapter">
  <depends-on>1</depends-on>
  <objective>
    Implement canonical workspace storage, revision/action binding, adapter
    registration, and transition results in attune-ai; migrate Fix as the
    compatibility witness without moving Fix semantics into shared code.
  </objective>
  <files-to-create>
    <file path="src/attune/elicitation/command_workspace.py" />
    <file path="tests/unit/elicitation/test_command_workspace.py" />
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/elicitation/fix_workspace.py" />
    <file path="src/attune/mcp/server.py" />
    <file path="src/attune/mcp/tool_schemas.py" />
  </files-to-modify>
  <validation>
    <check>All old Fix behavioral/security tests remain green.</check>
    <check>Two concurrent confirmations produce at most one approved argv.</check>
    <check>A live widget/Markdown action round trip returns the same legal action.</check>
    <check>Changed production code coverage is at least 90%.</check>
  </validation>
</task>
```

## Task 3 — Roundtable workspace adapter

```xml
<task id="3" name="roundtable-workspace-adapter">
  <depends-on>2</depends-on>
  <objective>
    Move Roundtable intake, spend preview, multi-round progress, follow-up
    gates, compact promotion triage, and terminal receipt onto the shared
    workspace contract while preserving board R1–R10 and the three-round cap.
  </objective>
  <files-to-create>
    <file path="src/attune/roundtable/workspace.py" />
    <file path="tests/unit/roundtable/test_workspace.py" />
  </files-to-create>
  <files-to-modify>
    <file path="plugin/skills/roundtable/SKILL.md" />
    <file path=".claude/skills/roundtable/SKILL.md" />
    <file path="src/attune/mcp/server.py" />
  </files-to-modify>
  <validation>
    <check>Compiler-dirty seat output still never reaches the board.</check>
    <check>Nested round and promotion checkpoints reject stale actions.</check>
    <check>Seven promotion items remain usable in the target viewport.</check>
    <check>A non-mocked run records seat receipts, synthesis, rulings, and terminal receipt.</check>
    <check>Skill projections are regenerated and drift tests pass.</check>
  </validation>
</task>
```

## Task 4 — Spec workspace adapter

```xml
<task id="4" name="spec-workspace-adapter">
  <depends-on>3</depends-on>
  <objective>
    Reuse spec_intake and expose spec creation, review, approval, task gates,
    resumable progress, and artifact receipts through the shared workspace.
  </objective>
  <files-to-create>
    <file path="src/attune/spec/workspace.py" />
    <file path="tests/unit/spec/test_workspace.py" />
  </files-to-create>
  <files-to-modify>
    <file path="plugin/skills/spec/SKILL.md" />
    <file path=".claude/skills/spec/SKILL.md" />
    <file path="src/attune/mcp/server.py" />
  </files-to-modify>
  <validation>
    <check>Existing spec intake candidates remain tree-derived.</check>
    <check>Redo/approve/resume loops use one canonical revision.</check>
    <check>Lifecycle BLOCKED and CHAIR_REQUIRED semantics cannot be bypassed.</check>
    <check>A non-mocked creation run links the exact artifacts and probes in its receipt.</check>
  </validation>
</task>
```

## Task 5 — Cohort examples 1 and 2

```xml
<task id="5" name="release-prep-and-bug-predict-adapters">
  <depends-on>4</depends-on>
  <objective>
    Ship both chair-selected leading cohort adapters: /release-prep first,
    then /bug-predict. Use their contrasting authority shapes to challenge
    the shared contract before wider rollout.
  </objective>
  <files-to-create>
    <file path="src/attune/workspaces/__init__.py" />
    <file path="src/attune/workspaces/release_prep.py" />
    <file path="src/attune/workspaces/bug_predict.py" />
    <file path="tests/unit/workspaces/test_release_prep.py" />
    <file path="tests/unit/workspaces/test_bug_predict.py" />
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/mcp/server.py" />
    <file path="plugin/skills/release-prep/SKILL.md" />
    <file path="plugin/skills/bug-predict/SKILL.md" />
    <file path=".agents/skills/release-prep/SKILL.md" />
    <file path=".agents/skills/bug-predict/SKILL.md" />
  </files-to-modify>
  <validation>
    <check>/release-prep preserves failed-gatekeeper-fails-gate semantics and repeated approvals.</check>
    <check>/bug-predict completes read-only without a synthetic confirmation gate.</check>
    <check>Both provide widget, Markdown/text, and terminal receipt paths.</check>
    <check>Any shared-core change is classified and recorded in decisions.md.</check>
  </validation>
</task>
```

## Task 6 — Select examples 3–10 from measured gaps

```xml
<task id="6" name="select-cohort-remainder">
  <depends-on>5</depends-on>
  <objective>
    Use the first four adapter receipts (Roundtable, Spec, release-prep,
    bug-predict) to select eight workflows that fill uncovered semantic
    matrix cells. Record the ordered list and per-example failure-sensitive
    receipt before implementation.
  </objective>
  <files-to-create>
    <file path="docs/specs/shared-command-workspaces/cohort.md" />
  </files-to-create>
  <files-to-modify>
    <file path="docs/specs/shared-command-workspaces/decisions.md" />
    <file path="docs/handoffs/codex-shared-command-workspaces-t1.md" />
  </files-to-modify>
  <validation>
    <check>The selection names the missing axis each example covers.</check>
    <check>No example is selected only for low implementation cost.</check>
    <check>The chair approves the ordered eight before Task 7 is authored.</check>
  </validation>
</task>
```

## Task 7 — Execute examples 3–10 as separately gated slices

```xml
<task id="7" name="execute-cohort-remainder">
  <depends-on>6</depends-on>
  <objective>
    Implement the eight approved adapters one at a time. Each example has
    its own chair gate, rollback boundary, 90% changed-code coverage receipt,
    fallback receipt, and live terminal receipt.
  </objective>
  <files-to-create>
    <file path="src/attune/workspaces/bulk.py" />
    <file path="src/attune/workspaces/memory_context.py" />
    <file path="src/attune/workspaces/smart_test.py" />
    <file path="src/attune/workspaces/doc_gen.py" />
    <file path="src/attune/workspaces/workflow_orchestration.py" />
    <file path="src/attune/workspaces/image_analysis.py" />
    <file path="src/attune/workspaces/verify.py" />
    <file path="src/attune/workspaces/security_audit.py" />
    <file path="tests/unit/workspaces/test_bulk.py" />
    <file path="tests/unit/workspaces/test_memory_context.py" />
    <file path="tests/unit/workspaces/test_smart_test.py" />
    <file path="tests/unit/workspaces/test_doc_gen.py" />
    <file path="tests/unit/workspaces/test_workflow_orchestration.py" />
    <file path="tests/unit/workspaces/test_image_analysis.py" />
    <file path="tests/unit/workspaces/test_verify.py" />
    <file path="tests/unit/workspaces/test_security_audit.py" />
    <file path="tests/unit/workspaces/test_cohort.py" />
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/mcp/server.py" />
    <file path="src/attune/workspaces/__init__.py" />
    <file path="tests/unit/test_mcp_memory_tools.py" />
    <file path="plugin/skills/bulk/SKILL.md" />
    <file path="plugin/skills/memory-and-context/SKILL.md" />
    <file path="plugin/skills/smart-test/SKILL.md" />
    <file path="plugin/skills/doc-gen/SKILL.md" />
    <file path="plugin/skills/workflow-orchestration/SKILL.md" />
    <file path="plugin/skills/image-analysis/SKILL.md" />
    <file path="plugin/skills/verify/SKILL.md" />
    <file path="plugin/skills/security-audit/SKILL.md" />
    <file path=".agents/skills/bulk/SKILL.md" />
    <file path=".agents/skills/memory-and-context/SKILL.md" />
    <file path=".agents/skills/smart-test/SKILL.md" />
    <file path=".agents/skills/doc-gen/SKILL.md" />
    <file path=".agents/skills/workflow-orchestration/SKILL.md" />
    <file path=".agents/skills/image-analysis/SKILL.md" />
    <file path=".agents/skills/verify/SKILL.md" />
    <file path=".agents/skills/security-audit/SKILL.md" />
    <file path="docs/specs/shared-command-workspaces/cohort.md" />
    <file path="docs/specs/shared-command-workspaces/decisions.md" />
    <file path="docs/handoffs/codex-shared-command-workspaces-t1.md" />
  </files-to-modify>
  <validation>
    <check>Ten cohort adapters exist in the chair-approved order.</check>
    <check>No adapter introduces command-domain concepts into shared core.</check>
    <check>The cohort ledger records core changes, failures, fallbacks, and receipts.</check>
    <check>The adapter interface is declared stable only after the tenth receipt.</check>
  </validation>
</task>
```

## Task 8 — Add validated action-scoped workspace responses

```xml
<task id="8" name="action-scoped-workspace-responses">
  <dependencies>
    <dep>7</dep>
  </dependencies>
  <objective>
    In the separate attune-forms repository, extend workspace actions with an
    optional declarative response schema and return only structurally
    validated, contract-bound values while preserving every version 1
    action-only response.
  </objective>
  <external-repository>Smart-AI-Memory/attune-forms</external-repository>
  <files-to-modify>
    <file path="src/attune_forms/workspace.py" />
    <file path="src/attune_forms/mcp_server.py" />
    <file path="src/attune_forms/__init__.py" />
    <file path="tests/test_workspace.py" />
    <file path="tests/test_mcp_server.py" />
  </files-to-modify>
  <validation>
    <check id="iqc-task-4-state">Before Task 8 arms, the public load_state receipt for docs/specs/interaction-quality-contract/tasks.md contains task 4 in completed; absent or malformed state is BLOCKED.</check>
    <check>Interaction Quality Task 4's accepted owner-routing receipt names this exact action-response gap.</check>
    <check>Actions without response fields preserve their serialized schema, widget/Markdown output, and collected response behavior.</check>
    <check>Action-scoped required fields, item ids, option membership, and unknown-key rejection use the public form validator rather than adapter callbacks.</check>
    <check>The canonical response schema participates in the contract digest and altered, stale, partial, duplicate, or replayed answers fail closed.</check>
    <check>A field-bearing action and a field-free sibling action on the same view validate only the schema associated with the selected action.</check>
    <check>Widget, Markdown, headless, and MCP collection return the same normalized response mapping.</check>
    <check>Changed production code coverage is at least 90% and the complete attune-forms suite passes on its supported Python versions.</check>
  </validation>
</task>
```

## Task 9 — Apply three-ruling Roundtable batches atomically

```xml
<task id="9" name="roundtable-three-ruling-batches">
  <dependencies>
    <dep>8</dep>
  </dependencies>
  <objective>
    Use the validated action-scoped response contract to apply Roundtable
    promotion rulings in bounded slices of at most three while retaining the
    one-candidate path as a compatible fallback and preserving board R1–R10.
  </objective>
  <files-to-modify>
    <file path="src/attune/roundtable/workspace.py" />
    <file path="src/attune/mcp/tool_schemas.py" />
    <file path="tests/unit/roundtable/test_workspace.py" />
    <file path="tests/unit/elicitation/test_interaction_conformance.py" />
    <file path="tests/unit/mcp/test_tool_schemas.py" />
  </files-to-modify>
  <validation>
    <check>Seven candidates complete through exactly three accepted batches of 3 + 3 + 1 and report +2 added submissions after the first.</check>
    <check>Each batch contains exactly the current item ids in canonical order; stale, partial, duplicate, foreign, or invalid members reject the whole batch without mutation.</check>
    <check>One accepted batch advances the workspace revision exactly once while recording every ruling exactly once.</check>
    <check>Because its declared choices include promote, every apply_rulings batch requires explicit confirmation and retains consequence text naming the authority granted.</check>
    <check>The legacy current-candidate promote/decline path remains completion-equivalent across widget, Markdown, and headless projections.</check>
    <check>The deterministic constrained profile proves every field and terminal batch action reachable when another_round is unavailable; the four-action state is an explicit failing sentinel owned by IQC Task 5, and unavailable native fit is not inferred.</check>
    <check>Changed production code coverage is at least 90% and command-cohort tests remain green.</check>
  </validation>
</task>
```

<!-- spec-state: {"schema_version": 1, "completed": ["1", "2", "3", "4", "5", "6", "7", "8", "9"], "current": null, "auto_run": false, "last_updated": "2026-09-01T22:57:26.798869+00:00"} -->
