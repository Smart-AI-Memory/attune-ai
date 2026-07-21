# Design: Test Discipline Controls

> Concrete shapes for the four mechanical controls in
> [`requirements.md`](requirements.md). Pairs with
> [`tasks.md`](tasks.md) for the execution prompts.

**Status:** superseded (2026-07-20 — spec closed stale on premise;
see [requirements.md](requirements.md))
**Last updated:** 2026-07-21

---

## Threshold: single source of truth

Per [`decisions.md`](decisions.md) D2 (pending), the leading
candidate is `pyproject.toml`:

```toml
[tool.coverage.report]
fail_under = 90  # patch-coverage gate enforced by pre-push hook
                 # and by codecov.yml's status.patch.target
```

Phase 1 verifies that codecov.yml can be configured to read this
value (or that we accept a tiny static-config duplication with a
drift-guard test).

The number itself is determined by inspecting codecov's current
config. If codecov enforces 90% patch coverage today, we encode
90%. If it's looser, we tighten. If it's tighter, we loosen.
The goal is alignment, not raising the bar arbitrarily.

---

## Pre-push coverage gate

### Hook file

`hooks/pre-push/coverage-gate.sh` — bash script invoked by the
git pre-push hook chain.

```bash
#!/usr/bin/env bash
# Pre-push: refuse if patch coverage on touched src/ files
# falls below the configured threshold.
#
# Override: PUSH_BYPASS_COVERAGE_GATE=1 git push ...

set -euo pipefail

# Honour the explicit-bypass env var.
if [[ "${PUSH_BYPASS_COVERAGE_GATE:-}" == "1" ]]; then
    echo "coverage-gate: bypass requested via PUSH_BYPASS_COVERAGE_GATE=1"
    exit 0
fi

# Identify changed Python files in the push range.
# `@{push}` is the upstream tip; HEAD is what we're about to push.
TOUCHED=$(git diff --name-only "@{push}..HEAD" -- 'src/**/*.py' 2>/dev/null || true)
if [[ -z "$TOUCHED" ]]; then
    # No production code changes — gate is a no-op.
    exit 0
fi

# Map src/foo/bar.py -> tests/unit/foo/test_bar.py (with fallback to
# tests/unit/foo/ if the exact test file doesn't exist).
TEST_PATHS=$(python scripts/coverage_gate/test_paths_for.py $TOUCHED)

THRESHOLD=$(python scripts/coverage_gate/read_threshold.py)
# Runs coverage + computes patch coverage on the diff.
python scripts/coverage_gate/check_patch.py \
    --files "$TOUCHED" \
    --tests "$TEST_PATHS" \
    --threshold "$THRESHOLD"
# Exit code: 0 if patch coverage >= threshold; non-zero otherwise.
```

### Companion Python helpers

Three small scripts under `scripts/coverage_gate/`:

| File | Purpose |
|---|---|
| `read_threshold.py` | Reads the threshold from the SOTH (pyproject.toml). Single line of Python; exits with the integer printed. |
| `test_paths_for.py` | Maps `src/foo/bar.py` → `tests/unit/foo/test_bar.py`. Falls back to `tests/unit/foo/` if the exact file is absent. Idempotent on already-test paths. |
| `check_patch.py` | Runs `coverage run -m pytest <tests>`, parses `coverage report -m` output, computes patch-coverage (lines touched ∩ lines covered / lines touched), exits non-zero if below threshold. Prints which lines are uncovered. |

### Installation

The hook is **opt-in** per D3. Wire-up via the existing
`attune setup hooks` machinery (or the equivalent). The setup
command copies `hooks/pre-push/coverage-gate.sh` into
`.git/hooks/pre-push` (or chains it if one already exists).
Contributors who never run setup don't get the hook; CI is
unaffected (CI doesn't push, it merges).

### Error message UX

When the gate fires:

```text
coverage-gate: patch coverage 84.5% below threshold 90%
 missing lines:
   src/attune/curator/cache.py:109-111  (mkdir failure path)
   src/attune/curator/cache.py:123-124  (write failure path)
   src/attune/curator/sources/telemetry.py:188  (5xx int status)

 actions:
   - add tests covering the lines above, OR
   - PUSH_BYPASS_COVERAGE_GATE=1 git push  (emergencies only)
```

Concrete and actionable. The agent reading this should be able to
write the missing tests without re-running coverage to find them.

---

## Documentation alignment

Three files quote the coverage bar:

1. `.claude/rules/attune/coding-standards-index.md`
2. `CLAUDE.md` (project root)
3. `python-standards.md` (loaded via `@./python-standards.md` from
   `.claude/CLAUDE.md`)

All three get updated to quote the same number as the SOTH. A
drift-guard test under `tests/unit/docs/` parses each file, grep
the codecov/pyproject SOTH, and fails if any disagree.

---

## XML prompt template extensions

### Test-first guidance (Item 3)

New section appended to
`.claude/rules/attune/xml-enhanced-prompts.md`:

````markdown
## Test-first for new-API modules

When a task creates a **new module with a public API** (e.g., a
fresh package's first source file, a dataclass + Protocol layer,
a public-facing service class), list the test file BEFORE the
implementation file in `<files-to-create>` and add this note:

```xml
<files-to-create>
  <file path="tests/unit/foo/test_bar.py" order="first">
    Write the test file as a contract assertion BEFORE the
    implementation. The tests document the public API; the
    implementation makes them pass.
  </file>
  <file path="src/attune/foo/bar.py" order="second">
    Implement to satisfy the tests above.
  </file>
</files-to-create>
```

Apply selectively:
- ✅ new public API of a new module / package
- ❌ modifications to existing modules — write tests after, check
  coverage diff
- ❌ internal helpers, refactors, formatting changes
- ❌ single-file edits, bug fixes (use `regression-guard` instead)

The reason this isn't universal: TDD's value comes from design
pressure on the API. When there's no new API, there's no design
pressure to capture. Forcing test-first on every task is the
strict-TDD model rejected in `decisions.md` D1.
````

### Branch-enumeration in `<validation>` (Item 5)

The existing `<validation>` block schema grows a `<branches>`
sub-element:

```xml
<validation>
  <check>functional happy-path assertion</check>
  <check>another functional check</check>
  <branches>
    <branch test="test_X">except OSError on iterdir</branch>
    <branch test="test_Y">data not a dict</branch>
    <branch test="test_Z">empty input → empty return</branch>
  </branches>
</validation>
```

Rules for the agent:

- Every `except` clause added by the task gets a `<branch>` line.
- Every `if not X: return` / `if X is None: return` early-out
  added by the task gets a `<branch>` line.
- Every meaningful malformed-input path (json decode failure,
  unicode error, type coercion failure) gets a `<branch>` line.
- Each branch names the test function that exercises it.

If a branch in the production code doesn't have a corresponding
`<branch>` entry, the task isn't done — write the test and add
the line. This is the structural pressure that closes the
happy-path-only failure mode at authoring time.

---

## Regression-first for `fix:` commits

Update `.claude/rules/attune/decision-routine.md` — the existing
concerns palette table — to promote `regression-guard` from
"optional" to "required when subject starts with `fix:`":

```markdown
| `regression-guard` | **Required** for any commit whose subject
starts with `fix:`. Optional for other concerns. A regression test
that fails on the pre-fix code and passes on the post-fix code is
the only proof the fix is real. |
```

No code change for v1 — this is documentation. The
`commit-msg` git hook (stretch goal) could parse the message and
warn if no test file is in the same commit, but the wording is
strong enough that human review catches violations.

---

## Drift-guard tests

Three new tests under `tests/unit/docs/` and `tests/unit/ci/`:

1. **`tests/unit/docs/test_coverage_bar_alignment.py`** — parses
   the SOTH (pyproject.toml `fail_under`) and asserts the value
   appears verbatim in the three doc files. Detects future drift.
2. **`tests/unit/ci/test_codecov_alignment.py`** — parses
   `codecov.yml` and asserts its patch-coverage target matches
   the SOTH. (Skips with a clear `pytest.skip()` if codecov.yml
   isn't present in the working tree, which is the case for
   sibling-repo checkouts.)
3. **`tests/unit/docs/test_xml_validation_branches.py`** — finds
   every XML prompt in `docs/implementation/TASK_PROMPTS.md` and
   `docs/specs/**/tasks.md` (only for spec status: in-flight /
   approved) and asserts each has a `<branches>` section if it
   touches `<files-to-modify>` or `<files-to-create>` for `.py`
   files. Allows opt-out via a `<branches none-applicable="true"
   />` marker for refactor-only tasks.

These tests are part of the regular suite — they'd fail in CI if
someone bumps codecov's threshold without updating docs, or vice
versa. Drift becomes a CI failure, not a slow-drift surprise.

---

## Self-application

The PR that lands this spec uses every control on itself:

- The pre-push hook installs and runs against the PR's own diff.
- The drift-guard tests are in the same commit set as the
  doc-alignment changes — proving they catch drift if either side
  moves without the other.
- The XML prompts in [`tasks.md`](tasks.md) include the new
  `<branches>` sections.
- The PR's commit messages demonstrate the `regression-guard`
  pattern (the drift-guard tests ARE the regression guards
  against future drift).

---

## What this spec doesn't do

- **No automated `<branches>` linter for retroactive specs.** The
  existing 30+ in-flight specs don't get retrofitted automatically;
  they're updated lazily as their tasks ship.
- **No required `commit-msg` hook.** The hook chain stays
  minimal — pre-push is the structural one; commit-msg is too
  invasive for v1.
- **No CI rejection of low-coverage PRs.** Codecov already does
  this. Adding a redundant gate would be friction without
  benefit.
- **No "type coverage" gate.** mypy / pyright coverage is a
  separate concern (and already broken — see CLAUDE.md "mypy
  removed from pre-commit"). This spec touches only test
  coverage.

---

## Cross-references

- [`requirements.md`](requirements.md) — problem statement,
  goals, acceptance criteria
- [`decisions.md`](decisions.md) — TDD-rejection rationale +
  pending threshold-SOTH decision
- [`tasks.md`](tasks.md) — XML-prompt execution plan
- [`.claude/rules/attune/xml-enhanced-prompts.md`](../../../.claude/rules/attune/xml-enhanced-prompts.md) — template this spec extends
- [`.claude/rules/attune/decision-routine.md`](../../../.claude/rules/attune/decision-routine.md) — concerns palette this spec extends
