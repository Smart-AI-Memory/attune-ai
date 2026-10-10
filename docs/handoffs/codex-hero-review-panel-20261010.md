# Hero panel draft handoff

## Goal

Help a homepage visitor understand the path from an idea to a result they
can review. Prepare the approved replacement right hero panel for review.

## Acceptance criteria

- Use Patrick's approved heading and three steps exactly.
- Preserve the left hero and existing visual style.
- Link **See the walkthrough** only to a verified, appropriate public
  walkthrough of one task across the steps. Omit the CTA if none qualifies.
- Test the built page, lint, accessibility and responsive behavior.
- Deliver screenshots and a local preview; do not push, merge or deploy.
- Completion review: complete; private local draft records the content gap.

## Scope and assumptions

- Branch: `codex/hero-review-panel-20261010`.
- Base: `5e11cb025b605d7a6c1725024baf517a9dc8369e`, verified against
  GitHub `origin/main` on October 10, 2026.
- Own isolated clone and worktree under the current Codex task directory.
- Only product source changed: `website/app/page.tsx`.
- Approved private writing policy revision:
  `e6e53f6a092deb4536b63bc8609c2453a20e5a53`, read through GitHub.
- No edit to the Harness checkout or its live walkthrough.

## Current state

- Draft only. The approved copy replaces the abstract scope/authorize/check
  panel. Existing CSS, left hero and all other page source are unchanged.
- The panel is a named `aside` with an explicit list role. Decorative
  numbers remain hidden from assistive technology.
- Removed the former illustrative-workflow caption.
- The CTA is omitted. Public `/how-it-works/` and the Fix sandbox describe
  earlier Attune AI behavior. The released Harness 1.3.0 CLI guide has a
  plan/build starter, but does not present a complete result-review
  walkthrough matching this panel's promise. Help Center PR2552 remains
  open and is not a released destination.
- Active Help Center and dependency lanes were read and left untouched.
- Local preview: `http://127.0.0.1:3217/`, retained in Codex's browser.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Source isolation and policy checks | Existing-venv collaboration preflight | 87 governance tests passed; clone-main warnings only |
| Production page compiles and types check | `npx next build --webpack` | Passed; 117 static pages; existing Edge Runtime warning |
| Changed page is lint clean | `npm run lint -- app/page.tsx` | Passed |
| Existing capability accuracy | Vitest `test/capabilities-accuracy.test.ts` with existing Python | 3 passed |
| Existing website version accuracy | Pytest `test_website_version_accuracy.py`, current `src` | 16 passed |
| Approved panel and unchanged left hero | Built-page DOM plus source comparison outside the card | Exact copy; outside-card source byte-identical |
| Responsive reflow | Built-page browser at 320, 390, 760, 768, 1024, 1440 pixels in light/dark | 12 cases; no horizontal overflow or clipped card text |
| Accessible presentation | Named aside, list role, hidden numbers, computed contrast | List exposed; body text 6.54:1 light and 7.05:1 dark |
| Keyboard access | Tab to skip link | Visible 3px focus outline |
| No dead CTA | Built card link count | Zero links |
| Browser errors | Browser console inspection | No captured warnings/errors |

Local evidence is in the task directory's `review/`: production build log,
test logs, browser JSON, keyboard JSON and desktop/mobile JPG screenshots
in both themes. These files are not a hosted deployment or an independent
review. The direct Next build avoided static docs regeneration and the
production indexing hook, neither of which is relevant to this copy edit.

## Next action

Review the draft and screenshots. If publication is later approved,
recheck current `origin/main` and active website lanes, apply this bounded
change, run the publication checks, then publish through the normal flow.
Treat adding a CTA as a separate content decision after its destination
actually demonstrates the promised journey.
