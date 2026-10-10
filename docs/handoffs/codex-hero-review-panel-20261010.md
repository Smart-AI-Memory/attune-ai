# Homepage and footer draft handoff

## Goal

Help a visitor understand the path from an idea to a result they can review,
then reach the existing public resources through working links.

## Acceptance criteria

- Use Patrick's approved right hero heading and three steps exactly.
- Preserve the left hero and existing visual style.
- Link **See the walkthrough** only to a verified public walkthrough of one
  task across those steps. Omit the CTA if none qualifies.
- Match the footer column headings to the footer brand's size, weight and
  letter spacing, retaining `h3` semantics and Patrick's requested labels.
- Audit homepage navigation, footer, CTAs and resource links; fix verified
  failures using existing destinations. Distinguish unavailable services
  from missing pages or anchors and browser handoff behavior.
- Deliver tested local previews and screenshots. No push, merge or deploy.
- Completion review: complete for both milestones. The private local draft
  retains CR-HERO-01 and adds CR-HERO-02 for external fragment checks.

## Scope and source

- Branch: `codex/hero-review-panel-20261010`.
- Base: `5e11cb025b605d7a6c1725024baf517a9dc8369e`, verified against
  GitHub `origin/main` on October 10, 2026.
- Own isolated clone and worktree under the current Codex task directory.
- Saved hero commit: `53dc9080dc6ddd34f2dd75df59e824fa7d792652`.
- Product source: homepage, docs and pricing pages; Footer component and
  its new CSS module. Docs/pricing changes correct the same broken PyPI
  fragments identified during the homepage audit.
- Approved private writing policy revision:
  `e6e53f6a092deb4536b63bc8609c2453a20e5a53`, read through GitHub.
- Harness live walkthrough and Help Center publication lane are untouched.
  No Help Center destination was implicated in the fixes.

## Draft behavior

The approved hero is a named `aside` with an explicit list role and hidden
decorative numbers. Its entire section remains byte-identical to the
saved hero commit. Existing left hero copy and style are preserved.

The CTA is omitted. Public `/how-it-works/` and the Fix sandbox describe
earlier Attune AI behavior. The released Harness 1.3.0 CLI plan/build
starter does not show a complete visitor-facing result-review walkthrough
matching the panel's promise. Help Center PR2552 was open at inspection;
a draft lane does not establish public availability or walkthrough fit.

The footer's two column headings previously computed to 32px with uppercase
text and negative letter spacing, while the brand computed to 20px. They
now read **Attune Harness** and **Resources and References** at 20px, weight
700, line height 28px and normal letter spacing, matching the footer brand.
The existing colors, column layout, link labels and `h3` hierarchy remain.

Six PyPI links across `/`, `/docs/` and `/pricing/` had missing anchors.
The published release page prefixes these IDs with `user-content-`.
The draft corrects the installation, qualification and agent-setup
fragments to those existing IDs. Production still has the former URLs
until a later approved publication.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Draft compiles and types check | `npx next build --webpack` | Passed; 117 static pages; existing Edge Runtime warning |
| Changed TSX is lint clean | ESLint on homepage/docs/pricing/Footer | Passed |
| Approved hero preserved | Compare entire first section to saved hero commit | Byte-identical |
| Footer typography matches brand | Computed font family/size/weight/line height/letter spacing/case | All match in 8 cases |
| Responsive footer | 320, 390, 768, 1440px in light and dark themes | No horizontal overflow or clipped heading text |
| Footer access | H3 elements, computed contrast, keyboard focus | Semantics retained; 10.92:1 light and 14.35:1 dark; visible 3px link focus outline |
| Homepage routes and anchors | Read-only GET and HTML ID audit of 28 unique destinations locally and against public targets | No 404 or missing anchor in corrected destinations; three GitHub HTML pages returned 503 |
| Six corrected PyPI links | Built DOM URLs versus published release-page IDs | All six match three real IDs |
| PyPI browser landing | Direct supported in-app navigation | Correct qualification heading appears at viewport top |
| Legacy docs footer link | Click in built preview; inspect final URL and content | Reaches `/framework-docs/index.html`, title and heading `Attune AI` |
| Browser console | Captured warnings/errors | None |

GitHub's contents API confirms all three unavailable HTML targets exist:
comparison at tag v1.3.0 (`fb98ba4f8482c4bcdbe07bf8ba81382c67270018`),
journey boundary at tag v1.3.0
(`dffc0899b6b1f30545450cc6e170e04fd5bcfabb`), and Attune AI LICENSE on main
(`7471531d99b053f91ab5ec492c67950393e23c82`). Their URLs were retained.
HTTP 503 availability remains unresolved; it is not evidence of a missing
file. No authentication or browser security denial was encountered.

Clicking the external qualification link did not change the in-app tab.
Direct navigation to the same URL loaded PyPI and landed on the heading.
This observed handoff behavior is separate from the verified wrong anchor.
No alternate localhost access route or security bypass was used.

The initial hero milestone also passed 87 governance tests, 3 capability
accuracy tests and 16 website version accuracy tests, with 12 responsive
hero cases. Those historical results are in `review/receipt.md`; this
milestone's current evidence is in `review/footer-link-receipt.md`.
Pinned hooks passed for the changed source and handoff; evidence is
`review/footer-link-pre-commit.log`.

## Deliverables and next action

- Local preview: `http://127.0.0.1:3217/`, retained in Codex's browser.
- Desktop/mobile footer screenshots in both themes are in task `review/`.
- Hero screenshots, source patches and machine-readable audit results are
  also in `review/`.
- Library screenshot transfer is blocked by the required helper's hosted
  app discovery TLS failure. No upload IDs were confirmed. The local files
  are intact; see `review/library-upload-status.md`.

Review the combined draft. Before later publication, recheck current main
and active lanes, integrate the bounded source change and rerun publication
checks. Add the hero CTA only after its public destination demonstrates
all three promised steps. This handoff grants no publishing authority.
