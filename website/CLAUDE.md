# Website — working notes

The marketing/docs/telemetry site for attune-ai (`smartaimemory.com`).
Next.js, deployed by Vercel's git integration on push to `main`. It is
**not** the application and is not versioned.

## Changelog policy

The website is continuously deployed and has no changelog of its own.

- **Website-only change** (CSS, copy, a new page, Vercel config — touches
  only `website/`): **no changelog entry anywhere.** Git history is the
  record.
- **Change that affects the PyPI package** (even if it also touches the
  site — e.g. a telemetry feature whose client ships in the package):
  entry goes in the **root `CHANGELOG.md`**, as normal.

Why the package CHANGELOG still matters here: the public page
`smartaimemory.com/changelog` renders the root `CHANGELOG.md` verbatim
(`app/changelog/page.tsx` reads `../CHANGELOG.md`). Keeping website-only
churn out of it keeps that page release-focused and avoids
website↔package merge conflicts in a shared changelog.

## CI

Website-only PRs (nothing changed outside `website/`) no-op the Python
test suite — the `changes` job in `.github/workflows/tests.yml` emits
`website_only=true`, and the full-suite jobs (`test`, `clock-tz`,
`coverage`) skip their pip-install + pytest steps while still reporting
green so branch protection stays satisfied.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
