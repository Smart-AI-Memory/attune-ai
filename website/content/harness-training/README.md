# Harness training delivery

The canonical lessons and renderer belong to
[attune-harness](https://github.com/Smart-AI-Memory/attune-harness/tree/main/training).
This website owns their static delivery and discovery links. Do not edit the
imported HTML or maintain another authored course here.

## Current course

Help and training use merged Harness commit
[`e889c0c`](https://github.com/Smart-AI-Memory/attune-harness/commit/e889c0c1625b51d9d401469b09b362ceeb955bc6).
The six-lesson course uses the published Harness 1.7.0 package for offline
practice. The archive retains the original guides and their evidence.

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

The importer reads the Help manifest at the same commit and requires published
Harness 1.7.0 before running the course renderer. It checks the configured GitHub
origin, regular files, confined paths, entry points, complete inventory and SHA-256
hashes. Review the commit to establish source trust. The website build checks the
committed receipt offline. Maintenance scripts stay outside the delivered payload.

The current export has 47 payload files. Its receipt and the Help receipt name
the same source. Review a refreshed export before replacing the published tree;
the importer refuses an existing destination. Preserve earlier evidence beside
new evidence rather than regenerating old receipts.

Check the committed export, too: the repository ignores `data/` directories.
Explicitly include the reviewed synthetic CSV and run both export checks from
a fresh clean Git checkout before pushing. A complete working directory alone
does not establish that the committed payload is complete.

## Verification boundary

Check the importer refusal controls, full website tests, production build and
actual public routes. Follow main navigation to Help, the course, a lesson and
its reading view on desktop and mobile. Unknown routes must return 404.
Course Help links use the canonical public domain, so local checks alone do not
prove that return journey. Verify source identity and the complete public
journey after deployment before reporting publication complete.
