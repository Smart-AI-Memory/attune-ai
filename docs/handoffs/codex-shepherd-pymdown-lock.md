# PR #2539 lock metadata repair

## Goal

Make the existing manifest-only dependency PR export its locked CI constraints
without changing resolved dependency packages.

## Acceptance criteria

Pinned locked export and lock check pass; dependency records stay identical;
fresh hosted checks are inspected without bypassing failures or merging.

## Scope and assumptions

- Original PR head: `523b2160cacdaac3b0f4a4a72d349d1786965c6c`.
- First published repair: `b8820337df2e08d8e7c7b4ef544dd03eb878c10b`.
- Patrick approved publication, normal Vercel previews and fresh CI.
- Merge, auto-merge enablement, production and new model calls remain held.

## Current state

The lock repair changes only root-project metadata matching the existing
manifest. All 189 dependency package records remain identical. Newly permitted
major dependency versions were not exercised.

The first published head installed and ran tests. The first observed lane
reported macOS Python 3.11: 1 failed, 26,492 passed, 285 skipped, 6 expected failures.
Its failure was the handoff corpus check: this added document lacked required
template headings. This follow-up corrects that structure without changing
product code, lock contents, tests, gates or assertions. First results are
retained in task evidence.

Both first-head previews succeeded. Dependency audit fails on the unchanged
MCP 1.29.1 pin, CVE-2026-59951; no ignore or pin change was made. The separately
held MCP upgrade remains outside this publication. Native auto-merge and both
helper labels are absent; dependency paths exclude the docs-only merge lane.

## Verification

- Original pinned locked export failed before the metadata repair.
- Repaired uv 0.9.22 locked export and offline lock check passed.
- TOML comparison preserved every nonproject package record.
- Applicable pinned pre-commit hooks and 87 governance cases passed before
  first publication. Full first-head hosted results were not all terminal.
- The local handoff corpus check reproduces the first-head failure; the
  corrected document passes all five unchanged handoff corpus tests.

## Next action

Verify the handoff correction locally, sign and publish its bounded follow-up,
then monitor fresh exact-head CI and previews to terminal outcomes. Re-read
remote heads before pushing; preserve concurrent work. Retain the MCP audit
failure and all merge/production holds.
