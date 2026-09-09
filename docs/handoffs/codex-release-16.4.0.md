# Agent work handoff

## Goal

Execute attune-ai 16.4.0 publication, authorized by Patrick through
release-execute after the reviewed version preparation. The prior 16.3.0 check stopped
because that version is already published; Patrick explicitly selected 16.4.0.

## Acceptance criteria

- All maintained package/plugin/docs/website version sites declare 16.4.0.
- The lockfile changes only the root package version; dependencies stay locked.
- The 16.4.0 changelog retains the unreleased entries and README history.
- Version/documentation gates and wheel/sdist metadata and clean-install checks pass.
- Before tagging, rerun attune-release-check against the actual merged SHA,
  including fresh PyPI/tag availability and main CI on that exact SHA.

## Scope and assumptions

- Branch/worktree: `codex/release-16.4.0`, `/private/tmp/attune-release-16.4.0`.
- Base: `ff968cc649937b7b2e2ed9bec255e03d593dc775` (merged cleanup #2500).
- Structured one-shot release execution; Codex integrates, a different-model
  advisory lane reviewed release and lock changes. Completion requires PyPI
  wheel and sdist visibility plus a clean installation of the published version.
- Existing main checkout is dirty and was not changed. No GitHub release,
  version tag or PyPI publication has been created by this preparation.

## Current state

- `scripts/bump_version.py 16.4.0` updated its 10 maintained files.
- Pinned uv 0.9.22 updated only the attune-ai root version in uv.lock and
  installed a fresh development environment with the locked dependencies.
- Unreleased entries were promoted to 16.4.0 (2026-09-09); the README's single
  current-release slot changed, with the 16.3.0 content preserved in details.
- Explicit release notes should come from the promoted changelog section.
  The existing release workflow's awk extraction was observed to emit only
  the heading before trimming; its fallback is a Git-log summary. This
  preparation does not change that workflow.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Requested version is unused | Live PyPI JSON plus `git ls-remote --tags origin refs/tags/v16.4.0` | Version absent; tag absent at preparation time |
| Version and docs agree | 8 focused version/plugin/website/changelog/README gate files | 121 passed |
| Changelog categories and README links are valid | Consolidator check for Unreleased and 16.4.0; README anchor checker | Passed |
| Both artifacts build and have valid metadata | Pinned uv build; twine check | Wheel and sdist passed |
| Installed artifacts carry 16.4.0 and retained surfaces | Separate wheel/sdist venvs outside checkout; release_artifact_smoke.py with inference guard active | Both passed, resolving from site-packages |
| Artifact memory works without local project state | Exact wheel recall gate from empty cwd and isolated HOME | hit@3 3/3 |
| Authored projections are current | Projector dry run and timestamp-normalized comparison | 341 help and 124 docs outputs match; no structural findings; not a prose accuracy audit |
| Reviewed hooks are packaged unchanged | Byte comparison of all three installed hook scripts against source in both smoke environments | All six comparisons passed |

Different-model release/lock review approved the diff without findings.
Post-change preflight passed all 87 governance tests; the dirty main checkout
was preserved. Pinned pre-commit hooks passed. The live PyPI simple index
still reports 16.3.0 as latest; 16.4.0 is absent. GitHub currently permits
tag deployments with no branch restriction; its pypi reviewer gate remains.

Explicit release notes: `/private/tmp/attune-16.4.0-release-notes.md`.
Artifacts: `/private/tmp/attune-16.4.0-dist/`. Smoke runner:
`/private/tmp/attune-16.4.0-run-smoke.py`. These are local evidence, not
published artifacts. The live Claude SessionStart harness remains outside
these receipts, as documented in the hook reliability report.

## Next action

Finish the reviewed release-preparation PR. After its merge, verify main CI
on the full merge SHA and repeat attune-release-check before tagging. The
PyPI environment approval remains Patrick's own Actions UI click. Delete
this handoff when the branch merges.
