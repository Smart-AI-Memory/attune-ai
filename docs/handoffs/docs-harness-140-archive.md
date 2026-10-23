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

Standalone runtime/page inputs at `59ddfa95` pass 78 website tests, TypeScript
and the 135-page production build, targeted lint, pinned pre-commit, and archive
plus existing-guide HTTP 200 checks. Exact archive-section comparison passes.

Final combined inputs are archive #2580 `59ddfa95`, publisher #2574 `dcaa5f05`,
Docs #2575 `948ba152` and revised entry points #2579 `d21e1c6e`. Fresh 78 tests,
TypeScript/124-page build, lint, 12-page/24-file export check, 31 HTTP checks and
the actual browser current/archive journey pass. The Help owner independently
replayed all 31 HTTP checks and that browser journey. Later handoff-only edits
do not change the validated runtime/page bytes. Hosted checks and production
remain separate.

## Next action

Keep the verified final disposable preview at `http://127.0.0.1:8871/docs/`
available for Patrick. The sibling `website-four-input-validation` checkout and
`live-audit/four-input-validation.json` retain the exact inputs and results.
Dependency order is this archive and #2574 independently, then #2575, then #2579. Main-triggered deployments therefore need no forward archive link.
Keep the PRs separate. No merge, publication, deployment or settings change is
authorized by this handoff.
