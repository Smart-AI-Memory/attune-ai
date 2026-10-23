# Agent work handoff

## Goal

Give the Attune Author reference its own page so it can leave the Harness Docs
flow without losing its content.

## Acceptance criteria

- `/attune-author/#attune-author` preserves the original section and anchor.
- The page identifies itself as an earlier project reference and links back to
  documentation.
- The destination builds on main before the Docs owner adds its concise link.
- Keep #2575's existing files and branch under their owner's control.

## Scope and assumptions

- Branch `docs/attune-author-reference`, website main `6695106f8`.
- Only the new Author page and this handoff; no source/export/release changes.
- Preserve the standalone package's archived status and original commands.
- Separate prerequisite draft; no merge, publication or deployment authority.

## Current state

Following Patrick's later Attune AI deprecation direction, the wrapper now
labels the retained installation command historical and directs new work to
Harness 1.5.1 preparation and current package availability in canonical Help.
It preserves existing environments and saved work, makes no migration-parity
claim and keeps the standalone attune-help reader distinct. The notice links
canonical Help without importing #2575's adapter, preserving this destination's
independent prerequisite build. The original section bytes remain unchanged.
This copy is a new validation phase; earlier receipts below remain historical.

The new page retains the exact original Author section from main's Docs page,
including `#attune-author`. A small wrapper adds reference context, one primary
heading, a documentation link and noindex metadata. The Docs owner will remove
its full inline block and retain a concise link after this destination is
committed and validated. No cross-owner file or branch writes occurred.

## Verification

Repository preflight passes all 87 governance checks using its existing Python
environment. The default system interpreter lacked pytest-xdist; that setup
failure is superseded by the configured-environment check, with no gate change.
Exact section preservation is recorded beside the clones in
`live-audit/author-preservation.json`: 1,940 bytes, SHA-256
`ef3183373161ea0453f17da04dc67f0e18b2e42cb2feae92188798e58b9d9990`.
The section also exactly matches the current Docs preview at `948ba152`.

78 website tests, targeted ESLint, pinned hooks and the main-based Next.js
production build/TypeScript pass (135 pages). HTTP 200, noindex, old anchor,
original command and back link pass. Actual browser rendered text exactly
matches the existing Docs block. At 390/320 CSS pixels there is no page-wide
overflow, one main/primary heading exists and local fragments resolve. The
keyboard skip link makes the next tab stop the documentation return link, with
visible three-pixel focus. Viewport override was reset afterward.

The first build rejected an out-of-root dependency symlink. A local copy of
the unchanged dependencies fixed that setup; a sandboxed compilation then
stalled and was stopped. The unchanged build with normal compiler access
passes. No code, configuration or assertion was changed for these setup
failures. Receipts and logs are beside the clones in `live-audit/author-*`.
These bounded checks do not establish full accessibility, independent-user
acceptance, hosted CI or production delivery. The standalone page inherits
main's existing Navigation/footer; the separate owner PRs supply their refresh.

## Next action

Send the committed destination's route/head to the Docs owner. Integrate this
prerequisite before #2575's layout link when
separately authorized. Validate the resulting combined Docs-to-Author journey;
retain earlier test receipts at their original inputs.
