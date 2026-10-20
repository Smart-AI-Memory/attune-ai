# PR #2538 lock metadata repair

Goal: make the existing manifest-only dependency PR export its locked CI
constraints without changing resolved dependency packages.

Original PR head: `6b44eb32d635072b88baeedfa89f30f8848d607e`. Patrick authorized publishing this bounded repair for review, normal Vercel
previews and fresh CI. Merge, auto-merge enablement and production remain held.

## Change

Regenerated `uv.lock` with CI-pinned uv 0.9.22, retained the original
`exceptiongroup` package record to omit unrelated marker normalization, and
kept only the 1 root-project metadata row(s) matching `filelock` in
the existing `pyproject.toml`. All 189 dependency package records are identical
to this PR head. The lock contains 190 package records including the project.
The repair does not exercise newly permitted major dependency versions.

## Verification

- Original `uv export --locked --all-extras --no-emit-project --no-hashes`
  failed because the lock needed updating, matching hosted Linux/Windows logs.
- Repaired export with the same pinned tool passed.
- `uv lock --offline --check` passed.
- TOML comparison preserved every nonproject package record, including versions,
  dependency edges, artifact URLs and hashes.
- `git diff --check` passed. No product or test source was modified.

## Remaining

Publish this narrow repair to the existing branch. Before a push, re-read the
remote head and preserve concurrent work. Patrick approved the two normal
Vercel previews and hosted CI; no additional model call is authorized. PR #2538's pre-existing auto-merge request
was disabled during shepherding to respect the current merge hold.
Full fresh hosted CI is pending. No credentials/settings, model calls, security
bypass, thresholds or exclusions were changed. Merge remains held.
