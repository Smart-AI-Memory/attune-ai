# Workflow Intake Forms — Tasks

**Status:** active (2026-07-31) — Task 1 authored, awaiting its
chair go. Tasks 2–4 are gated placeholders: each is authored only
after the prior phase's acceptance passes (spec rule; no batch
authorization exists).

## Task 1 — Phase 1: declare the input contracts (AUTHORED, not started)

```xml
<task id="1" name="input-schema-sweep">
  <objective>
    Every registered workflow declares an InputSchema; workflow
    run rejects malformed input with named-field errors; the
    PATH_ARG_REGISTRY consumers that can cheaply read
    input_schema do so.
  </objective>
  <context>
    <existing-code path="src/attune/workflows/validation.py">
      InputSchema (required keys + key types) and
      validate_against_input_schema already exist; coverage is
      the gap, not machinery.
    </existing-code>
    <constraint>
      Execution scope is GREP-DERIVED at start time: the set of
      registry workflows whose class lacks input_schema — never
      this document's guess. Record the measured set in the PR.
    </constraint>
    <constraint>
      Contracts stay UI-free: no labels, help text, or provider
      hints on workflows — that is the template layer's job
      (design.md).
    </constraint>
  </context>
  <files-to-modify>
    <file path="src/attune/workflows/*.py">
      Add input_schema declarations matching each workflow's
      actual execute() consumption (read the code, not the docs).
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="tests/unit/workflows/test_input_schema_coverage.py">
      Registry sweep: every discovered workflow declares
      input_schema (shrink-only allowlist for any ruled
      exception); plus one behavioral case per key type showing
      the named-field rejection message.
    </file>
  </files-to-create>
  <validation>
    <check>Coverage sweep passes with an empty (or ruled)
      allowlist.</check>
    <check>`attune workflow run fix --input '{}'` (and one more
      workflow) fail with named missing keys, exit per the pinned
      0/1/2/3 contract — characterization pins untouched.</check>
    <check>No behavior change for valid inputs: full suite green,
      serial keyless.</check>
  </validation>
  <risks>
    <risk severity="medium">A declared schema stricter than a
      workflow's real tolerance breaks a working caller —
      mitigation: derive keys from execute() reads, and land the
      sweep test's behavioral cases per workflow touched.</risk>
  </risks>
</task>
```

## Task 2 — Phase 2: FormTemplate + providers (GATED)

Authored only when the rule-of-three fires (a third intake is
requested). Must include the byte-identical re-expression pins
for the fix and spec intakes (design.md proof obligation).

## Task 3 — Phase 2/theme: shared form theme (GATED)

`attune/elicitation/theme.py` (`FORM_THEME_CSS`, host-token
fallbacks), widget injection swap, dashboard static projection,
budget + byte-equality drift tests, rendered screenshots on both
surfaces. May be authored alongside Task 2 or independently —
chair's call; it has no dependency on the template layer.

## Task 4 — Phase 3: latency instrumentation + cache (GATED)

Instrument first; cache and the Redis-Function escalation only on
a measured budget miss (design.md latency mechanics).
