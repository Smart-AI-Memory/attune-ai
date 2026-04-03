---
type: task
name: task-ci-cd-pipeline
tags: [ci, cd, github-actions, automation]
source: developer-guidance
---

# Task: Set up a CI/CD pipeline

Step-by-step guide to building a GitHub Actions CI
pipeline for a Python project -- from a blank repository
to linting, testing, security scanning, and matrix builds.

## Prerequisites

- A Python project with `pyproject.toml`
- A test suite runnable with `pytest`
- A GitHub repository (public or private)

## Create the workflow file

GitHub Actions workflows live in `.github/workflows/`.
Create the directory and a workflow file:

```
mkdir -p .github/workflows
```

Create `.github/workflows/ci.yml`. The rest of this guide
builds up the file section by section.

## Define when the pipeline runs

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

This runs CI on every push to `main` and on every pull
request targeting `main`. Most projects start here and
add more triggers later.

## Add a linting job

Linting is the fastest check and should run first. If
code doesn't pass the linter, there's no point running
the full test suite.

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff black
      - run: ruff check src/
      - run: black --check src/ tests/
```

## Add a testing job with matrix strategy

Run your tests across multiple Python versions to catch
compatibility issues early.

```yaml
  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e '.[dev]'
      - run: pytest --tb=short
```

The `needs: lint` line makes the test job wait for
linting to pass. The matrix runs all four Python versions
in parallel.

### Cross-platform matrix

To also test on macOS and Windows, expand the matrix:

```yaml
    strategy:
      matrix:
        python-version: ["3.10", "3.12"]
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
```

Keep cross-platform matrices smaller (fewer Python
versions) to avoid an explosion of jobs. A 4-version x
3-OS matrix is 12 jobs.

## Add a security scanning job

```yaml
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install bandit pip-audit
      - run: bandit -r src/ --severity-level medium
      - run: pip install -e '.' && pip-audit
```

This catches insecure code patterns (bandit) and known
vulnerabilities in your dependencies (pip-audit).

## Cache dependencies to speed up builds

Installing dependencies on every run wastes time. Add
caching to the test job:

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
```

The `cache: pip` option on `setup-python` automatically
caches the pip download cache, cutting install time
significantly on subsequent runs.

### Caching with uv

If you use `uv` instead of pip:

```yaml
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv pip install -e '.[dev]'
```

## Set up required status checks

After your pipeline runs successfully at least once:

1. Go to **Settings > Branches > Branch protection rules**
2. Add a rule for `main`
3. Enable **Require status checks to pass before merging**
4. Select your CI jobs (e.g., `lint`, `test (3.12)`)

Now pull requests cannot merge until CI passes.

## The complete workflow file

Here is the full `.github/workflows/ci.yml` with all
sections combined:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install ruff black
      - run: ruff check src/
      - run: black --check src/ tests/

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pip install -e '.[dev]'
      - run: pytest --tb=short

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install bandit pip-audit
      - run: bandit -r src/ --severity-level medium
      - run: pip install -e '.' && pip-audit
```

## Verification checklist

After pushing the workflow:

- [ ] Navigate to the **Actions** tab on GitHub
- [ ] Confirm the workflow triggered on your push
- [ ] All jobs show green checkmarks
- [ ] Open a draft PR to verify the PR trigger works
- [ ] Required status checks block merge if a job fails

## Want to learn more?

- Say **"what is CI/CD?"** to understand pipeline
  concepts, stages, and trade-offs
- Say **"show me the GitHub Actions reference"** for
  trigger events, caching options, and common problems
- Try **/security** to add deeper security scanning
  beyond bandit
- Try **/smart-test** to generate tests for uncovered
  code before enabling CI
- Try **/release** to add automated deployment after
  CI passes

## Related Topics

- **Concept**: CI/CD pipeline -- CI vs CD, pipeline
  stages, matrix builds, and what to automate
- **Reference**: CI/CD pipeline -- GitHub Actions syntax,
  triggers, caching, secrets, and common problems
- **Quickstart**: CI/CD pipeline -- 5-step guide to a
  working pipeline
