---
type: concept
name: task-package-publishing
tags: [publishing, pypi, python, packaging]
source: developer-guidance
---

# Package Publishing

Publishing a Python package to PyPI is the final step
in making your code available to the world. It looks
simple -- build, upload, done -- but each stage has
failure modes that are invisible until a user tries to
install your package and something breaks.

## The publish cycle

Every release follows the same sequence. Skipping a
step is how broken packages end up on PyPI:

| Step | What happens | What can go wrong |
|------|-------------|-------------------|
| **Version bump** | Update version in `pyproject.toml` | Forgetting to bump, publishing a duplicate |
| **Clean build** | Remove old `dist/`, rebuild | Stale artifacts upload the previous version |
| **TestPyPI** | Upload to test index, install from it | README doesn't render, missing files |
| **Production publish** | Upload to real PyPI | Version already exists (immutable), broken links |
| **Verify** | Install from PyPI in a fresh env | Wrong dependencies, missing extras |

## Semantic versioning

Version numbers communicate intent to your users:

| Component | When to bump | Example |
|-----------|-------------|---------|
| **Major** (X.0.0) | Breaking changes to public API | Renamed function, removed parameter |
| **Minor** (0.X.0) | New features, backward compatible | Added a new command, new optional parameter |
| **Patch** (0.0.X) | Bug fixes, no API changes | Fixed a crash, corrected a typo in output |

Pre-release suffixes like `1.0.0rc1` or `1.0.0a1` let
early adopters test without affecting stable users.
PyPI treats them as separate from the release version.

## Why README rendering matters

PyPI uses your `README.md` as the package description
page. What works on GitHub may break on PyPI because:

- **Relative links break.** `docs/ARCHITECTURE.md`
  becomes `https://pypi.org/project/your-package/docs/...`
  which does not exist. Use absolute GitHub URLs.
- **Some HTML is stripped.** PyPI's markdown renderer
  is stricter than GitHub's.
- **Images need absolute URLs.** Relative image paths
  produce broken images on the PyPI page.

TestPyPI lets you preview the rendered README before
publishing to production.

## What usually goes wrong

| Problem | Root cause | How to avoid it |
|---------|-----------|-----------------|
| **Stale dist** | Old files in `dist/` from a previous build | Always `rm -rf dist/` before building |
| **Wrong version on PyPI** | Built before updating `pyproject.toml` | Verify version in `dist/` filenames before uploading |
| **"Version already exists"** | PyPI versions are immutable once uploaded | Bump to a new version; you cannot overwrite |
| **README not rendering** | Relative links, unsupported HTML, bad markdown | Test on TestPyPI first; use absolute URLs |
| **Missing package data** | Files not included in the sdist/wheel | Check `MANIFEST.in` or build backend config |
| **Broken install** | Missing or incorrect dependencies in metadata | Test `pip install` in a clean virtual environment |

## When you'd think about this

When you're ready to share your package with others.
When cutting a release after a milestone. When CI
passes and you want to make the latest version
available. When you need to publish a security patch.

## Want to learn more?

- Say **"how do I publish my package?"** for the full
  step-by-step guide
- Say **"show me the publishing reference"** for
  pyproject.toml fields, build tools, and twine commands
- Say **"I need to publish my package"** for a 5-minute
  quickstart
- Ask **"/release"** for pre-publish health checks,
  changelog generation, and version bumps
- Ask **"/security"** to scan for supply chain risks
  before publishing
