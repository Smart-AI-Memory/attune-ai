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
