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
corrects it and checks disclosure ownership. Existing versioned training retains
its historical labels.

## Current quick start and historical setup

The Docs page's top **Harness Quick Start** action opens the canonical
`/harness/help/get-started/` guide. The existing `/docs#quickstart` anchor remains
a short current-version entry, using the imported release notice and linking to
the guide, dynamic version overview and `/harness/archive/1-4-0/#quickstart`.
The `/docs#harness-docs` entry remains available. Active Docs content no longer
duplicates runnable 1.4.0 installation steps or the current guide's commands.

Website #2580 supplies the historical archive page and preserves the original
1.4.0 instructions. Website #2579 owns Navigation, pricing and how-it-works
corrections. Integrate #2580, the canonical publisher #2574 and the Author
reference page #2581 before #2575, then #2579. Validate these dependencies together, retain each PR's ownership
and require fresh checks on the final integrated source.

## Current migration guidance

Both active Docs migration links use `docs/migration.md` at the documentation
revision supplied by the canonical export. Publisher #2574 pins the reviewed
guide at `93f161b8e65bf86b4a7670e899ff96ff260644f1` during preparation. The guide
distinguishes unpublished 1.5.1 from the published 1.5.0 baseline, describes
current Windows limits and retains the original 1.0.0 migration as historical
reference. The existing release adapter supplies this source; no separate
migration pin or publication switch is introduced here.

## Earlier authoring reference

The full Attune Author section is preserved on `/attune-author/`, supplied by
the independently owned website #2581. Docs keeps a concise reference beside
the earlier Attune AI references; `/docs#attune-author` still reaches that link.
The original 1,940-byte section is unchanged in its destination. This placement
change follows the migration correction in a separate commit and requires its
own five-input layout validation, including #2581. The earlier four-input
migration receipt retains its original source identity.

## Release and cutover checks

Before package publication, integrate canonical Help #299, documentation #300
and the audit in #305, then reconcile the selected final source, metadata, exact
candidate artifact and required qualification in #301. Run Help projection/link checks and the
real website rewrite journey, preserving observed results and untested limits.
The metadata-only validation wheel is not the accepted release artifact.

After package publication, verify package bytes/source and index installation.
Refresh the canonical publication status/source, rebuild and import the reviewed
merged export, then validate this site's entry points and release links. Obtain
the applicable merge/publication approval and verify the production landing-to-
goals journey. Package publication does not deploy the website.

The earlier #2575 build/tests/preview passed. Its when-green run39880319742
failed with HTTP401 at the metadata API call; credential/settings repair remains
Patrick's. This website automation failure is separate from Harness package
qualification.

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

## Current quick-start follow-up validation

The October 23 Docs correction was checked in a fresh disposable tree combining
publisher `dcaa5f05f54dc9470783a15613730b85fa4f350b` with this PR's seven page/runtime
inputs. The readiness record is prose only. All 78 website tests, 87 collaboration
preflight checks, targeted ESLint and pinned pre-commit checks passed. Initial
Python dependency failures were resolved in a temporary environment using the
repository's pinned SDK and MCP versions; no test assertion or source changed.

The Next.js 16.3.8 production build passed TypeScript and generated 123 pages.
All 29 local HTTP checks passed, including exported page/asset hashes, current
guide and overview links, both retained Docs anchors, preparation notices,
published package fallback, sitemap exclusions and historical redirect behavior.
Docs contains no 1.4.0 install commands. Actual browser clicks opened the canonical
**Get started** and **Prepare for Harness 1.5.1** pages with their preparation
notices; returning to `/docs#quickstart` showed the current entry.

The archive page is a separate dependency. A later four-input combination with
publisher `dcaa5f05`, this PR's `948ba152` runtime files, archive `59ddfa95`
and current entry points `d21e1c6e` passed 78 tests, a 124-page production build,
31 HTTP checks and the actual Docs-to-archive-to-Help browser journey. The Help
owner independently replayed that journey and checked 23 exact exported payloads.
These historical local checks establish neither a standalone #2575 deployment
nor final integrated source, release publication or production acceptance.
