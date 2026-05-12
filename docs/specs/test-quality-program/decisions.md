# Per-module decisions — Test Quality Program

Append-only log. One section per module as it's worked. See
`requirements.md`, `design.md`, `tasks.md` for the framework.

Format per entry:

```text
## <module path>

**Date:** YYYY-MM-DD
**Rubric score at pick time:** <score> (weight × gap × risk)
**Picked because:** <one-line reasoning>
**Outcome:** <one-line summary — modules touched, bug classes, tests added/removed>
**PR:** <link>
**Bug log entry:** <link to COVERAGE_BUG_LOG.md section>

[Body: what stays, what got rewritten, what got deleted, and
why. Any surfaced production change deferred to a sibling PR.]
```

---

<!-- First entry lands here when task #8 ships. -->

## workflows/dependency_check.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.685 (weight=5 × gap=0.537 × risk=1.0)
**Picked because:** First entry with measured `covered_pct`
after `ops/cli.py` shipped. The 11 rows above it
(scores 4.0 / 3.0, `workflows/test_*.py` files) are
coverage-omit artifacts of the `*/test_*.py` pattern in
`pyproject.toml` — coverage never measures them, so the
rubric's `?` marker is informational, not a real gap.
**Outcome:** 1 test file added (`test_dependency_check_execute.py`,
21 tests). Coverage 41.67% → 100% line+branch. Zero
production bugs surfaced. Pattern is reusable for
sibling SDK-native workflows (`bug_predict`,
`perf_audit`, `refactor_plan`).
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — fourth module under test-quality-program"

The module is a thin async shell around
`claude_agent_sdk.query()`. The uncovered slice was
the entire `execute()` body (lines 127–166) and the
`_run_agent_check()` async loop (lines 180–229). The
only thing mocked in the new tests is `query()` itself;
the messages it yields are real
`claude_agent_sdk.AssistantMessage` and
`ResultMessage` dataclasses so the `isinstance()`
checks in `agent_sdk_adapter.collect_agent_output`
fire correctly (this avoids the trap documented in
CLAUDE.md: "Duck-typed test fakes fail
isinstance-based collectors silently"). Depth
mapping (quick=10 / standard=20 / deep=40), each
specific exception path (`ImportError`,
`ConnectionError`, `TimeoutError`, generic
`Exception`), and the empty-stream "No results
returned" fallback are all individually covered.

**Rubric refinement flagged (not done here):** the
`*/test_*.py` omit pattern hides four `workflows/test_*.py`
production modules from coverage entirely. Either the
pattern should tighten to `tests/test_*.py`, or the
rubric script should drop `?` covered_pct rows from
the working-set top. Surfaced as a follow-up; not in
scope for this PR.

## workflows/bug_predict.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.636 (weight=5 × gap=0.527 × risk=1.0)
**Picked because:** Top entry with measured `covered_pct`
after `dependency_check.py` shipped. Structurally
identical SDK-native shell — the test scaffold from
PR #265 transferred with a one-pass rename. The prior
decision entry explicitly flagged it as the next pick.
**Outcome:** 1 test file added (`test_bug_predict_execute.py`,
21 tests). Coverage 47.3% → 97% line+branch (only the
`if __name__ == "__main__"` guard at line 271 remains
uncovered, standard untestable boilerplate). Zero
production bugs surfaced. Two SDK-native shells now
through the program; `perf_audit` and `refactor_plan`
remain.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — fifth module under test-quality-program"

Same body shape as `dependency_check`: thin async shell
around `claude_agent_sdk.query()`, three subagents
(`pattern-scanner`, `risk-correlator`,
`prevention-advisor`), depth → max_turns mapping
(quick=10/standard=20/deep=40), specific exception
paths each producing a structured `_error_result`. Only
`claude_agent_sdk.query` is mocked; the messages it
yields are real `claude_agent_sdk.AssistantMessage` and
`ResultMessage` dataclasses so the `isinstance()`
checks in `agent_sdk_adapter.collect_agent_output` fire
correctly. No production changes; no sibling PR
needed.

**Reuse signal:** Two consecutive SDK-native cycles
shipped from the same test scaffold with single-pass
renames. The pattern is mature enough to script as a
per-workflow template (e.g. `scripts/scaffold_sdk_workflow_tests.py`
taking module path + subagent list as inputs). Flagged
for the next cycle to consider; not committed.

## workflows/perf_audit.py

**Date:** 2026-05-12
**Rubric score at pick time:** 2.606 (weight=4 × gap=0.651 × risk=1.0)
**Picked because:** Top entry with measured `covered_pct`
after `bug_predict.py` shipped. Third instance of the
SDK-native shell pattern — same scaffold transferred
verbatim with subagent + method-name renames.
**Outcome:** 1 test file added (`test_perf_audit_execute.py`,
23 tests including 2 for the inline `main()` CLI entry
point). Coverage 34.8% → 96% line+branch. Only line 281
(`if __name__ == "__main__"`) and one falsy-branch in
`main()` remain uncovered. Zero production bugs
surfaced. Three SDK-native shells now through the
program; `refactor_plan` remains.
**PR:** _(filled in after merge)_
**Bug log entry:** `docs/COVERAGE_BUG_LOG.md` —
"2026-05-12 — sixth module under test-quality-program"

Same body shape as the two prior SDK-native cycles
with one twist: `perf_audit.py` ships an inline
`main()` CLI entry point (lines 259-277) rather than
delegating to a sibling `*_report.py` module. Two
extra tests handle it — one happy path with a patched
`query()` yielding a `ResultMessage`, one error path
with `query()` raising `RuntimeError`. Both go through
`capsys` to assert the printed banner.

**Reuse signal (third consecutive cycle):** the test
scaffold is now demonstrably reusable across all
SDK-native shells. The remaining sibling
(`refactor_plan.py`) should be a one-pass rename. If
the inline-`main()` shape recurs there too, scripting
a generator becomes more clearly justified than
hand-renaming.
