# Agent work handoff

## Goal

Make current website installation guidance consistently select published Harness 1.8.1 and reflect the completed Windows ARM64 experiments without broadening qualification claims.

## Acceptance criteria

- Homepage, Help, Docs, FAQ and Pricing agree on published 1.8.1.
- Help and training exports identify the same reviewed Harness source commit; historical evidence retains its versions and bytes.
- Windows guidance distinguishes published 1.8.1 with local pinned wheels, separate upstream development tests, and the remaining PyPI-only ARM64 installation blocker.
- Export integrity, website tests, lint, build and served-page checks pass.
- Completion review: recorded in the session’s private O-07 follow-through; the remaining opportunity is a release-to-website publication check.

## Scope and assumptions

- Branch/worktree: `codex/website-harness-181-current`; isolated website checkout owned by this task.
- Provider/session: Codex; independent read-only review within the configured session.
- Artifact tier: structured one-shot, paired with a canonical Harness documentation PR.
- Source content is maintained in Harness; this repository owns its website import and presentation.
- Deployment and merge await Patrick's approval. The earlier #2604 merge authorization applied only to that PR.

## Current state

- Status: content and local website validation complete; source PR #366 and website merge remain pending.
- Changed files: website release constants, homepage, Windows page, Help import expectations and generated exports.
- Decisions: preserve published packages, dependency pins, retained failures, archived guides and course qualification records.
- Dependency: merge Smart-AI-Memory/attune-harness#366 first, then re-import from its exact merged commit before website merge. The reviewed draft currently imports `04c2b32ca4ed8cc74d24503a3a0e2b94e8297733`.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Repository collaboration rules remain coherent | Existing project interpreter runs `scripts/collaboration_preflight.py` | 87 governance checks passed; separate local main is behind, current task branches from fetched origin/main |
| Changed website source passes lint | ESLint on all eight authored changed files | Passed |
| Current release and imports agree | Both export checkers and full website suite | 15 Help pages, 30 Help files and 92 training payload files; 121 tests passed |
| Production build succeeds | `next build --webpack` | Passed; 123 static pages, TypeScript checks complete |
| Install links reach current guidance | Browser: Home → Install, Docs current install link, Pricing → Windows | 1.8.1 displayed; install command pins 1.8.1; Windows results and limits visible; no page overflow at observed 1076px width |
| Old evidence retains its identity | Independent rebuild and byte comparison | 30 Help files match the source export; all 92 training payload files unchanged; twelve other Help pages only update their shared current-release sidebar |
| Independent content review | Read-only source/evidence review by separate configured session agent | No blocking findings after two stale navigation labels were corrected |

## Next action

Obtain Patrick’s approval for the paired PRs. Merge source #366 after its checks pass, refresh both website import receipts to that exact merged commit, rerun import and content checks, then obtain or act on explicit website merge authorization. Verify production afterward. No new package publication is needed.
