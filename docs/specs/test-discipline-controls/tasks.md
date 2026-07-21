# Tasks: Test Discipline Controls

> XML-enhanced execution prompts per
> [`.claude/rules/attune/xml-enhanced-prompts.md`](../../../.claude/rules/attune/xml-enhanced-prompts.md).
> Companion to [`requirements.md`](requirements.md) and
> [`design.md`](design.md).

**Status:** superseded (2026-07-20 — spec closed stale on premise;
see [requirements.md](requirements.md)). Previously parked
2026-06-09; the unimplemented tasks (coverage-gate hook, XML
`<branches>` schema, drift-guard tests) die with the closure. D5
("pre-push hook MUST run `--branch`") stays live policy via
CLAUDE.md.
**Last updated:** 2026-05-27
**Total estimate:** ~5.5h across 3 phases.

---

## Phase 1 — Coverage gate hook + docs alignment

### Task 1.1 — Resolve threshold SOTH + read current codecov target

```xml
<task id="1.1" name="threshold-soth">
  <objective>
    Inspect the current codecov configuration and pick the
    single-source-of-truth (SOTH) for the patch-coverage
    threshold. Write the chosen value into pyproject.toml's
    [tool.coverage.report] fail_under (per design.md leaning),
    or document why a different location is better.
  </objective>

  <context>
    <design-ref>design.md "Threshold: single source of truth"</design-ref>
    <decision-ref>decisions.md D2 (pending — this task resolves it)</decision-ref>
  </context>

  <files-to-read>
    <file path="codecov.yml">
      Source of truth for what CI enforces today.
    </file>
    <file path="pyproject.toml">
      Existing [tool.coverage.report] section if any.
    </file>
  </files-to-read>

  <files-to-modify>
    <file path="pyproject.toml">
      <change location="[tool.coverage.report]">
        Add or update fail_under to match codecov's patch-coverage
        target. Add a one-line comment naming this as the SOTH.
      </change>
    </file>
    <file path="docs/specs/test-discipline-controls/decisions.md">
      <change location="D2 entry">
        Resolve D2 with the chosen location + number + brief
        rationale. Stamp the date.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pyproject.toml's fail_under value matches codecov.yml's
    patch-coverage target.</check>
    <check>decisions.md D2 is no longer "PENDING".</check>
    <branches>
      <branches none-applicable="true" />
      <!-- Pure configuration update; no production code branches. -->
    </branches>
  </validation>
</task>
```

### Task 1.2 — Pre-push hook + helper scripts

```xml
<task id="1.2" name="pre-push-hook">
  <objective>
    Implement the pre-push coverage gate as a shell hook plus
    three Python helpers. Hook refuses pushes whose patch
    coverage falls below the SOTH threshold; PUSH_BYPASS_COVERAGE
    _GATE=1 bypasses.
  </objective>

  <context>
    <design-ref>design.md "Pre-push coverage gate"</design-ref>
    <existing-pattern path="src/attune/hooks/scripts/">
      Existing hook scripts (lessons_reminder, security_guard).
      Match this directory's conventions: stdlib-only when
      possible, shebang line, explicit `set -euo pipefail`.
    </existing-pattern>
  </context>

  <files-to-create>
    <file path="hooks/pre-push/coverage-gate.sh">
      Bash hook per design.md. Identifies touched src/ files in
      the push range, maps to test paths, invokes check_patch.py,
      exits non-zero on failure. Honours PUSH_BYPASS_COVERAGE_GATE.
    </file>
    <file path="scripts/coverage_gate/__init__.py">
      Empty marker so the gate scripts are an importable package
      for unit testing.
    </file>
    <file path="scripts/coverage_gate/read_threshold.py">
      Reads fail_under from pyproject.toml; prints integer; exits
      non-zero if missing.
    </file>
    <file path="scripts/coverage_gate/test_paths_for.py">
      Maps src/foo/bar.py to tests/unit/foo/test_bar.py with
      fallback to tests/unit/foo/. Idempotent on already-test
      paths. Handles deleted source files cleanly (drops them).
    </file>
    <file path="scripts/coverage_gate/check_patch.py">
      Runs `coverage run -m pytest <tests>`, parses coverage's
      JSON output, intersects with the touched-line set from
      `git diff @{push}..HEAD --unified=0`, computes patch
      coverage, exits non-zero if below threshold with the
      actionable error message from design.md UX section.
    </file>
    <file path="tests/unit/coverage_gate/test_read_threshold.py">
      Asserts read_threshold parses pyproject correctly; missing
      [tool.coverage.report] returns non-zero with clear stderr.
    </file>
    <file path="tests/unit/coverage_gate/test_test_paths_for.py">
      Round-trips: src/x/y.py → tests/unit/x/test_y.py; fallback
      to dir when exact file missing; already-test paths pass
      through; deleted-src files dropped.
    </file>
    <file path="tests/unit/coverage_gate/test_check_patch.py">
      End-to-end against a fixture mini-repo: tmp_path with a
      synthetic src + tests + git history; assert hook exits
      0 when coverage ≥ threshold; non-zero when below; bypass
      env var short-circuits.
    </file>
  </files-to-create>

  <validation>
    <check>Hook refuses a push whose patch coverage is below
    threshold (verified with fixture).</check>
    <check>Hook passes when patch coverage meets threshold.</check>
    <check>PUSH_BYPASS_COVERAGE_GATE=1 bypasses the check.</check>
    <check>Hook is a no-op when no src/**/*.py files changed.</check>
    <check>Error message names the missing line ranges with the
    "actions:" footer from design.md UX section.</check>
    <branches>
      <branch test="test_check_patch_below_threshold_exits_non_zero">below-threshold path</branch>
      <branch test="test_check_patch_above_threshold_exits_zero">happy path</branch>
      <branch test="test_check_patch_bypass_env_short_circuits">bypass env var</branch>
      <branch test="test_check_patch_no_src_changes_is_noop">no-touched-files path</branch>
      <branch test="test_check_patch_missing_threshold_errors_clearly">missing SOTH config</branch>
      <branch test="test_test_paths_for_falls_back_to_dir">missing test file fallback</branch>
      <branch test="test_test_paths_for_drops_deleted_sources">deleted-src filter</branch>
      <branch test="test_read_threshold_missing_section_exits_non_zero">missing pyproject section</branch>
    </branches>
  </validation>

  <risks>
    <risk severity="medium">
      `git diff @{push}..HEAD` requires an upstream to exist; on
      first push to a fresh branch, @{push} doesn't resolve.
      Mitigation: fall back to `git diff origin/main..HEAD` when
      @{push} is undefined; document in the hook header.
    </risk>
    <risk severity="low">
      coverage's JSON output format may shift between minor
      versions. Mitigation: pin coverage to >=7.x,&lt;8 in the
      [dev] extra (or wherever its already pinned) and assert
      the JSON shape in test_check_patch's fixtures.
    </risk>
  </risks>
</task>
```

### Task 1.3 — Hook installation via setup machinery + docs alignment

```xml
<task id="1.3" name="hook-install-and-docs">
  <objective>
    Wire the hook into the project's setup-hooks mechanism
    (opt-in per D3) and update the three doc files to quote the
    SOTH threshold. Add the drift-guard tests.
  </objective>

  <context>
    <decision-ref>decisions.md D3 (opt-in installation)</decision-ref>
    <existing-code path="src/attune/hooks/">
      Hook installer machinery — find the entry point that
      copies hooks into .git/hooks/ and add coverage-gate to its
      pre-push chain.
    </existing-code>
    <design-ref>design.md "Documentation alignment" + "Drift-guard tests"</design-ref>
  </context>

  <files-to-modify>
    <file path="src/attune/hooks/installer.py">
      <change location="pre-push hook chain (or equivalent)">
        Register hooks/pre-push/coverage-gate.sh as part of the
        pre-push chain. Idempotent install (don't double-add if
        already wired).
      </change>
    </file>
    <file path=".claude/rules/attune/coding-standards-index.md">
      <change location="'Minimum 80% test coverage' line">
        Replace with the SOTH-aligned wording. Reference the
        pre-push hook and the bypass env var.
      </change>
    </file>
    <file path="CLAUDE.md">
      <change location="Critical Rules section">
        Update coverage line to match SOTH; add one-line pointer
        to `attune setup hooks` (or equivalent) for the gate.
      </change>
    </file>
    <file path=".claude/python-standards.md">
      <change location="Target 90%+ test coverage line">
        Align to the SOTH; remove or update the "90%+" wording.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path="tests/unit/docs/test_coverage_bar_alignment.py">
      Reads pyproject.toml fail_under; greps the three doc files;
      asserts they all quote the same number. Fails CI on drift.
    </file>
    <file path="tests/unit/ci/test_codecov_alignment.py">
      Reads codecov.yml + pyproject.toml; asserts the patch-
      coverage target matches the SOTH. Skips cleanly if
      codecov.yml is absent in the working tree.
    </file>
  </files-to-create>

  <validation>
    <check>`attune setup hooks` (or equivalent) installs the hook
    into .git/hooks/pre-push.</check>
    <check>The three doc files quote the same threshold number
    that pyproject.toml's fail_under specifies.</check>
    <check>The drift-guard tests fail loudly if the doc strings
    diverge from the SOTH.</check>
    <branches>
      <branch test="test_coverage_bar_alignment_passes_when_synced">in-sync passes</branch>
      <branch test="test_coverage_bar_alignment_fails_on_doc_drift">doc drift detected</branch>
      <branch test="test_codecov_alignment_skipped_without_yml">codecov.yml-absent skip</branch>
      <branch test="test_codecov_alignment_fails_on_target_mismatch">codecov drift detected</branch>
    </branches>
  </validation>
</task>
```

---

## Phase 2 — XML-prompt template extensions

### Task 2.1 — `<branches>` schema + test-first section

```xml
<task id="2.1" name="xml-prompt-extensions">
  <objective>
    Extend the XML-prompt rule file with the new test-first
    guidance (Item 3) and the <branches> sub-element of
    <validation> (Item 5). Provide a worked example.
  </objective>

  <context>
    <design-ref>design.md "Test-first guidance" + "Branch-enumeration in <validation>"</design-ref>
    <existing-code path=".claude/rules/attune/xml-enhanced-prompts.md">
      Current template — extend, don't rewrite.
    </existing-code>
  </context>

  <files-to-modify>
    <file path=".claude/rules/attune/xml-enhanced-prompts.md">
      <change location="end of file or new ## section">
        Add the Test-first section per design.md. Add the
        <branches> schema description. Update the "Quick Example"
        block to demonstrate both (the security-guard-hook example
        gains a <branches> section).
      </change>
    </file>
    <file path="docs/guides/xml-enhanced-prompts.md">
      <change location="schema reference">
        Mirror the rule-file changes — the docs guide stays in
        lockstep with the rule file.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>The rule file has a "Test-first" section with the
    selective-application bullets from design.md.</check>
    <check>The rule file's <validation> schema includes
    <branches>.</check>
    <check>The quick example XML in both files now includes a
    <branches> sub-element.</check>
    <branches>
      <branches none-applicable="true" />
      <!-- Documentation update — no production-code branches. -->
    </branches>
  </validation>
</task>
```

### Task 2.2 — Decision-routine concerns palette: regression-guard required for `fix:`

```xml
<task id="2.2" name="regression-guard-required">
  <objective>
    Promote regression-guard from "use on bug fixes" to "required
    for any commit whose subject starts with fix:" in the
    concerns palette.
  </objective>

  <context>
    <design-ref>design.md "Regression-first for `fix:` commits"</design-ref>
    <existing-code path=".claude/rules/attune/decision-routine.md">
      Current concerns palette table. Update the regression-guard
      row's "When to include" cell.
    </existing-code>
  </context>

  <files-to-modify>
    <file path=".claude/rules/attune/decision-routine.md">
      <change location="concerns palette table, regression-guard row">
        Change the "When to include" cell to the wording in
        design.md "Regression-first for fix: commits". Keep the
        other rows untouched.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>The regression-guard row's text reads "Required for
    any commit whose subject starts with `fix:`..."</check>
    <check>No other palette rows changed (verified by diff).</check>
    <branches>
      <branches none-applicable="true" />
    </branches>
  </validation>
</task>
```

---

## Phase 3 — Drift-guard + self-application

### Task 3.1 — XML branches drift-guard test

```xml
<task id="3.1" name="xml-branches-drift-guard">
  <objective>
    Add the third drift-guard test that asserts every in-flight
    spec's tasks.md XML prompts include a <branches> section
    when they touch .py files.
  </objective>

  <context>
    <design-ref>design.md "Drift-guard tests" item 3</design-ref>
  </context>

  <files-to-create>
    <file path="tests/unit/docs/test_xml_validation_branches.py">
      Walks docs/specs/**/tasks.md AND docs/implementation/
      TASK_PROMPTS.md. For each <task> block: parse via stdlib
      ElementTree (XML-fragment-extraction from markdown);
      check if any <files-to-modify> or <files-to-create> path
      ends in .py; if so, assert <validation> contains either
      <branches> with at least one <branch>, or
      <branches none-applicable="true"/>.
      Skip task blocks in specs whose status is "retired",
      "paused", "done", or "complete".
    </file>
  </files-to-create>

  <validation>
    <check>Test passes against the current repo (all in-flight
    tasks already comply OR are exempt).</check>
    <check>Test fails if a new XML prompt touches a .py file
    without a <branches> section.</check>
    <check>Test skips correctly when a spec is marked
    retired/paused/done/complete.</check>
    <branches>
      <branch test="test_in_flight_spec_with_py_files_must_have_branches">required-section enforcement</branch>
      <branch test="test_branches_none_applicable_marker_is_accepted">explicit-opt-out path</branch>
      <branch test="test_retired_spec_is_skipped">status-skip path</branch>
      <branch test="test_doc_only_task_doesnt_require_branches">no-py-files path</branch>
    </branches>
  </validation>
</task>
```

### Task 3.2 — Self-application: backfill `<branches>` on this spec's own tasks

```xml
<task id="3.2" name="self-apply-branches">
  <objective>
    Verify this spec's own tasks (above) include <branches>
    sections that satisfy the drift-guard from Task 3.1.
    Verify the pre-push hook can run against this PR's diff.
  </objective>

  <context>
    <note>
      This is a verification pass, not new code. The XML prompts
      in this tasks.md should already include the <branches>
      sections — Task 3.1's test ensures they do.
    </note>
  </context>

  <validation>
    <check>tests/unit/docs/test_xml_validation_branches.py passes
    against this spec.</check>
    <check>The full pytest suite passes locally.</check>
    <check>The pre-push hook runs against this PR's diff without
    firing (because this PR doesn't touch src/**/*.py beyond
    scripts/coverage_gate/, which is covered by Phase 1's own
    test suite).</check>
    <branches>
      <branches none-applicable="true" />
      <!-- Self-verification only; no new code. -->
    </branches>
  </validation>
</task>
```

---

## Dependencies

```text
Task 1.1 (threshold SOTH) ─┐
                            ├── Task 1.2 (hook + helpers)
                            │
                            └── Task 1.3 (install + docs align + drift-guards)
                                  │
Task 2.1 (XML schema) ──────┐    │
                            │    │
Task 2.2 (regression-guard) ┤    │
                            │    │
                            ├──── Task 3.1 (xml branches drift-guard)
                            │            │
                            │            └── Task 3.2 (self-apply)
```

Phase 1 must complete before Phase 3 (the drift-guard needs the
SOTH wired). Phase 2 is independent of Phase 1 and can run in
parallel. Phase 3 depends on both 1 and 2.

---

## Out of scope (deferred)

- **Automated retrofit** of existing in-flight specs' tasks.md
  files to add `<branches>` sections. The drift-guard in Task 3.1
  fails on new specs only — existing specs are grandfathered via
  the `none-applicable` marker as they ship.
- **`commit-msg` git hook** that warns on `fix:` commits without
  a test file change. Stretch goal; not in this spec.
- **mypy / type-coverage gates.** Separate concern; mypy was
  removed from pre-commit per CLAUDE.md. Out of scope here.
- **Per-module coverage targets** (e.g. higher for security code).
  The single threshold simplifies the SOTH story; per-module
  tuning is a follow-up if the data shows it's needed.
