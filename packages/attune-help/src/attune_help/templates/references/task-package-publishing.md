---
type: reference
subtype: tabular
name: task-package-publishing
category: task
tags: [publishing, pypi, python, packaging]
source: developer-guidance
---

# Package Publishing Reference

Complete reference for publishing Python packages --
pyproject.toml metadata, build tools, twine commands,
TestPyPI setup, classifiers, entry points, extras, and
common problems.

## pyproject.toml metadata fields

### Required fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Package name on PyPI (must be unique) | `"attune-ai"` |
| `version` | string | Semantic version | `"2.1.0"` |
| `description` | string | One-line summary (shown in search) | `"AI-powered developer workflows"` |
| `readme` | string | Path to README (rendered on PyPI page) | `"README.md"` |
| `requires-python` | string | Minimum Python version | `">=3.10"` |
| `license` | table | SPDX license identifier | `{text = "Apache-2.0"}` |
| `dependencies` | array | Runtime dependencies | `["pydantic>=2.6.0,<3.0"]` |

### Recommended fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `authors` | array | Author name and email | `[{name = "Your Name", email = "you@example.com"}]` |
| `urls` | table | Project links (shown on PyPI sidebar) | See below |
| `classifiers` | array | PyPI classifiers for discovery | See below |
| `keywords` | array | Search keywords | `["cli", "developer-tools"]` |

### Project URLs

```toml
[project.urls]
Homepage = "https://github.com/you/your-package"
Documentation = "https://your-package.readthedocs.io"
Repository = "https://github.com/you/your-package"
Changelog = "https://github.com/you/your-package/blob/main/CHANGELOG.md"
"Bug Tracker" = "https://github.com/you/your-package/issues"
```

All URLs must be absolute. Relative paths become broken
links on PyPI.

## Classifiers

Classifiers categorize your package on PyPI. They
appear on your package page and in search filters:

```toml
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries",
    "Typing :: Typed",
]
```

| Development status | When to use |
|--------------------|-------------|
| `1 - Planning` | Idea stage, no usable code |
| `3 - Alpha` | Functional but unstable API |
| `4 - Beta` | Stable API, may have bugs |
| `5 - Production/Stable` | Battle-tested, ready for production |

Full list:
`https://pypi.org/classifiers/`

## Entry points

### Console scripts

Register CLI commands that users can run after
`pip install`:

```toml
[project.scripts]
myapp = "myapp.cli:main"
```

After installation, users run `myapp` directly in
their terminal. The value is `module.path:function`.

### GUI scripts

```toml
[project.gui-scripts]
myapp-gui = "myapp.gui:main"
```

Same as console scripts but for GUI applications
(no console window on Windows).

### Plugin entry points

Register discoverable plugins for other packages:

```toml
[project.entry-points."myapp.plugins"]
my-plugin = "myapp_plugin:Plugin"
```

## Optional dependencies (extras)

Define optional feature groups that users install with
bracket syntax:

```toml
[project.optional-dependencies]
redis = ["redis>=5.0.0"]
developer = [
    "pytest>=8.0",
    "ruff>=0.4.0",
    "black>=24.0",
]
all = [
    "attune-ai[redis,developer]",
]
```

Users install with:

```bash
pip install 'your-package[redis]'
pip install 'your-package[developer]'
pip install 'your-package[all]'
```

Always quote the brackets in shell commands -- bare
brackets are glob characters in bash and zsh.

## Build tools

| Tool | Config location | Strengths | When to use |
|------|----------------|-----------|-------------|
| **setuptools** | `pyproject.toml` `[build-system]` | Most widely used, mature | Default choice for most projects |
| **hatchling** | `pyproject.toml` `[tool.hatch]` | Fast, good version management | Projects using hatch for dev workflow |
| **flit** | `pyproject.toml` `[tool.flit]` | Minimal config for pure Python | Simple packages, no compiled extensions |
| **poetry** | `pyproject.toml` `[tool.poetry]` | Integrated dep management | Teams using poetry end-to-end |
| **maturin** | `pyproject.toml` + `Cargo.toml` | Rust extensions | Python packages with Rust code |

### setuptools build-system config

```toml
[build-system]
requires = ["setuptools>=75.0", "wheel"]
build-backend = "setuptools.build_meta"
```

### hatchling build-system config

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Build commands

| Command | What it does |
|---------|-------------|
| `python -m build` | Build sdist and wheel into `dist/` |
| `python -m build --sdist` | Build source distribution only |
| `python -m build --wheel` | Build wheel only |

Always clean before building:

```bash
rm -rf dist/ build/ *.egg-info
python -m build
```

## Twine commands

| Command | What it does |
|---------|-------------|
| `twine check dist/*` | Validate dist files (README rendering, metadata) |
| `twine upload dist/*` | Upload to production PyPI |
| `twine upload --repository testpypi dist/*` | Upload to TestPyPI |

### `~/.pypirc` configuration

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-...
```

Alternatively, pass the token via environment variable
to avoid storing it in a file:

```bash
TWINE_PASSWORD=pypi-... twine upload dist/* \
    --username __token__
```

This is required in non-interactive terminals like CI
runners, where twine cannot prompt for input.

## TestPyPI setup

TestPyPI is a separate index at
`https://test.pypi.org`. You need a separate account
and token.

| Step | Command |
|------|---------|
| Register at `https://test.pypi.org/account/register/` | (browser) |
| Create a token at `https://test.pypi.org/manage/account/` | (browser) |
| Upload | `twine upload --repository testpypi dist/*` |
| Install from TestPyPI | See below |

Installing from TestPyPI while pulling real
dependencies from production PyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    your-package==2.1.0
```

## README rendering on PyPI

PyPI renders `README.md` (or `.rst`) as the package
description. The renderer is stricter than GitHub's:

| Issue | Cause | Fix |
|-------|-------|-----|
| Broken links | Relative paths like `docs/FILE.md` | Use absolute GitHub URLs |
| Missing images | Relative image paths | Use absolute raw.githubusercontent.com URLs |
| HTML stripped | Unsupported HTML tags | Use standard markdown |
| Bad formatting | Trailing whitespace, broken tables | Run `twine check dist/*` before uploading |

Validate before uploading:

```bash
twine check dist/*
```

Or use `readme_renderer` directly:

```bash
python -m readme_renderer README.md -o /tmp/readme.html
```

## Package data and MANIFEST.in

Files included in the sdist are controlled by your
build backend. For setuptools:

```toml
[tool.setuptools.package-data]
mypackage = ["py.typed", "templates/*.html"]
```

If using a `MANIFEST.in` (setuptools only):

```
include LICENSE
include README.md
recursive-include src *.py *.pyi
```

Hatchling and flit use different inclusion mechanisms.
Check your build backend's documentation.

## Common problems

| Problem | Cause | Fix | Recovery |
|---------|-------|-----|----------|
| **Stale dist** | Old files in `dist/` from a previous build | `rm -rf dist/` before every build | Delete the PyPI release (if within minutes), bump version |
| **README not rendering** | Relative links, bad markdown | Use absolute URLs, run `twine check dist/*` | Bump version with fixed README, re-publish |
| **"Version already exists"** | PyPI versions are immutable | Cannot overwrite | Bump to next patch version |
| **Missing MANIFEST.in** | Non-Python files excluded from sdist | Add `MANIFEST.in` or configure `package-data` | Bump version, rebuild with correct includes |
| **Wrong dependencies** | Typo or missing entry in `dependencies` | Fix `pyproject.toml`, rebuild | Bump version, re-publish |
| **Import fails after install** | Package not found in wheel | Check `packages` or `py-modules` in build config | Fix package discovery, bump version |
| **Entry point not found** | Wrong module path in `[project.scripts]` | Verify the function exists and is importable | Fix path, bump version |
| **Twine hangs** | Non-interactive terminal, no stored token | Pass token via `TWINE_PASSWORD` env var | Ctrl+C, set the env var, retry |
| **TestPyPI dep resolution fails** | Dependencies not on TestPyPI | Add `--extra-index-url https://pypi.org/simple/` | Re-run with both index URLs |
| **License not showing** | Missing or misconfigured `license` field | Use `license = {text = "MIT"}` in metadata | Bump version with corrected metadata |

## Want to learn more?

- Say **"what is package publishing?"** for the
  concepts behind versioning and the publish cycle
- Say **"how do I publish my package?"** for the
  step-by-step guide
- Say **"I need to publish my package"** for a
  5-minute quickstart
- Ask **"/release"** for automated pre-publish checks,
  changelog generation, and version bumps
- Ask **"/security"** to audit dependencies and scan
  for supply chain risks before publishing
