---
type: quickstart
name: task-ci-cd-pipeline
tags: [ci, cd, github-actions, automation]
source: developer-guidance
---

# I Need CI for My Python Project

Five steps to a working GitHub Actions pipeline that
lints, tests, and scans your code on every push.

## Step 1: Create the workflow directory

```
mkdir -p .github/workflows
```

GitHub Actions only looks for workflow files in this
exact directory.

## Step 2: Create the workflow file

Create `.github/workflows/ci.yml` with this content:

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
      - run: pip install ruff
      - run: ruff check src/

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pip install -e '.[dev]'
      - run: pytest --tb=short
```

Adjust `src/` and `'.[dev]'` to match your project
layout and test extras.

## Step 3: Push and verify

```
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions pipeline"
git push
```

Go to the **Actions** tab on your GitHub repository.
You should see the workflow running within a few seconds.

## Step 4: Open a test pull request

Create a branch, make a small change, and open a PR.
Verify that CI runs on the pull request and the status
checks appear on the PR page.

## Step 5: Protect your main branch

Go to **Settings > Branches > Add branch protection
rule** for `main`:

- Enable **Require status checks to pass before merging**
- Select the `lint` and `test` jobs
- Save

Now no one can merge a PR that breaks CI.

**Done.** Every push and PR now runs linting and tests
automatically.

## Quick additions

| Want to add | What to do |
|---|---|
| Security scanning | Add a `security` job with `bandit -r src/` and `pip-audit` |
| More Python versions | Add versions to the matrix list |
| macOS/Windows testing | Add `os: [ubuntu-latest, macos-latest, windows-latest]` to the matrix |
| Dependency caching with uv | Replace `setup-python` with `astral-sh/setup-uv@v4` and `enable-cache: true` |
| Auto-publish to PyPI | Add a deploy job triggered by tag push |

## Want to learn more?

- Say **"what is CI/CD?"** for pipeline concepts -- CI
  vs CD, stages, and matrix builds explained
- Say **"walk me through the full CI setup"** for the
  detailed guide with security scanning and caching
- Say **"show me the GitHub Actions reference"** for
  trigger events, caching options, secrets, and
  troubleshooting
- Try **/security** to add security gates to your
  pipeline
- Try **/smart-test** to generate tests for uncovered
  code before enabling CI
- Try **/release** to automate deployment after CI
  passes

## Related Topics

- **Concept**: CI/CD pipeline -- CI vs CD, pipeline
  stages, matrix builds, and what to automate
- **Task**: CI/CD pipeline -- step-by-step guide to
  setting up GitHub Actions for a Python project
- **Reference**: CI/CD pipeline -- GitHub Actions syntax,
  triggers, caching, secrets, and common problems
