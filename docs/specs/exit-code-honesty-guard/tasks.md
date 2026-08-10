# Exit-Code Honesty Guard — Tasks

**Status:** draft (2026-08-10) — awaiting chair approval of
[design.md](design.md); implementation authority begins at that
gate. Sized as one small PR (impl + tests together — the diff is
one module and one new test file).

## T1 — Guard the post-result steps (impl)

In `src/attune/cli_commands/_exit_codes.py`: add the
`_post_result_step` helper (D-1) and route all three post-result
steps through it — `_emit_json_result`, `print_result`,
`on_result`. Remove `on_result`'s now-redundant local try/except.
`exit_code` is computed before the steps and returned
unconditionally after them. No behavior change on the
pre-result exception paths (exit 2 / exit 3 branches untouched).

**Receipt (suite):** full `tests/unit/cli_commands/` +
`tests/unit/cli/test_workflow_commands_run_meta.py` run SERIALLY,
exact tail recorded.

## T2 — R3 drift-guard test (regression-guard)

New `tests/unit/cli_commands/test_exit_code_honesty_guard.py` per
the design's test matrix: three injected-raiser hook points ×
{success→0, planned-failure→1}, stderr warning asserted, and the
execute()-raises case still returning 2.

**Receipt (behavioral):** red-before/green-after — run the new
test against the pre-T1 module (expect failures on the unguarded
hook points), then post-T1 (expect pass); both tails recorded in
decisions.md per the acceptance criteria.

## T3 — #1904 suite unchanged (regression-guard)

`tests/unit/cli/test_workflow_commands_run_meta.py` and
`tests/unit/ops/test_run_meta_stdout.py` pass UNCHANGED — no
edits to those files in the PR diff (acceptance criterion:
"the #1904 regression suite continues to pass unchanged").

**Receipt (suite):** serial run tail + `git diff --stat` showing
neither file touched.

## T4 — Record and close (release-notes)

decisions.md entry: chair's design ruling (incl. Q1/Q2 answers
D-3/D-4 — adopted or amended), the T2 red/green receipts, and the
status flip to complete. CHANGELOG entry under Unreleased
(user-visible: post-success plumbing failures no longer corrupt
the exit code; stderr warning added). Spec headers status-truthed
in the same PR.

## Explicitly deferred

- MCP `_workflow_response` invariant (D-4) — reopen trigger
  recorded in design.md.
- Run-record annotation for chronic-breakage visibility (D-3) —
  reopen trigger recorded in design.md.
