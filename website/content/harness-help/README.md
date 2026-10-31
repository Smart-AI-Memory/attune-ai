# Harness Help Center publishing bridge

The canonical guides, goals master and controls, release manifest, renderer and walkthrough verification
belong to [attune-harness](https://github.com/Smart-AI-Memory/attune-harness/tree/main/help).
This website publishes a generated static export at `/harness/help/` and keeps
existing topic URLs and heading fragments, including `/harness/help/goals/`.
Do not edit exported HTML or maintain
a second command reference here.

## Published 1.6.0 onboarding promotion

This update promotes the existing `/harness/help/get-started/` page for published
Harness 1.6.0 and delivers its command and starter-prompt copy controls. The
runtime release source is `af2159516a67172cc8f2a1ff62213296b1b67112`. The new
`release-1.6.0.json` records that release; `release-1.5.1.json` and older evidence
retain their original bytes and identities.

The Help build keeps reference version `1.5.1` and behavior source
`ebb5b03b8a4398325df7ddabd28c08186451452e`, with current `published_version`
`1.6.0`. Get started explicitly identifies published 1.6.0; other topics keep
their stated versions. The importer checks this combination instead of
relabeling every guide. Public rewrites also serve `code-copy.js` and the new
release record.

This branch imports merged Harness source
`069b9f010cabcefa076ec292b4a287c49a85d219` from
[Harness #326](https://github.com/Smart-AI-Memory/attune-harness/pull/326).
Its tree matches reviewed candidate `fd690080076dad45dea3e4b2f190e4ecf8c0fbf6`.
A fresh committed-source import reproduced all 27 payloads and the build record
byte-for-byte; only `import.json` changed to identify the actual merge commit.
The earlier source `5929c18c542a667a8a175a06b67ca5f2f571b73a` remains the prior
published website snapshot. Current-head checks and served-route verification
remain required before production delivery.

## Historical 1.5.1 update

The current proposed export has fourteen pages: current 1.5.1 guidance and an
archive grouped by version and release state. Historical 1.5.0 and preparation
guides keep their content and evidence identities. The separate release record
names the actual published files and software-check boundaries. Its route is
covered by the same rewrite and exact-file/hash checks as the other payloads.

The import names verified merged canonical Help commit `5929c18c542a667a8a175a06b67ca5f2f571b73a`.
Its tree equals the tested branch source; all 26 generated files and the build
hash remain byte-identical. The earlier twelve-page results below remain
historical; current checks are recorded in the pull request. Public deployment
requires its separate current-head gates and post-deployment verification.

## Cutover design

Import an exact committed Harness source, build it without network access, and
retain the source revision, source-file hashes and exported-file hashes. The
website build checks that receipt using Node's standard library. Python-Markdown
is needed only when refreshing the export, not when Vercel builds this website.

Next.js rewrites keep the established public URLs while serving the static files.
The eleven registered topics, overview, scripts, styles, images and evidence records must resolve.
Unknown topic paths must stay 404; changed exported bytes or path escapes must
fail the receipt check. The old noindex preparation URL redirects to its immutable
historical record. Source snapshots and their original provenance remain below.

The Harness renderer's twelve-page build, internal-link checks, refusal controls,
reproducibility and published-1.5.0 walkthroughs were checked before this cutover
was prepared. The Next 16.3.8 standalone production build and local HTTP checks served all
twelve pages and their ten supporting payload files, plus the build record, with byte-identical output.
Unknown topics returned 404, and the historical preparation URL returned 308.
All 37 original topic-heading bookmarks remain valid. Browser checks followed
the prominent landing link to the goals page while preserving the public URL.
Learning comes first in its compact navigation. The local worksheet remains
unapproved; its controls and six testing FAQs stay within their owning
disclosures. These are local integration observations;
production deployment, mobile layout and assistive technology remain unchecked.

Rejected alternative: keeping React copies of the guides here would retain two
owners for release-sensitive instructions. A static export leaves a small,
inspectable publishing boundary. Independent hosting can replace that boundary
later without changing who owns the content.

## Refresh the export

From `website/`, with `help/requirements.txt` installed in the Python interpreter
you select:

```sh
node scripts/harness-help-export.mjs import --repo /absolute/path/to/attune-harness --commit FULL_COMMIT_SHA --python /absolute/path/to/python
node scripts/harness-help-export.mjs check
```

The importer reads committed files only. It refuses to replace an existing
export; prepare a fresh destination with `--output` for a subsequent review,
then review the replacement explicitly. No source checkout or retained snapshot
is changed. Before merging the cutover, import from the reviewed **merged Harness
commit**, not an unmerged branch. The receipt names its exact source.

Import only from a trusted local Harness checkout and reviewed commit. The
importer checks the configured GitHub origin, then executes that commit's
renderer. Origin configuration is not source authentication. The offline build
check detects drift against the committed receipt; review of the receipt and
source revision establishes the trust boundary.

## Retained historical evidence

The existing `tutorials-1.3.0.source.md`, `walkthroughs.generated.json`,
`walkthrough-provenance.json` and `next-release.json` retain their original bytes
and evidence boundaries. They are historical inputs, not the current Help Center
source or new 1.5.0 observations. The historical projector remains usable:

```sh
python3 scripts/project-harness-walkthroughs.py --check
```

This source change proposes a website cutover. It does not grant merge,
production publication, account-setting or routing-setting authority.
