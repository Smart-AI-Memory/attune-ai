# Agent work handoff

## Goal

Publish Harness in practice with direct website and Help Center entrances.

## Acceptance criteria

Main navigation and footer expose Help Center and Learn Harness. Help features
the course. Lessons, reading views and downloads work on desktop and mobile.
Current, preparation and historical guidance remain distinct. Verify the
production routes and source identity after the existing Vercel Git deployment.
Completion review: pending for the production cutover.

## Scope and assumptions

- Owned branch: `codex/website-harness-learning`, based on attune-ai main
  `98c881be8f98432b2df713889ae9e98b5f007b23` (merged PR #2592).
- Structured one-shot integration: website files and this required handoff.
- Patrick explicitly assigned this chat ownership of the website PR and
  publication. Existing merge gates remain applicable.
- Keep the earlier tester preview checkout unchanged while it is in use.

## Current state

The website retains PR #2592's benefit-led copy, release adapter, FAQ and
canonical Help importer. Added training delivery, integrity checks and direct
entrances extend that merged work. Older overlapping drafts #2575, #2579 and
#2590 were not modified or closed.

Help and training import receipts currently name Harness source
`1ad347d7b4a87d93f08df99e5c1efb4ee748632a` (draft PR #340). Reimport the reviewed,
merged Harness source before production. Current package setup remains 1.6.0;
the six-lesson course is labeled 1.7.0 preparation.

## Verification

- Collaboration preflight: 87 governance tests passed; no failed checks. The
  standalone clone has no linked checkout of main (reported warning).
- Locked website dependencies installed with `npm ci --no-audit --no-fund`.
- Training import: 47 payload files; Help import: 15 pages, 30 total files.
- Website suite: 109 tests pass, including 26 training importer controls.
- Production Next 16.3.8 build, TypeScript and scoped ESLint pass. Pre-commit
  passes; no package runtime files changed.
- All 75 Help/training payload routes match their recorded SHA-256 hashes;
  two unknown routes return 404. Receipts bind the same source.
- Desktop main → Help → course → lesson 2 → reading view observed in the
  current-base production preview. The prior candidate passed 390px checks;
  fresh current-base mobile review is pending while Patrick uses the tester
  browser. Canonical course Help links leave a local preview for production.
- Read-only independent agent review identified and corrected the distinction
  between published installation and the course's separate 1.7 command setup,
  and an inaccurate merged-source word in the Help publishing guide.
- Production delivery: pending.

Local evidence: `/private/tmp/harness-website-publish-tests-final-20261105.log`,
`/private/tmp/harness-website-publish-build-reviewed-20261105.log`,
`/private/tmp/harness-website-publish-types-20261105.log`,
`/private/tmp/harness-website-publish-lint-final-20261105.log`,
`/private/tmp/harness-website-publish-route-receipt-20261105.json`.
These paths are local evidence, not portable attachments or deployment receipts.

## Next action

Complete current-base verification and publish this branch as a draft PR.
After Harness PR #340 clears CI and Patrick merges it, reimport that exact
merged source. Complete website review and applicable merge gates, then verify
the deployed main → Help → course journey and imported file hashes.
