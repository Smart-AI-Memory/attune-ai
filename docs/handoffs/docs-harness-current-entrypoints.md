# Agent work handoff

## Goal

Send current Harness readers to canonical Help and preserve the 1.4.0 quick
start in an explicit archive.

## Acceptance criteria

- Navigation and the how-it-works Help action open `/harness/help/`.
- Pricing uses canonical preparation/publication metadata and links the current
  Quick Start, rather than recommending the old 1.4.0 installation.
- `/harness/archive/1-4-0/#quickstart` preserves the original instructions.
- #2575's owner retains Docs, FAQ, homepage, footer, sitemap and release adapter.

## Scope and assumptions

- Branch: `docs/harness-current-entrypoints`, based on website main `6695106f8`.
- Session: Codex, separate checkout; no cross-owner branch writes.
- Dependencies: #2574 supplies the canonical export; #2575 supplies its release
  adapter. Integrate those through main and revalidate before merging this draft.
- Preparation remains unpublished. PyPI's fresh JSON reports 1.5.0, no 1.5.1.

## Current state

Patrick subsequently directed deprecation of Attune AI in favor of Harness
1.5.1, rather than further routine dependency or feature maintenance. The
Pricing and How it works notices now state that direction, retain existing
environments and saved work, and make no feature-parity or automatic-migration
claim. How it works and Pricing consume the existing canonical release notice;
no publication flag changes here. Navigation already points to canonical Help.
The standalone attune-help reader is a separate project. The new copy is a
separate validation phase; the historical receipts below retain their inputs.

- Three website files changed: Navigation, pricing and how-it-works. This
  handoff is the fourth tracked change. The archive now belongs to a separate
  main-based prerequisite so #2575 can link it before this adapter-dependent PR.
- The separate archive prerequisite retains the exact 4,538-byte JSX block from main
  `6695106f8a185e310b7b8f9d463395cb0752c22a`'s `website/app/docs/page.tsx`.
  SHA-256: `3d9eb727c5e5f7e37e25e07366102261dfe1a4e5ff2df0b2c088380c8a670ba0`.
- #2575's owner agreed to replace the active Docs block and point the top Quick
  Start action to `/harness/help/get-started/`, keeping `#quickstart` as a short
  current notice with an explicit archive link. That change remains its lane.
- Canonical Help, generated assets, original screenshots and historical
  projections are unchanged here. No release identity is manually flipped.

## Verification

Validation uses a disposable complete checkout of publisher `dcaa5f05f`, the
eight committed #2575 inputs from `948ba1522`, and the original four website files
from `cb1955c16`. After review exposed the delivery order, the archive was
extracted unchanged into its own prerequisite. Final four-input validation passed with archive #2580 `59ddfa95`, publisher
#2574 `dcaa5f05`, Docs #2575 `948ba152` and this PR runtime/page inputs
`d21e1c6e`: 78 tests, TypeScript/124-page production build, targeted lint,
12-page/24-file export check and 31 HTTP checks. The Help owner independently
replayed the 31 HTTP checks and actual current/archive browser journey. Later
handoff-only edits do not change the validated runtime/page bytes.
This is a test combination, not a branch integration or production deployment.

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Existing website behavior preserved | `npm test` with the configured Python registry interpreter | 78 tests pass |
| New pages and adapter compile | Next.js 16.3.8 production build | 124 pages generated; TypeScript passes |
| Canonical export preserved | `node scripts/harness-help-export.mjs check` and byte comparisons through real rewrites | 12 pages / 24 export files verified |
| Changed files follow repository formatting | Targeted ESLint, pinned pre-commit and whitespace checks | Pass |
| Routes and published baseline agree | 31 localhost HTTP checks, including canonical payload bytes and unknown-topic 404 | Pass |
| User-facing links reach the intended guides | Actual browser Docs → Quick Start → compatibility anchor → archive; Navigation → Help → Get started | Pass; 1.5.1 preparation and published 1.5.0 fallback visible |
| Historical block survives | Exact UTF-8 substring comparison and SHA-256 | Pass |

The first scratch `git archive` omitted required export-ignored repository
inputs and failed before useful validation. The complete committed-checkout
rerun above passes. No source, deadline or assertion was changed to clear that
setup failure. The full Attune AI Python suite, Vercel deployment, production,
full accessibility certification were not run for this bounded copy/link
change. The standalone draft needs its unmerged adapter/export dependencies.

Follow-up on the same four runtime inputs: at 390 and 320 CSS pixels, Docs and
the archive have no page-wide overflow; historical code scrolls locally. The
mobile menu opens/closes with Enter, exposes expanded state and reaches Help by
keyboard, with a visible three-pixel focus outline. Archive skip-link tab order,
PowerShell disclosure and local fragments pass bounded checks. This does not
establish full accessibility, screen-reader or independent-user acceptance.
The receipt is `live-audit/mobile-accessibility-preview.json` beside this clone.
No unchanged full suite was rerun. Chrome's visible Harness preview tab and a
fresh visible in-app tab both render `/docs/#quickstart`; the server is healthy.
The original parent-link blank-page cause is unproven.

## Next action

Final combined source is retained in the local `website-four-input-validation`
checkout beside this checkout and served at `http://127.0.0.1:8871/docs/`.
The receipt is in the sibling `live-audit/four-input-validation.json`. Keep that
preview available for Patrick; it is a disposable local combination.

Integrate the separate archive-only prerequisite #2580 and #2574 independently, then
#2575, then update this draft normally and rerun the real link journey on the
resulting head. This avoids #2575 linking an archive supplied only by a later
adapter-dependent PR. Separate merge and publication approvals remain
required. This draft is outside the named Harness release shepherd sequence.
