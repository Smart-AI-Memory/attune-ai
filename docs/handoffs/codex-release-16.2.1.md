# Agent work handoff

## Goal

Publish attune-ai 16.2.1 from the main-branch merge of the strict dynamic-form
payload fix and the release-gate parser fix.

## Acceptance criteria

- Every governed source version site and `uv.lock` agree on 16.2.1.
- The existing post-merge docs-sync job updates the served framework-docs
  artifact to 16.2.1, and the deployed page is checked before tagging.
- The changelog promotes the two fixes from `[Unreleased]` into 16.2.1.
- The release-prep PR passes all required CI checks and merges.
- The final tag targets the verified full post-sync `main` SHA that contains
  both the release-prep merge and the generated docs-sync commit.
- PyPI's simple index exposes both the 16.2.1 wheel and source distribution.

## Scope and assumptions

- Branch/worktree: `codex/release-16.2.1` at
  `/private/tmp/attune-ai-release-16.2.1`
- Provider/session: Codex local session, 2026-09-03
- Assumptions:
  - The release is a patch because `[Unreleased]` contains fixes only.
  - Patrick's zero-spend instruction remains active: do not call paid model
    APIs or run AI-backed release workflows until separately authorized.
  - The dirty original `main` checkout is left untouched; all release work
    stays in this isolated worktree.

## Current state

- Status: no-cost release preparation is locally complete; SDK-backed workflow
  calls remain prohibited by the zero-spend instruction.
- Changed files: governed version projections, `CHANGELOG.md`, `README.md`,
  `uv.lock`, and this handoff.
- Decisions:
  - Target version is 16.2.1.
  - PR #2394 merged at
    `3fda0611429e83ad5defb6208398f26166a15b93` before this branch was created.
  - The release commit was rebased onto the unrelated spec-only #2395 merge
    before push.
- Risks or open questions:
  - `secure-release` and `release-notes` are SDK-backed and have not run. Their
    deterministic substance is being reproduced locally and will be labeled
    Codex/manual rather than reported as workflow execution.
  - The first `release-prep` attempt reported 40% coverage after pytest stopped
    before emitting `TOTAL`; that value was a heuristic, not a measurement, and
    is invalidated by the complete coverage receipt below.
  - PR #2375 overlaps only `CHANGELOG.md`; it remains intentionally outside this
    release. Re-check the overlap immediately before opening the release PR.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Fix PR is merged from a fully green required-check set. | `gh pr checks 2394 --required` and `gh pr view 2394 --json state,mergeCommit` | Pass: required checks green; merged at full SHA `3fda0611429e83ad5defb6208398f26166a15b93`. |
| Release branch started from current main. | `git rev-parse HEAD origin/main` before edits | Pass: both were `3fda0611429e83ad5defb6208398f26166a15b93`. |
| 16.2.1 is not already on PyPI. | Query `https://pypi.org/simple/attune-ai/` | Pass: latest artifact is 16.2.0. |
| Lockfile refresh is scoped. | `git diff -- uv.lock` | Pass: only the editable attune-ai version changed. |
| Version projections agree. | Focused plugin/website version consistency tests. | Pass: 5 tests. |
| README's historical Roundtable measurements are reproducible. | The two named seven-candidate workspace tests plus independent arithmetic. | Pass: 7 items complete in 3 submissions (`3 + 3 + 1`); submissions reduce 57.143% (`7 -> 3`) and added navigation reduces 66.667% (`6 -> 2`). |
| README rotating release slot is current. | `tests/unit/scripts/test_check_badge_freshness.py` | Pass: 5 tests. |
| Full-suite coverage clears the release floor. | `ATTUNE_REDIS_MOCK=true uv run --frozen pytest --cov=attune --cov-report=term-missing -x -q --no-header --timeout=30` | Pass: 25,264 passed, 259 skipped, 3 xfailed; measured total 95.30%. |
| Deterministic documentation projection is current. | `uv run --frozen python scripts/list_stale_help_features.py --help-dir .help --project-root .` | Pass: empty stdout, meaning no stale features. |
| Deterministic release team approves. | `release-prep` in simulated mode, empty Anthropic key, zero budget. | Pass: 4/4 agents, high confidence, recorded cost $0.00. |
| Separately named release gate approves. | `release-gate` in simulated mode, empty Anthropic key, zero budget. | Pass: 4/4 agents, high confidence, recorded cost $0.00. |
| Security scan matches CI scope. | `uv run --frozen bandit -c .bandit -r src/ attune_software/ --severity-level medium --confidence-level medium` | Pass: 156,680 lines scanned; 0 medium and 0 high findings. |
| Changed files satisfy local hooks. | Pinned `pre-commit run --files ...` over all changed files. | Pass: all applicable hooks. |
| Final artifacts are valid. | Fresh `uv build`, then Twine-check wheel and sdist. | Pass: both artifacts; wheel SHA-256 `5b304f7f11650736a3d2cac115808251196e748f485f52a23b8d3cc0beb17f8b`, sdist SHA-256 `fde2fc27f6846c2144a298f37f9144c9eeeeda0b6b28bd801fbcc95f78f1708c`. |
| Built metadata contains the corrected release surface. | Inspect the wheel's `METADATA`. | Pass: version 16.2.1 and the `New in 16.2.1` form-improvement section are embedded. |
| Installed wheel exposes the intended behavior. | Install the final wheel in a fresh venv; run `attune version` and both intake modules from `/private/tmp`. | Pass: `attune-ai 16.2.1`; 2 valid payloads, 0 null values, 3 Fix fields and 4 Spec fields. |
| Source documentation builds. | `uv run --frozen mkdocs build --strict` | Pass. A local sync exposed broad generated-asset churn, so that output was reverted and publication is gated on the repository's existing post-merge docs-sync job instead. |
| A different model reviewed the release diff. | Read-only release-risk review plus disposition review. | One P1 found: the served API-reference artifact remains 16.2.0 until docs sync. Resolution accepted: wait for and verify the post-merge docs-sync deployment, then tag the full post-sync `main` SHA; do not commit a 283-file toolchain-churn rebuild into this patch PR. |

## Next action

Push and open the release-prep PR, then wait for required CI. After merge, wait
for the docs-sync job and verify the served 16.2.1 page before tagging. Do not
cross the SDK-backed workflow boundary.
