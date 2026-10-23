# Harness 1.5.1 website entry-point readiness

Preparation; publish after the package release and verified index delivery.
This PR depends on canonical Harness Help #299 and the website cutover #2574
landing through main. It changes Docs, FAQ, homepage, footer and sitemap entry
points. The canonical export owns all Help pages, goal controls and assets.

## One release identity

`lib/harness-release.ts` reads the imported `build.json` and `preparation.json`.
The Help owner maintains version, publication status, published fallback and
behavior source. Preparation links use the pinned current documentation revision;
published links use the final behavior source. There is no second release switch
or independent Help renderer in this PR. Preparation routes stay out of new
sitemap entries until the canonical export says published.

## Preserved work

The original signed implementation and review evidence remain at website commit
`569b15d2d1a49c6c5d465032ec365c0e0527e59a`. Harness #299 ports the authored
guide, 21 goals, six testing FAQs, worksheet, compact learning-first navigation
and historical 1.5.0 captures. An independent browser review found a table-wrapper
containment regression; source `295230ac53d601c9a2539020a3f5be7044cc7559`
corrects it and checks disclosure ownership. Existing versioned training and
the 1.4.0 Quick Start retain their labels.

## Release and cutover checks

Before package publication, complete the canonical documentation audit in
Harness #300 and reconcile the selected final source, metadata, exact candidate
artifact and required qualification. Run Help projection/link checks and the
real website rewrite journey, preserving observed results and untested limits.
The metadata-only validation wheel is not the accepted release artifact.

After package publication, verify package bytes/source and index installation.
Refresh the canonical publication status/source, rebuild and import the reviewed
merged export, then validate this site's entry points and release links. Obtain
the applicable merge/publication approval and verify the production landing-to-
goals journey. Package publication does not deploy the website.

The earlier #2575 build/tests/preview passed. Its when-green run39880319742
failed with HTTP401 at the metadata API call; credential/settings repair remains
Patrick's. This website automation failure is separate from the passing Harness
main qualification.

## Combined preparation validation

A disposable tree combined committed cutover
`6d80ed6c34c3aae7b76e830beb77b3e837e2b594` (Help source
`a90d66d314eee4f612fb514e967acb675be25795`) with these eight entry-point files.
All 78 website tests and targeted ESLint passed. The Next.js 16.3.8 production
build passed TypeScript and generated 123 pages. All 29 local HTTP checks passed:
12 Help pages, exported payload hashes, build metadata, entry points, preparation
notices, sitemap exclusions, unknown-route refusal and historical redirect.

The browser walk passed Docs/FAQ to Help/goals, learning-topic navigation and
reload, 21-topic open/close, worksheet containment, two wording choices, reset
and exact copying of the 5,526-character selected draft. The draft remains
unapproved. These checks made no model calls.

Initial scratch setup failures were corrected by restoring unchanged committed
test/article inputs and using physical dependencies with normal compiler process
permissions. No production source or assertion changed to clear those failures.
This local combination is not a branch merge or final release qualification.
The standalone PR depends on #2574 supplying the imported metadata through main;
its build cannot resolve those imports before that dependency lands. Keep the
draft dependency explicit and check the final integrated head before release.
