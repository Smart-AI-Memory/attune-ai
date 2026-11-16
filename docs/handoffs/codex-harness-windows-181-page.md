# Agent work handoff

## Goal

Give Windows users a public Harness 1.8.1 compatibility guide that distinguishes
tested configurations from remaining validation work.

## Acceptance criteria

- Add `/harness/windows/`, a homepage link and a sitemap entry.
- Preserve package-version, operating-system and interpreter boundaries in every
  test claim, with links to the source evidence.
- Verify the production build, website tests and desktop/mobile presentation.
- Commit the change and open a website PR. Merge and deployment remain separate.
- Completion review: complete for the page and commit preparation; see the
  decisions and open questions below. Verify the remote PR after creation.

## Scope and assumptions

- Branch/worktree: `codex/harness-windows-181-page`, isolated attune-ai worktree.
- Provider/session: Codex; independent read-only evidence review completed.
- Artifact tier: structured one-shot, bounded to the compatibility page and its
  discoverability. No Harness runtime change or new Windows qualification.
- Starting commit: `49ab13944570481d3392e76965b045685f1eb3c5`; fetched `origin/main`
  matched this commit before branch creation.
- The user authorized the commit and website PR on November 16, 2026.

## Current state

- Status: page implemented and locally verified; prepared for commit and PR.
- Changed files: `website/app/harness/windows/page.tsx`, its `page.module.css`,
  `website/app/page.tsx`, `website/app/sitemap.ts`, and this handoff.
- Decisions: exact published 1.8.1 Windows Server results remain separate from
  published 1.8.0 desktop runs and the earlier Parallels fix candidate. ARM64
  hardware with x64 Python is distinct from native ARM64 Python.
- Source identity: Harness `f2baa8b1f9c0acaab2109cbc7facfb029c596586`, with the
  published wheel hash and release-check links on the page.
- Risks or open questions: a fresh published-1.8.1 Windows 11 walkthrough and
  Windows browser inspection remain open. Native ARM64 binary-only installation
  is blocked by the retained dependency pins; source builds and runtime remain
  unqualified. Timeout recovery and broader integrations remain separate work.
- Completion review: no distinct new opportunity emerged during commit
  preparation. The existing homepage release notice and imported Help bundle
  still identify 1.8.0. Users encounter those setup links first; reconciliation
  requires the normal Help export/import process, with live routes and artifact
  identities checked together. Do not patch generated version strings alone.
  This note does not authorize that follow-up or publication.

## Verification

All website commands ran from `website/`. `ATTUNE_PYTHON` selected an existing
Python environment containing the project's test dependencies.

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Production route builds | `npx next build` and inspection of the prerender manifest | Passed; 123 static pages, including `/harness/windows` |
| Changed TypeScript passes lint | `npx eslint app/harness/windows/page.tsx app/page.tsx app/sitemap.ts` | Passed |
| Existing website behavior remains covered | `npm test` with `ATTUNE_PYTHON` configured | 121 tests passed across 15 files |
| Generated imports remain consistent | `node scripts/harness-help-export.mjs check` and `node scripts/harness-training-export.mjs check` | Both passed; imported files unchanged |
| Page is readable and reachable | Local production preview in Mac Chrome, desktop and 390 × 844 viewport; homepage navigation and keyboard table scrolling | Passed; narrow-screen scrolling hint and visible focus verified |
| Document structure is usable | Inspect generated HTML for heading, fragment and ID integrity | One H1; eight unique IDs; local fragments resolve |
| Repository governance checks pass | `python scripts/collaboration_preflight.py` with the configured repository Python | 87 tests passed |
| Claims preserve evidence limits | Independent read-only review against retained release evidence and source links | No blocking findings; breadcrumb and mobile-scroll improvements incorporated |

The first website test attempt lacked `claude_agent_sdk` in the default Python;
selecting the existing configured environment resolved it without code changes.
The browser checks above are Mac website checks, not Windows acceptance tests.

## Next action

Open and verify the PR for this branch, then review its diff and CI results before
any separate merge/deployment decision. Remove this temporary handoff when the
branch is merged, following the repository's handoff convention.
