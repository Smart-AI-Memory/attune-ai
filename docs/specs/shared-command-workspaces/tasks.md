# Shared Command Workspaces — Tasks

**Status:** active planning (2026-08-31) — tasks authored from approved
requirements; no implementation task is authorized yet. Execute one task at
a time behind its own chair gate.

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
  <validation>
    <check>Ten cohort adapters exist in the chair-approved order.</check>
    <check>No adapter introduces command-domain concepts into shared core.</check>
    <check>The cohort ledger records core changes, failures, fallbacks, and receipts.</check>
    <check>The adapter interface is declared stable only after the tenth receipt.</check>
  </validation>
</task>
```
