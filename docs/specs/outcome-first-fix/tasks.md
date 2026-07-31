# Outcome-First Fix — Tasks

**Status:** draft (2026-07-30) — Task 0 authored; executing it
requires a chair go. Later phase tasks are authored only after
the prior phase's acceptance passes (decisions.md D2). This
file never carries more than the next executable unit.

## Task 0 — Phase 0: architecture and characterization proof

```xml
<task id="0" name="outcome-first-fix-phase0">
  <objective>
    Prove the canonical hardened failing-test Fix scenario can be
    traced end-to-end through EXISTING attune interfaces with zero
    new machinery, and pin current behavior with characterization
    tests so later phases change it deliberately or not at all.
  </objective>

  <context>
    <existing-code path="src/attune/cli_minimal.py">
      Top-level CLI. `attune workflow run` subparser (~line 159);
      `attune diagnose` seam (~line 207). No `fix` subcommand
      exists — the namespace is free.
    </existing-code>
    <existing-code path="src/attune/cli_router.py">
      HybridRouter + SmartRouter natural-language routing;
      _WORKFLOW_SKILL_MAP is the canonical workflow-name -> skill
      map. Do NOT extend it in Phase 0.
    </existing-code>
    <existing-code path="src/attune/workflows/data_classes.py">
      WorkflowResult (~line 86): success flag, error taxonomy
      (error_type/transient), suggestions. The receipt concept
      must map onto this + existing telemetry — no new result
      store.
    </existing-code>
    <existing-code path="src/attune/cli_commands/diagnosis_commands.py">
      Existing diagnosis seam; candidate route target for the Fix
      facade in later phases.
    </existing-code>
    <constraint>
      Phase 0 is read-only with respect to production code: no
      new or modified modules under src/attune/. Deliverables are
      docs, fixtures, and tests only.
    </constraint>
  </context>

  <files-to-create>
    <file path="docs/specs/outcome-first-fix/phase0-inventory.md">
      Seam map: every ruling concept (outcome contract DTO,
      execution receipt, verification probes, routing, --explain
      projection) mapped to a named existing interface — or
      explicitly listed under REMOVED with the reason. Include a
      traced walkthrough of the canonical scenario through those
      interfaces, and the evidence trace for the
      exit-0-with-failed-WorkflowResult divergence.
    </file>
    <file path="tests/fixtures/outcome_first_fix/">
      Deterministic fixture package: a tiny module with one
      seeded, unambiguous bug (e.g. off-by-one boundary), ONE
      failing target test, and green sibling tests — so "full
      suite green" is a probe distinct from "target test passes".
      Pure stdlib, OS-independent (no shell scripts, no chmod —
      Windows lanes are real).
    </file>
    <file path="tests/unit/characterization/test_outcome_first_phase0.py">
      Characterization pins: (a) `attune workflow list` / `attune
      workflow run` current contract, including the exit-code
      vs WorkflowResult.success divergence on mismatched input;
      (b) router mapping stability for fix-adjacent phrases
      through the REAL routing algorithm (never hand-predicted
      tables); (c) a dry-trace section that imports every
      interface named in phase0-inventory.md's seam map and
      asserts the documented call signature via introspection —
      a prose-only mapping fails this test. Mark each pin
      INTENTIONAL or INCIDENTAL so later phases know which
      behavior is contract and which is accident.
    </file>
  </files-to-create>

  <validation>
    <check>Fixture: target test fails and sibling tests pass, via
      a real pytest subprocess (non-mocked boundary), on the
      unmodified tree.</check>
    <check>Characterization tests pass against unmodified main —
      they pin behavior, they do not change it.</check>
    <check>phase0-inventory.md accounts for 100% of the ruling's
      concepts: each row names an existing interface or sits
      under REMOVED. Zero rows invent new machinery.</check>
    <check>Dry-trace introspection test passes: every seam-map
      interface imports and matches its documented signature, so
      the traced walkthrough is mechanically checked, not prose.
      (Live execution proof — the fix actually landing through
      these interfaces — is ruling Phase 2's acceptance, by
      design, not Phase 0's.)</check>
    <check>git diff shows no changes under src/attune/.</check>
  </validation>

  <risks>
    <risk severity="medium">Characterization can freeze accidental
      behavior as contract. Mitigation: the INTENTIONAL /
      INCIDENTAL tag on every pin.</risk>
    <risk severity="low">Fixture nondeterminism across OS.
      Mitigation: pure-stdlib fixture, no subprocess-executable
      fixtures, wait for Windows lanes before merge.</risk>
  </risks>
</task>
```

**Acceptance (ruling Phase 0):** the canonical scenario can be
traced through existing interfaces without requiring a parallel
registry, planner, executor, evidence store, lifecycle, or
source of truth.
