# Refresh the Harness 1.7.0 website imports

## Goal

Bring the Help Center and six-lesson course in attune-ai #2593 onto the same
merged Harness source for published 1.7.0.

## Acceptance criteria

Both exports name the same merged commit and match canonical bytes. The website
identifies 1.7.0 as published and keeps the preparation walkthroughs in the
archive. Refusal controls detect mismatched release metadata and payload drift.

## Scope and assumptions

This candidate extends website #2593 head
`5af1febb87a2e6e68f49d060ae94b61e5afa3c04` on
`codex/refresh-harness-170-website`. It uses Harness #344's merged source at
`e889c0c1625b51d9d401469b09b362ceeb955bc6`.

## Current state

The local candidate updates the release links and course copy, refreshes both
exports through their importers, and checks publication against the committed
Help manifest before importing training. The Help reference remains 1.5.1.

The unresolved Code Quality comment points to an intentional single commit
message split across two literals in the canonical `practice.py` at lines 69–70.
The imported bytes match the canonical helper. The PR owner can explain the
intent in the thread or request an upstream formatting change, then refresh both
exports from the successor merge commit. Hosted delivery, mobile walkthrough and
independent learner observation remain open.
[Code Quality thread](https://github.com/Smart-AI-Memory/attune-ai/pull/2593#discussion_r4488453476)

## Verification

| Claim | Probe | Result |
| --- | --- | --- |
| Both imports reproduce their canonical payloads | Run both export scripts with `import` against `e889c0c`, compare each complete directory with `diff -qr`, and run both scripts with `check`. Help rendered with Markdown 3.10. | 15 Help pages and 30 files including receipts, 47 training payload files, both directories identical to fresh imports. |
| Older source cannot claim published 1.7.0 training | Run the training import against former source `1ad347d7b4a87d93f08df99e5c1efb4ee748632a`. | Refused its published 1.6.0 manifest before output creation. |
| The website still builds and passes its tests | Run `npm test`, scoped ESLint, `tsc --noEmit --incremental false`, and `next build` on Next 16.3.8 with the API key empty. | 111 tests passed, lint and types passed, and Next built 123 static pages. |
| The production build serves the reviewed bytes | Compare the response SHA-256 against the receipts for each Help and training payload on loopback. | 75 hashes match. Learn redirects to the course, two unknown routes return 404, and Home, Docs and Pricing show 1.7.0. |

## Next action

Review the local successor and integrate it into #2593 through its owner. Update
the PR description with the merged source identity and verification. Check the
hosted preview, then verify the public paths and hashes after authorized delivery.
