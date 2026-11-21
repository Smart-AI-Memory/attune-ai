# Agent work handoff

## Goal

Mark Attune AI deprecated and direct new work to Attune Harness 1.5.1 without
another Attune AI maintenance or package release.

## Acceptance criteria

- The README opens with a deprecation notice and the exact replacement version.
- The install command is conditional on 1.5.1 publication.
- Existing instructions, runtime, dependencies and published artifacts remain
  available; no migration parity or saved-data conversion is claimed.

## Scope and assumptions

- Branch: `codex/deprecate-attune-ai`, based on current `origin/main`.
- Two-file documentation change: README notice and this handoff.
- The separate website and Harness owners retain their existing PRs.

## Current state

The notice is prepared. A live PyPI query returned HTTP 404 for Harness 1.5.1;
Attune AI 16.4.0 is published and its index project status is `active`.
PyPI archival is an owner action; no archive, merge or publication is performed
by this PR. Keep the GitHub repository writable for its hosted website work.

## Verification

| Claim | Probe | Result |
| --- | --- | --- |
| Existing README is preserved | Remove the inserted notice and compare with main | Byte-identical |
| Install target is truthful | Check exact command and publication condition; query PyPI 1.5.1 | Conditional command present; index returned 404 |
| Repository checks remain intact | Collaboration preflight and pinned pre-commit | 87 checks and applicable hooks passed |
| Guide target exists | Read the linked installation file at Harness main | Existing installation guide |

Runtime and package suites are outside this documentation-only retirement
change. No dependency or CI repair was attempted.

## Next action

Review the small notice PR. Publish and verify Harness 1.5.1 before following
its install command; complete the separate PyPI archive action when authorized.
