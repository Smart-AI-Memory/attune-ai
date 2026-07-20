# Spec: Test Discipline Controls

> Four mechanical controls that close the test-coverage discipline
> gap surfaced by PR #485 — without adopting strict TDD.
**Status:** draft (2026-05-27) — in review
**Created:** 2026-05-27
**Owner:** TBD
**Related:**

- [PR #485](https://github.com/Smart-AI-Memory/attune-ai/pull/485) — surfaced the gap (89% local coverage, codecov flagged 6 modules below patch-coverage gate)
- [`.claude/rules/attune/coding-standards-index.md`](../../../.claude/rules/attune/coding-standards-index.md) — current "Minimum 80%" rule
- [`.claude/rules/attune/xml-enhanced-prompts.md`](../../../.claude/rules/attune/xml-enhanced-prompts.md) — XML prompt schema this spec extends
- [`.claude/rules/attune/decision-routine.md`](../../../.claude/rules/attune/decision-routine.md) — concerns palette this spec extends

---

## Problem statement

PR #485 shipped with 89% line coverage on Phase 1 of bulletin-curator.
The coding standards say 80% is the floor, so on paper the work was
compliant. Codecov's patch-coverage gate disagreed and flagged six
modules below threshold. Two distinct issues collided:

1. **The agent's working pattern produced happy-path-only tests.** Tests
   came AFTER production code, exercised success paths, and stopped
   at "green." Error branches (`except` clauses, `if not X: return`
   early-outs, malformed-input handlers) were systematically
   under-tested. The pattern hit ~89% reliably and felt "done."
2. **The repo's stated bar is below the enforced bar.** CLAUDE.md
   says "Minimum 80%" but codecov flags <90% on patches. Agents
   reading the docs target 80%; CI rejects them. The doc and the
   gate disagree, and the gate is the load-bearing one. The agent
   only learns this AFTER pushing and reading codecov.

The cost wasn't catastrophic (we caught it in PR review, added
tests, lifted coverage to 100%). But the failure mode is recurring
and structural — *every* agent-written PR on a fresh module set
will hit the same shape unless the controls change.

Strict TDD adoption was considered and rejected (see [Decision: not
TDD](decisions.md)). The cost-per-value of red-green-refactor with
an AI agent in the loop is high (2-3× more tool calls per task,
plus AI-faithfulness verification overhead on the "did the red
phase actually run" step). Cheaper, more mechanical controls
address the same failure mode at lower cost.

---

## Goals

1. **Pre-push coverage gate.** Make it impossible to push code with
   patch coverage below threshold without explicitly overriding —
   the check fires on the developer's machine, not 7 minutes later
   in CI.
2. **Documentation/enforcement alignment.** The stated coverage bar
   in CLAUDE.md and the codecov enforcement gate must agree.
   Whichever way the alignment lands, agents reading the rules
   should be targeting the same number CI enforces.
3. **Selective test-first for new-API modules.** When a task creates
   a brand-new module with a clear public surface, write the test
   file *first* — the test file IS the API contract. This
   captures TDD's design-pressure benefit at exactly the moment it
   pays off, without imposing it on internal/refactor work where
   it doesn't.
4. **Regression-first required for `fix:` commits.** The existing
   `regression-guard` concern (in the decision-routine concerns
   palette) becomes required, not optional, for any commit whose
   subject starts with `fix:`. The fix doesn't go in without a
   test that fails on the pre-fix code and passes on the post-fix
   code.
5. **Branch-enumeration in XML `<validation>` blocks.** Strengthen
   the XML-prompt template so `<validation>` lists every error
   branch added and which test exercises it. Surfaces gaps at
   authoring time, not at codecov time.

## Non-goals

- **Adopting strict TDD as policy.** See `decisions.md`. The four
  controls in this spec address the same failure mode at lower
  cost without the AI-verification problem TDD introduces.
- **Raising the bar to 100%.** 100% coverage is a poor target —
  it rewards testing trivial branches and dead defensive code. A
  realistic target is 90-95% patch coverage with the branch-
  enumeration habit catching meaningful gaps.
- **Replacing CI's coverage gate.** The pre-push hook is a *local*
  fast-feedback control; CI stays the authoritative gate. The
  push hook just moves the signal forward in time.
- **Blocking workflow / agent-development specs.** This spec ships
  alongside ongoing work; no in-flight spec gets blocked by it.

---

## Design

### Item 1 — Pre-push coverage gate

A git `pre-push` hook (opt-in via project settings) that:

- Detects which `src/attune/**/*.py` files are in the push range
  (commits between `@{push}` and `HEAD`).
- Runs `coverage run -m pytest <targeted-tests>` over the matching
  `tests/unit/` paths.
- Computes patch coverage (lines in the diff that were exercised
  during the run vs total touched lines).
- Refuses the push with a clear message if patch coverage falls
  below the configured threshold (default 90%).
- Provides a one-time override (`PUSH_BYPASS_COVERAGE_GATE=1`) for
  emergencies and infrastructure-only commits.

The hook lives at `.claude/hooks/pre-push/coverage-gate.sh` (or
equivalent) and is wired into `.git/hooks/pre-push` via the
project's existing hook-installer machinery.

### Item 2 — Documentation alignment

Two files change to match codecov's actual enforcement:

- `.claude/rules/attune/coding-standards-index.md` — replace
  "Minimum 80% test coverage" with the explicit codecov-aligned
  number (likely "Minimum 90% patch coverage on new/modified
  modules; 80% line coverage as the long-running floor").
- `CLAUDE.md` (project root) — same alignment, plus a one-line
  pointer to the pre-push hook setup.

The exact number is set by inspecting codecov's current config
during Phase 1; whatever it is, the docs match.

### Item 3 — Selective test-first for new-API modules

Add a new section to `xml-enhanced-prompts.md`:

> **Test-first when the task creates a new module with a public
> API.** For these tasks, the XML prompt's `<files-to-create>`
> block lists the test file BEFORE the implementation file, with
> a note that the test file should be written and committed first
> as a contract assertion. Subsequent commits implement the
> contract.

This is guidance, not enforcement. Apply selectively per the
decision routine — single-file edits, internal helpers, and bug
fixes don't qualify.

### Item 4 — Regression-first for `fix:` commits

Promote `regression-guard` from "use on bug fixes" (current
status: optional concern in the palette) to "required for any
commit whose subject line starts with `fix:`."

Mechanism: extend the existing decision-routine concerns palette
in `.claude/rules/attune/decision-routine.md` with the
required-when condition. Optionally add a `commit-msg` git hook
that warns (not blocks) when a `fix:` commit lands without a test
file change in the same commit — but this is a stretch goal, not
required for the spec.

### Item 5 — Branch-enumeration in `<validation>` blocks

Extend the XML-prompt template's `<validation>` block schema:

```xml
<validation>
  <check>existing functional check</check>
  <branches>
    <branch>except OSError on iterdir — covered by test_X</branch>
    <branch>data not a dict — covered by test_Y</branch>
    <branch>empty input → empty return — covered by test_Z</branch>
  </branches>
</validation>
```

Force the agent to enumerate the new error branches per task with
the test that exercises each. The cost is ~30 seconds per task;
the benefit is the gap becomes visible at authoring time.

---

## Acceptance criteria

1. **Coverage gate fires locally.** A staged commit with patch
   coverage <90% blocks `git push`; the message names the modules
   and line numbers that are missing. Override env var bypasses
   cleanly.
2. **Docs match enforcement.** `.claude/rules/attune/coding-
   standards-index.md` and `CLAUDE.md` both quote the same number
   codecov enforces. Demonstrate by adding a drift-guard test:
   `tests/unit/docs/test_coverage_bar_alignment.py` parses the
   codecov config + greps the docs and fails if they disagree.
3. **Test-first guidance lands in `xml-enhanced-prompts.md`.** The
   new section is present, references the decision routine, and
   includes an example XML prompt where the test file precedes the
   implementation file.
4. **Regression-guard required for `fix:` commits.** Updated
   concerns palette in decision-routine.md. The change is
   documentation — no enforcement code required for v1 — but the
   wording is clear enough that a reviewer can call out missing
   regression tests in `fix:` PRs.
5. **`<validation>` blocks gain a `<branches>` section.** Schema
   updated, example XML prompts in `TASK_PROMPTS.md` retrofitted
   to demonstrate. Drift-guard test asserts every task in the
   existing spec library that's marked "in-flight" has a
   `<branches>` section.
6. **Self-application.** PR that lands this spec uses the new
   controls on itself: branch-enumerated `<validation>` blocks for
   each task, pre-push hook validates the push, regression test
   verifies the alignment-drift-guard.

---

## Tasks (overview)

Detail in [`tasks.md`](tasks.md). Phased:

- **Phase 1** — Coverage gate hook + docs alignment (3h)
- **Phase 2** — XML-prompt template extensions (1.5h)
- **Phase 3** — Drift-guard tests + self-application (1h)

Total: ~5.5h. Each phase ships independently.

---

## Open questions

1. **Where does the threshold live as a single source of truth?**
   Three candidates: (a) codecov.yml — already the load-bearing
   gate; (b) `pyproject.toml [tool.coverage.report] fail_under` —
   already in our tooling; (c) a new `.claude/coverage-bar.json`
   that both the hook and docs read. Lean: (b), because it's
   already on the box and tools respect it natively.
2. **Hook installation: opt-in or default-on?** Lean opt-in via
   the project's existing settings.json mechanism — forcing a hook
   onto every contributor's machine is heavy-handed and breaks
   non-developer worktrees (CI runners, ephemeral build agents).
3. **What about `feat:` commits that ship without tests because
   the feature is a refactor / dead-code-removal?** Lean: the
   coverage gate's role is to ensure *new* code is covered.
   Removing code can't fail the gate by definition. Refactors of
   existing code that don't add new lines also can't fail (no
   new patch to cover). The hook should be self-resolving for
   these cases.
