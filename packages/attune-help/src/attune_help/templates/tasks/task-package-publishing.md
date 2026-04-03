---
type: task
name: task-package-publishing
tags: [publishing, pypi, python, packaging]
source: developer-guidance
---

# How to Publish a Python Package

## Before you start

Make sure your `pyproject.toml` has the required
metadata: `name`, `version`, `description`, `readme`,
`license`, `requires-python`, and `dependencies`. If
any of these are missing, PyPI will accept the upload
but your package page will look broken or incomplete.

## Step 1: Bump the version

Update the version in `pyproject.toml`:

```toml
[project]
version = "2.1.0"
```

Follow semantic versioning: major for breaking changes,
minor for new features, patch for bug fixes.

| Check | What to look for | Common mistake |
|-------|-----------------|----------------|
| Version is higher than the last published version | Compare with `pip index versions your-package` | Forgetting to bump after the last release |
| CHANGELOG is updated | New section for this version | Publishing without documenting what changed |
| All tests pass | `pytest` exits clean | Skipping tests "because it's just a version bump" |

## Step 2: Clean build

Always delete old build artifacts before building.
Stale files in `dist/` are the most common cause of
uploading the wrong version:

```bash
rm -rf dist/ build/ *.egg-info
python -m build
```

After building, verify the filenames in `dist/`:

```bash
ls dist/
```

You should see files matching your new version, like
`your_package-2.1.0.tar.gz` and
`your_package-2.1.0-py3-none-any.whl`.

| Check | What to verify | Recovery if wrong |
|-------|---------------|-------------------|
| Filenames show correct version | `2.1.0` in both `.tar.gz` and `.whl` | Delete `dist/`, fix `pyproject.toml`, rebuild |
| Both sdist and wheel present | Two files in `dist/` | Re-run `python -m build` |
| README changes included | Rebuild if you edited README after building | `rm -rf dist/ && python -m build` |

## Step 3: Test on TestPyPI

Upload to the test index first. This catches README
rendering issues, missing files, and metadata problems
before they hit production:

```bash
twine upload --repository testpypi dist/*
```

Then install from TestPyPI in a fresh environment to
verify everything works:

```bash
python -m venv /tmp/test-install
source /tmp/test-install/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    your-package==2.1.0
```

The `--extra-index-url` lets pip find your real
dependencies on production PyPI while installing your
package from TestPyPI.

| Check | What to verify | Recovery if wrong |
|-------|---------------|-------------------|
| README renders correctly | Visit `https://test.pypi.org/project/your-package/` | Fix markdown, bump to `2.1.1`, re-upload |
| Package installs | `pip install` succeeds | Check `dependencies` in `pyproject.toml` |
| Import works | `python -c "import your_package"` | Check package structure and `py_modules`/`packages` config |
| CLI entry points work | Run any console scripts | Verify `[project.scripts]` in `pyproject.toml` |

## Step 4: Publish to production PyPI

Once TestPyPI looks good, upload to the real index:

```bash
twine upload dist/*
```

Twine will prompt for your credentials or use a token
from `~/.pypirc`.

**This is irreversible.** Once a version is on PyPI,
you cannot overwrite it. If something is wrong, you
must bump the version and publish again.

## Step 5: Verify the published package

Install from production PyPI in a clean environment:

```bash
python -m venv /tmp/verify-install
source /tmp/verify-install/bin/activate
pip install your-package==2.1.0
python -c "import your_package; print(your_package.__version__)"
```

| Check | What to verify | Recovery if wrong |
|-------|---------------|-------------------|
| Correct version installed | `__version__` matches `2.1.0` | You uploaded stale artifacts; bump and re-publish |
| All extras install | `pip install 'your-package[dev]'` | Fix `optional-dependencies`, bump version |
| No import errors | Exercise the main entry points | Fix missing `__init__.py` or package data |

## After publishing

- Tag the release in git: `git tag v2.1.0 && git push origin v2.1.0`
- Create a GitHub release from the tag
- Announce the release if your project has users

## What to do next

| Goal | What to say |
|------|-------------|
| Automate pre-publish checks | "help me prepare a release" |
| Scan for supply chain risks | "run a security audit" |
| See all pyproject.toml fields | "show me the publishing reference" |
| Set up CI publishing | "how do I automate PyPI publishing?" |

## Want to learn more?

- Say **"show me the publishing reference"** for
  pyproject.toml metadata, build tools, and twine
  commands
- Say **"what is package publishing?"** for the
  concepts behind versioning and the publish cycle
- Ask **"/release"** to run pre-publish health checks
  and generate a changelog
- Ask **"/security"** to audit your dependencies
  before shipping
