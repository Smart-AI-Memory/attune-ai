# Harness Help publisher handoff

## Goal

Serve the Harness-owned Help export at the existing public URLs with one
canonical content owner and an inspectable source receipt.

## Acceptance criteria

Preserve the twelve Help pages, goals controls, assets and historical bookmarks.
Check exact exported bytes and the real Next.js routes before cutover.

## Scope and assumptions

- Branch: `codex/harness-help-150`, PR #2574.
- Canonical Help: merged attune-harness PR #299. This branch publishes its export.
- Website entry points and current copy remain with their original owners.
  Release metadata and package preparation are separate.

## Current state

The generated receipt imports signed canonical merge
`013b84a6d1984f388df41452299ddacc90bb5f5b`. GitHub confirms its tree
`6e048e0dacc3a718533ce0255a265d04eedb39fe` exactly matches reviewed and
tested Help head `3073eb4a7fde625649b05f19007599b837d2e282`.

The latest generated update changes only the source commit and URL in
`import.json`. The other 23 files, including build metadata, pages, commands,
controls, preparation data and historical evidence, are byte-identical.
Documentation still pins reviewed `0dc82db327af9eae41f7bf812480cc76d2cd7fc7`;
behavior, validation and tutorial identities remain distinct. Help remains
explicit 1.5.1 preparation with published 1.5.0 available.

The earlier six-file correction aligns four walkthrough introductions with
Get started's preparation source. Its resolved review and independent approval
remain bound to that correction. Historical 1.0 migration and 1.5.0 observations
remain unchanged.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Merged canonical source | GitHub PR/commit signatures and tree comparison | Merged; verified signatures; exact tested-tree match |
| Current export | Fresh exact-commit import and exporter check | 12 pages, 24 files; only import receipt changes |
| Delivered receipt | HTTP comparison with regenerated file | 200; exact source commit, build hash and bytes |
| Unchanged content | Compare all other generated files with parent | 23 byte-identical files |
| Prior website checks | Publisher `4feebc0a` tests/types/lint/build/HTTP | 78 tests; 123-page build; all 24 files served exactly |

The prior GPT-6 Astra review verifies all source/output/renderer hashes for the
unchanged content. No test suite or build was repeated for this receipt-only
update; current hosted CI remains its own gate. Later combined website copy
changes need their owners' exact-input delivery checks.

## Next action

Read the PR body for current CI, dependency and combined-delivery evidence.
Canonical #299 is merged; keep publisher #2574 before entry-point #2575.
Preserve the separate archive, navigation and Author wrapper lanes.

The merged-source import gate is closed for canonical Help. Final release
source/artifact reconciliation and cutover qualification remain open. Package
publication and website deployment need their separate approvals. This handoff
authorizes no merge, publication, credential/settings change or manual workflow.
