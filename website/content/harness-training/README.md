# Harness training delivery

The canonical lessons and renderer belong to
[attune-harness](https://github.com/Smart-AI-Memory/attune-harness/tree/main/training).
This website owns their static delivery and discovery links. Do not edit the
imported HTML or maintain another authored course here.

## Current candidate

Help and training are imported from Harness commit
`1ad347d7b4a87d93f08df99e5c1efb4ee748632a`, on draft PR #340. Before production,
merge the reviewed Harness source and reimport its exact merged commit.
The course is a draft for unpublished 1.7.0; current installation guidance
continues to describe published 1.6.0. Historical documents retain their
original version and evidence behind the archive entrance.

The stable entry `/harness/learn/` redirects to
`/harness/learn/1.7.0-preparation/`. Keep the course and archive directories as
siblings so their relative links work. Interactive lessons, reading views,
fixtures and downloads are copied without content changes.

## Refresh the export

From `website/`, import a trusted, reviewed commit into a fresh directory:

```sh
node scripts/harness-training-export.mjs import --repo /absolute/path/to/attune-harness --commit FULL_COMMIT_SHA --python /absolute/path/to/python --output /absolute/path/to/new-export
node scripts/harness-training-export.mjs check --output /absolute/path/to/new-export
```

The importer verifies the configured GitHub origin, exact commit, regular
files, confined paths, source renderer, complete inventory and SHA-256 hashes.
Origin configuration does not authenticate a commit: source review establishes
that trust boundary. The website build checks the committed receipt offline.
Maintenance scripts are excluded from the delivered payload.

The current export has 47 payload files. Its receipt and the Help receipt name
the same source. Review a refreshed export before replacing the published tree;
the importer refuses an existing destination. Preserve earlier evidence beside
new evidence rather than regenerating old receipts.

Check the committed export, too: the repository ignores `data/` directories.
Explicitly include the reviewed synthetic CSV and run both export checks from
a clean Git archive before pushing. A complete working directory alone does
not establish that the committed payload is complete.

## Verification boundary

Check the importer refusal controls, full website tests, production build and
actual public routes. Follow main navigation to Help, the course, a lesson and
its reading view on desktop and mobile. Unknown routes must return 404.
Course Help links use the canonical public domain, so local checks alone do not
prove that return journey. Verify source identity and the complete public
journey after deployment before reporting publication complete.
