# Harness Help source publication handoff

## Goal

Prepare the existing Help Center source for review against website main
`5e11cb025b605d7a6c1725024baf517a9dc8369e`, on the owned branch
`feat/harness-help-source-publication`. The original local implementation at
`44b817290103f06a2f4f26bbbc151388d312422d` and its frozen evidence are preserved.

This source adds the Help layout, overview, seven task articles and separate
next-release preparation page under `/harness/help/`. Legacy AI docs, shared
Navigation/Footer, themes, static framework docs, dependencies and deployment
configuration are unchanged. Historical delivery plans, private coordination
notes, raw receipts, captures and the review ZIP are not part of this delta.

## Current state

Draft PR #2552 publishes the initial signed source head
`21d6853b135f869e3a028aa2f2614b457bf7f5be`. Its automatic review previews are
ready, and Patrick's existing browser can open the Help Center. Production
integration remains held. Initial CI failures are retained: the projection's
comment expression did not match newlines, and this handoff lacked required
section headings. The owned corrections require a normal push and fresh
exact-head automatic checks before a final qualification claim.

## Content provenance

The released articles retain the published Harness 1.3.0 behavior boundary.
The four canonical walkthroughs are projected from the tutorial owner's
committed local source `86e83c6e29a27f605128600ff011176265e4e431`; the pinned
snapshot and generated JSON remain unchanged. `walkthrough-provenance.json`
records its distinct behavior release and unpublished source status.

The separate next-release record retains its reviewed candidate source/capture
pins. It does not assign a new version/date or imply that those candidates were
part of published 1.3.0. Later software merges do not silently refresh canonical
instructions, captures or this preparation record. Coordinate any refresh with
the tutorial and candidate owners before publication.

## Verification

An isolated Python environment was provisioned from the unchanged repository
lock using `uv sync --frozen --extra dev`; the website environment uses the
unchanged lock through `npm ci`. Shared Python and owner environments were not
modified. The required collaboration preflight passes 87 governance tests;
its two cached-main warnings do not replace the separately fetched main identity.

Local checks pass: projection `--check`, targeted ESLint, TypeScript, 72 website
tests in nine files, and direct Next Webpack compilation. The build creates 126
static pages including all nine Help routes. Default docs regeneration and
`build:vercel`/IndexNow scripts are not invoked. Preserve exact source/hash and
independent-review evidence separately before the proposed commit is pushed.

The first source head's CodeQL check found that editorial comment removal did
not match newlines. The bounded projector correction enables multiline matching;
single-line/multiline regression cases pass, and the canonical snapshot and
generated walkthroughs remain unchanged. This is comment handling, not a claim
that a regular expression provides general HTML sanitization.

Prior browser/link receipts remain attributed to their original implementation.
New source integration does not establish screen-reader, full AT/400% zoom,
real-device, Safari/Firefox, native Windows walkthrough, provider quality,
user comprehension or WCAG conformance. No paid provider call is authorized.

## Publication boundary

The existing Git integration creates hosted Vercel previews for branch/PR
updates, including draft PRs. Main integration automatically deploys production.
Primary deployment records demonstrate both consequences. Patrick authorized
source preparation and the automatic hosted review preview. Push reviewed
corrections normally to existing draft PR #2552; verify the refreshed preview's
exact source and user access.
Keep merge/production held separately. Do not change hosting settings, grants
or shared navigation to bypass the production boundary or preview protection.

The already merged Harness release-runbook PR #244 is a separate completed
documentation change. It does not publish this website source or authorize a
new Harness version. Central retains its sequential Harness merge queue; this
website source preparation schedules no main merge.

## Next action

After independent review and signed commit, deliver the exact head, draft PR,
preview URL and access requirements, focused patch and retained check evidence.
Delete this portable handoff when its eventual PR merges, under the repository
handoff rule.
