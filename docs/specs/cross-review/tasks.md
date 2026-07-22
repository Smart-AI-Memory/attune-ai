# Cross Review — Tasks

**Status:** APPROVED (chair, 2026-07-22); execution SECOND after
cross-provider-session-handoff (chair sequencing), post-07-27.
OPEN-1..3 rulings land before T3 dogfooding begins.

Pre-execution rule: re-grep every named scope against the current
tree (spec text goes stale; code is the contract).

## T1 — review module

```xml
<task id="crossreview-t1" name="review-module">
  <objective>
    Build attune.roundtable.review: target/diff resolution with
    budget manifest (D2), brief build, seat invocation wrapper,
    lint_review() (D3), board posting (D1), ledger-row rendering
    (D5).
  </objective>
  <context>
    <existing-code path="src/attune/roundtable/">Board, compiler
    role budgets, seat recipes in the roundtable skill.</existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/roundtable/review.py">module per design
      D1-D5</file>
    <file path="tests/unit/roundtable/test_review.py">target
      resolution; manifest math; lint matrix (compliant /
      noncompliant / NO FINDINGS / ABSENT); ledger rendering</file>
  </files-to-create>
  <validation>
    <check>suite receipt: tests/unit/roundtable SERIAL, exact
      tail</check>
    <check>grep receipt: no mutating git tokens in review.py</check>
    <check>advisory invariant test: run result is success for
      findings / NO FINDINGS / ABSENT alike</check>
  </validation>
  <risks>
    <risk severity="medium">Seat recipe drift (CLI flags change) —
      recipes live in one place, imported by skill text and
      module.</risk>
  </risks>
</task>
```

## T2 — skill surface

```xml
<task id="crossreview-t2" name="skill-surface">
  <objective>
    /cross-review skill: plugin/skills/cross-review/SKILL.md,
    .claude shim, .agents mirror via sync_agents_skills.py --write
    (single-source projection rule — commit both sides).
  </objective>
  <validation>
    <check>tests/unit/plugins/test_plugin_reference_validation.py
      green (skill references resolve)</check>
    <check>drift-guard: .agents mirror regenerated in the same
      PR</check>
  </validation>
  <risks>
    <risk severity="low">Binding-posture language must appear in
      the skill body (advisory-only) — reviewed against
      requirements' Binding posture section.</risk>
  </risks>
</task>
```

## T3 — dogfood ledger (five real runs)

```xml
<task id="crossreview-t3" name="dogfood-ledger">
  <objective>
    Execute >=5 real cross-review runs on real diffs across >=2
    seats; accrue R5 ledger rows in receipts.md with human
    dispositions. This is the live-fire receipt AND the future
    gate-upgrade evidence base.
  </objective>
  <context>
    <depends>OPEN-1..3 ruled (07-27); T1+T2 merged.</depends>
  </context>
  <validation>
    <check>metric receipt: ledger rows == runs performed (no
      synthetic rows, D7)</check>
    <check>live-fire: at least one run per seat with the board
      thread id recorded</check>
  </validation>
  <risks>
    <risk severity="medium">Low finding-quality outcome is a VALID
      result — it rules the advisory posture permanent, not a
      failure to hide (dogfood-or-remove discipline).</risk>
  </risks>
</task>
```

## T4 — docs + OPEN closure

```xml
<task id="crossreview-t4" name="docs-open-closure">
  <objective>
    Feature page per the single-source playbook; record OPEN-1..3
    rulings in decisions.md; replace provisional knob values (D6)
    in one commit.
  </objective>
  <validation>
    <check>evidence-chain: each OPEN item's ruling cites the 07-27
      usage-read datum it rests on</check>
  </validation>
  <risks>
    <risk severity="low">None beyond docs drift; doc-import gate
      covers fenced imports.</risk>
  </risks>
</task>
```
