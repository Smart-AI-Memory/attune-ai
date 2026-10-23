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

The generated receipt imports signed Harness commit
`fd42e9cb202fd3dbd3ea1fe87b6e9bd6ba814815`, which includes current Harness
main `e78576eda9b99369472f3f58f768230a4a2656c9`.
Help remains explicit 1.5.1 preparation; published 1.5.0 evidence is retained.
The current migration, release-notes and readiness links use documentation
revision `93f161b8e65bf86b4a7670e899ff96ff260644f1`. The original runtime
source, validation artifact, tutorial source and published verification records
keep their separate identities. The generated delta changes the preparation
page and metadata; importer and renderer implementations are unchanged.

The entry-point owner must use this refreshed export before changing the two
active migration links in PR #2575 to `docs/migration.md`. The historical 1.0
migration record is preserved. Keep all branches separate and based on main.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Committed source and exact export | Import full SHA, then `node scripts/harness-help-export.mjs check` | 12 pages, 24 files; pass |
| Website integration | All website tests, TypeScript and changed-file ESLint | 78 tests; pass |
| Production compilation | `npx next build` | Pass; 123 pages |

Independent GPT-6 Astra review found no actionable findings in the generated
four-file delta. All source/output hashes match. The original validation,
tutorial and historical verification identities are unchanged. A local HTTP
round trip verified all 24 exported files byte for byte, including the new
migration link. Combined entry-point validation remains with the PR #2575 owner.

## Next action

Read the PR body for final CI and HTTP/browser evidence. Keep the dependency
order: canonical #299 through main, regenerated publisher #2574, then entry
points #2575. Re-import the reviewed merged source before cutover and reconcile
the release record with the selected final artifact. Package publication and
website deployment require their separate approvals. Do not merge, publish,
change credentials or dispatch a workflow from this handoff.
