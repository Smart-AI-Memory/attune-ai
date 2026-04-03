---
type: quickstart
name: task-package-publishing
tags: [publishing, pypi, python, packaging]
source: developer-guidance
---

# Quickstart: Publish Your Package

Get from "ready to publish" to "verified on PyPI"
in 5 steps.

## Step 1: Bump the version

Edit `pyproject.toml`:

```toml
[project]
version = "2.1.0"
```

Pick the right bump: major for breaking changes, minor
for new features, patch for bug fixes.

## Step 2: Clean build

```bash
rm -rf dist/ build/ *.egg-info
python -m build
```

Check that the filenames in `dist/` show your new
version. If they show the old version, you forgot to
save `pyproject.toml`.

## Step 3: Test on TestPyPI

```bash
twine upload --repository testpypi dist/*
```

Visit `https://test.pypi.org/project/your-package/`
and verify the README renders correctly and the version
is right. Then test the install:

```bash
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    your-package==2.1.0
```

## Step 4: Publish to PyPI

```bash
twine upload dist/*
```

This is permanent. You cannot overwrite a version once
it is uploaded.

## Step 5: Verify

```bash
pip install your-package==2.1.0
python -c "import your_package; print(your_package.__version__)"
```

If the version matches, you are done. Tag the release:

```bash
git tag v2.1.0
git push origin v2.1.0
```

**Done.** Your package is live on PyPI.

## What you get

| Feature | How it works |
|---------|-------------|
| Installable package | Anyone can `pip install your-package` |
| Rendered README | PyPI shows your README as the package page |
| Versioned releases | Users pin to specific versions |
| Extras support | `pip install 'your-package[redis]'` installs optional deps |

## Preflight checklist

| Step | What to check | Common mistake | Recovery |
|------|--------------|----------------|----------|
| Version bump | `pyproject.toml` version is new | Forgot to bump | Fix and rebuild |
| Clean build | `dist/` only has new version files | Stale artifacts from last build | `rm -rf dist/` and rebuild |
| TestPyPI | README renders, install works | Relative links break on PyPI | Fix links, bump patch, re-upload |
| Publish | Twine succeeds without errors | Token not configured | Set `TWINE_PASSWORD` env var |
| Verify | Correct version installs and imports | Published stale dist | Bump version and re-publish |

## Want to learn more?

- Say **"how do I publish my package?"** for the full
  step-by-step guide with detailed verification tables
- Say **"show me the publishing reference"** for every
  pyproject.toml field, build tool, and twine command
- Say **"what is package publishing?"** for semantic
  versioning and what can go wrong
- Ask **"/release"** to run pre-publish health checks
  and generate a changelog automatically
- Ask **"/security"** to scan dependencies for supply
  chain vulnerabilities before publishing
