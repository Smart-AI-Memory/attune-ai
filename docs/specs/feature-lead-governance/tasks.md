# Feature Lead Governance — Tasks

**Status:** DRAFT — do not execute until requirements and OPEN-1..4 are
chair-approved.

Pre-execution rule: re-grep all named integration points against the
current tree. The handoff and cross-review specs are currently moving;
their shipped APIs, not this draft, will be authoritative.

## T1 — governance core

```xml
<task id="featurelead-t1" name="governance-core">
  <objective>
    Implement the provider-neutral assignment, lifecycle, authority,
    finding, and disposition models from D1-D4.
  </objective>
  <files-to-create>
    <file path="src/attune/governance/__init__.py">public API</file>
    <file path="src/attune/governance/assignment.py">schema,
      validated persistence, transition table</file>
    <file path="src/attune/governance/findings.py">immutable findings
      and appended dispositions</file>
    <file path="src/attune/governance/policy.py">feature_lead_v1
      authority and conflict resolution</file>
    <file path="tests/unit/governance/">unit and security suites</file>
  </files-to-create>
  <validation>
    <check>AC-1 through AC-5 and AC-7 have direct failure tests</check>
    <check>path traversal and symlink escapes fail before I/O</check>
    <check>changed-code coverage is at least 80%</check>
  </validation>
  <risks>
    <risk severity="high">A caller-forged human approval would erase
      the authority boundary; activation/transfer/revocation need an
      explicit trusted invocation context.</risk>
  </risks>
</task>
```

## T2 — MCP assignment surface

```xml
<task id="featurelead-t2" name="mcp-surface">
  <objective>
    Register assignment_create/status/transfer/dispose_finding/
    complete through the existing Attune MCP server and trusted human
    decision boundary.
  </objective>
  <context>
    <depends>featurelead-t1</depends>
  </context>
  <validation>
    <check>real server dispatch round trip for every tool</check>
    <check>read-only status works without workspace write access</check>
    <check>denied writes and unavailable leads return truthful
      structured failures</check>
  </validation>
  <risks>
    <risk severity="high">MCP caller identity may not prove “human”;
      implementation must identify the existing trusted decision
      mechanism or hold mutating transitions for explicit UI
      confirmation.</risk>
  </risks>
</task>
```

## T3 — handoff and cross-review integration

```xml
<task id="featurelead-t3" name="collaboration-integration">
  <objective>
    Link assignment IDs/digests into handoff and append immutable
    cross-review findings for separate lead disposition.
  </objective>
  <context>
    <depends>featurelead-t2</depends>
    <existing-spec path="docs/specs/cross-provider-session-handoff/"/>
    <existing-spec path="docs/specs/cross-review/"/>
  </context>
  <validation>
    <check>AC-6 live transfer detects deliberate HEAD/file drift</check>
    <check>reviewer text is byte-preserved through disposition</check>
    <check>ABSENT reviewer never becomes self-review</check>
  </validation>
  <risks>
    <risk severity="medium">Pending feature APIs may change; adapt to
      main rather than recreating their storage or invocation paths.</risk>
  </risks>
</task>
```

## T4 — projected contract and user surface

```xml
<task id="featurelead-t4" name="contract-docs-dogfood">
  <objective>
    Add feature-lead behavior to the collaboration master, project all
    provider surfaces, document the tools, and run the two-direction
    dogfood matrix from D7.
  </objective>
  <context>
    <depends>featurelead-t3</depends>
  </context>
  <validation>
    <check>AC-8 projector check exits zero</check>
    <check>Claude-lead/Codex-review live receipt recorded</check>
    <check>Codex-lead/Claude-review live receipt recorded</check>
    <check>preference-only churn and actionable findings are counted
      separately in receipts.md</check>
  </validation>
  <risks>
    <risk severity="medium">Two successful demos do not prove reduced
      rewrite churn; retain opt-in posture until repeated use shows a
      useful signal.</risk>
  </risks>
</task>
```
