# Harness Help publisher handoff

## Goal

Serve the Harness-owned Help export at the existing public URLs with one
canonical content owner and an inspectable source receipt.

## Acceptance criteria

Preserve the twelve Help pages, goals controls, assets and historical bookmarks.
Check exact exported bytes and the real Next.js routes before cutover.

## Scope and assumptions

- Branch: `codex/harness-help-150`, PR #2574.
- Canonical Help: attune-harness PR #299. This branch only publishes its export.
- Website entry points: PR #2575. Release metadata and package preparation are
  owned separately. Do not copy their work into this branch.

## Current state

The generated receipt imports Harness commit
`d668d02a1cc3618696dc97ad26bd9c99077686f3`, which includes current Harness
main `5fca534972ac3904c6aa92a0a0fd89e7cf9ba4a9`.
Help remains explicit 1.5.1 preparation; published 1.5.0 evidence is retained.
The refreshed export changes only the source commit receipt; rendered bytes
and the importer's reviewed implementation are unchanged.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Committed source and exact export | Import full SHA, then `node scripts/harness-help-export.mjs check` | 12 pages, 24 files; pass |
| Website integration | All website tests, TypeScript and changed-file ESLint | 78 tests; pass |
| Production compilation | `npx next build` | Pass; 123 pages |

## Next action

Read the PR body for final CI and HTTP/browser evidence. Keep the dependency
order: canonical #299 through main, regenerated publisher #2574, then entry
points #2575. Re-import the reviewed merged source before cutover and reconcile
the release record with the selected final artifact. Package publication and
website deployment require their separate approvals. Do not merge, publish,
change credentials or dispatch a workflow from this handoff.
