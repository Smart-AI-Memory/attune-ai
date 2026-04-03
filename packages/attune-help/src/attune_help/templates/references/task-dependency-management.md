---
type: reference
subtype: tabular
name: task-dependency-management
tags: [deps, packaging, python]
source: developer-guidance
---

# Dependency Management Reference

Complete reference for Python dependency management —
version constraints, lockfiles, auditing tools, extras,
groups, and vendoring.

## Version constraint syntax

These specifiers go in `pyproject.toml` under
`[project] dependencies`:

| Specifier | Example | What it allows | When to use |
|-----------|---------|---------------|-------------|
| `>=` | `>=2.0.0` | 2.0.0 and above (no ceiling) | Libraries with good semver history |
| `>=,<` | `>=2.0.0,<3.0` | 2.x only | Most dependencies (recommended) |
| `~=` | `~=2.5.0` | >=2.5.0, <2.6.0 (patch only) | When you need tight compatibility |
| `==` | `==2.5.3` | Exactly this version | Reproducible builds, CI pinning |
| `!=` | `!=2.5.4` | Exclude a broken release | Temporary workaround for bad versions |
| `>=` + `!=` | `>=2.0,!=2.5.4` | Range minus one bad version | Skip a known-broken release |

### Pinning strategy by context

| Context | Strategy | Example | Rationale |
|---------|----------|---------|-----------|
| **Application** | Pin exact or tight range | `==2.5.3` or `~=2.5.0` | Reproducible deploys |
| **Library** | Wide range with floor | `>=2.0.0,<3.0` | Let users resolve conflicts |
| **CI/tooling** | Pin exact in lockfile | `pip-compile` output | Deterministic builds |

## pyproject.toml dependency sections

### Core dependencies

```toml
[project]
dependencies = [
    "pydantic>=2.6.0,<3.0",
    "structlog>=24.1.0",
    "rich>=13.0.0",
]
```

### Optional extras

```toml
[project.optional-dependencies]
redis = ["redis>=5.0.0"]
developer = [
    "pytest>=8.0",
    "ruff>=0.4.0",
    "black>=24.0",
]
memory = ["sentence-transformers>=2.2.0"]
```

Users install extras with:

```
pip install 'your-package[redis,developer]'
```

### Dependency groups (PEP 735)

For dependencies that aren't user-installable extras
(build tools, linters, CI-only):

```toml
[dependency-groups]
test = ["pytest>=8.0", "coverage>=7.0"]
lint = ["ruff>=0.4.0", "black>=24.0"]
docs = ["mkdocs>=1.6", "mkdocs-material>=9.5"]
```

Install with:

```
pip install --dependency-groups=test,lint
```

## Lockfile management

### pip-compile (pip-tools)

Generates a pinned `requirements.txt` from your
`pyproject.toml`:

```
pip-compile pyproject.toml -o requirements.lock
pip-compile --extra=dev -o requirements-dev.lock
```

The lockfile pins every transitive dependency with
hashes:

```
httpx==0.27.0 \
    --hash=sha256:abc123...
idna==3.7 \
    --hash=sha256:def456...
```

Install from lockfile:

```
pip install -r requirements.lock
```

### uv (faster alternative)

```
uv pip compile pyproject.toml -o requirements.lock
uv pip sync requirements.lock
```

## Auditing tools

### pip-audit

Scans installed packages against the OSV database:

```
pip-audit
```

| Flag | Effect |
|------|--------|
| `--strict` | Non-zero exit on any finding (for CI) |
| `--fix` | Auto-upgrade vulnerable packages |
| `--desc` | Include vulnerability descriptions |
| `--format=json` | Machine-readable output |
| `-r requirements.lock` | Audit a lockfile without installing |

Example CI integration:

```yaml
- name: Audit dependencies
  run: pip-audit --strict --desc
```

### pip-licenses

Checks license compliance:

```
pip-licenses --format=table --with-urls
```

| Flag | Effect |
|------|--------|
| `--allow-only="MIT;BSD-3-Clause;Apache-2.0"` | Fail on disallowed licenses |
| `--fail-on="GPL-3.0"` | Fail on specific licenses |
| `--format=json` | Machine-readable output |
| `--with-description` | Include package descriptions |

### safety (alternative to pip-audit)

```
safety check
```

Uses a commercial vulnerability database. Free for
open-source projects, paid for private repos.

## Transitive dependency inspection

### See what a package pulls in

```
pip show httpx
```

Look at the `Requires:` line. For a full tree:

```
pipdeptree -p httpx
```

Example output:

```
httpx==0.27.0
  - anyio>=3.0 [installed: 4.3.0]
  - certifi [installed: 2024.2.2]
  - httpcore==1.* [installed: 1.0.5]
    - certifi [installed: 2024.2.2]
    - h11>=0.13,<0.15 [installed: 0.14.0]
  - idna [installed: 3.7]
```

### Find unused dependencies

```
pip-autoremove --list
```

Or manually check imports:

```
grep -r "import package_name" src/
```

If no imports exist outside test files, the dependency
may be removable.

## Vendoring

Vendoring copies a dependency's source into your repo
so you don't rely on PyPI at install time.

| Situation | Vendor? | Reason |
|-----------|---------|--------|
| Small utility, 1 file | Maybe | Avoids a dependency for trivial code |
| Large library | No | Maintenance burden too high |
| Unstable/abandoned package | Maybe | Freeze at a known-good version |
| Airgapped environments | Yes | No network access at install |

If you vendor, put the code in a `_vendor/` directory
and document the original source and version in a
`_vendor/README.md`.

## Common problems

| Problem | Cause | Fix |
|---------|-------|-----|
| `pip-audit` fails on unpublished versions | Local editable install with version not on PyPI | Self-resolves after publishing; not a blocking issue |
| Dependency lower bounds trigger Scorecard alerts | `pyproject.toml` allows versions with known CVEs | Bump lower bound past the patched version |
| Transitive dep conflict | Two packages require incompatible versions | Pin the conflicting package explicitly or find an alternative |
| `ModuleNotFoundError` in CI | Optional dep not installed | Add to the right extras group; use `pytest.importorskip()` in tests |

## Want to learn more?

- Say **"what is dependency management?"** to go back
  to the overview
- Say **"how do I manage dependencies?"** for the
  step-by-step guide
- Say **"run a security audit"** to scan your installed
  packages for known CVEs
- Say **"help me prepare a release"** to verify
  dependencies before publishing
