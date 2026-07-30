# Feature Lead Governance — Tasks

**Status:** draft (2026-07-27) — OPEN-1..4 ruled and the revision
pass applied. P1 ruled 2026-07-30 (full activation): the P1 gate
no longer blocks execution; T1+ awaits tasks approval through the
/spec loop.

Pre-execution rule: re-grep all named integration points against the
current tree. Handoff and cross-review T1+T2 are SHIPPED dependencies
(consume their seams as-is); their pending T3/T4, not this draft,
will own any new packet/board fields (propose amendments, never a
parallel format).

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
    Register the D7-shrunk surface — assignment_propose /
    assignment_status / assignment_dispose_finding — through the
    existing Attune MCP server. Transfer/complete/revoke requests
    return chair_required plus registry-PR instructions; no MCP tool
    asserts human approval (decisions.md D7).
  </objective>
  <context>
    <depends>featurelead-t1</depends>
  </context>
  <validation>
    <check>real server dispatch round trip for every tool</check>
    <check>read-only status works without workspace write access</check>
    <check>denied writes and unavailable leads return truthful
      structured failures</check>
    <check>a transfer/complete/revoke request returns chair_required
      and mutates nothing</check>
  </validation>
  <risks>
    <risk severity="low">RESOLVED by D7 (was: MCP caller identity may
      not prove “human”) — chair transitions moved out of MCP into
      chair-merged registry PRs verified by the D3 probe set;
      residual risk is probe-implementation fidelity, covered by the
      per-probe security tests.</risk>
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
    <risk severity="medium">Distribution lag: the Codex/Antigravity
      seats consume the PUBLISHED attune-ai, so the live matrix waits
      for a release carrying the governance tools — schedule the
      receipts post-publish, and record seat ABSENT (not failure)
      when a seat is unavailable (R7).</risk>
  </risks>
</task>
```
