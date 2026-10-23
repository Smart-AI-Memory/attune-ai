# Agent work handoff

## Goal

Make the historical 1.4.0 quick start available before current Docs links to it.

## Acceptance criteria

- `/harness/archive/1-4-0/#quickstart` builds against current main independently
  of the canonical publisher and release adapter.
- The original 4,538-byte historical section and bookmark remain identical.
- The page clearly identifies its archive status and links current Help.

## Scope and assumptions

- Branch: `docs/harness-140-archive`, main `6695106f8`.
- Separate Codex worktree; only the new archive page and this handoff.
- Canonical Help links are established routes. This branch makes no future
  1.5.1-delivery claim and imports no preparation metadata adapter.

## Current state

- Archive copied unchanged from the first #2579 commit `cb1955c16`.
- Historical JSX section exactly matches main
  `6695106f8a185e310b7b8f9d463395cb0752c22a`'s Docs section, 4,538 bytes;
  SHA-256 `3d9eb727c5e5f7e37e25e07366102261dfe1a4e5ff2df0b2c088380c8a670ba0`.
- Independent GPT-6 Astra review of the original combined change found no
  actionable code defect and identified the sequential-delivery dependency.
  The existing Docs owner independently verified exact archive bytes, noindex
  and the current-guide link.
- #2579 removes its new archive addition from its net diff by an ordinary
  follow-up commit. Original commit/content remain retained.

## Verification

Standalone main-based test/build, route and content results are recorded in the
draft PR. The earlier three-input combined validation does not qualify this
standalone draft by itself.

## Next action

Verify this standalone draft, then validate the final exact committed inputs
for this prerequisite, #2574, #2575 and revised #2579 in a separate disposable
tree. Dependency order is this archive and #2574 independently, then #2575,
then #2579. Main-triggered deployments therefore need no forward archive link.
Keep the PRs separate. No merge, publication, deployment or settings change is
authorized by this handoff.
