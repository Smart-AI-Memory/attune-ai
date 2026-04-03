---
type: reference
subtype: tabular
name: task-ci-cd-pipeline
tags: [ci, cd, github-actions, automation]
source: developer-guidance
---

# Reference: GitHub Actions for Python projects

Complete reference for GitHub Actions workflow syntax,
trigger events, caching, secrets, common actions, and
troubleshooting.

## Trigger events

| Event | YAML key | When it fires | Common use |
|---|---|---|---|
| Push to branch | `push: branches: [main]` | Commit lands on the branch | Run CI on main, trigger deploy |
| Pull request | `pull_request: branches: [main]` | PR opened, updated, or reopened | Run CI before merge |
| Schedule | `schedule: - cron: '0 6 * * 1'` | Cron schedule (UTC) | Weekly dependency audits |
| Manual dispatch | `workflow_dispatch:` | Click "Run workflow" in Actions tab | On-demand releases, debugging |
| Tag push | `push: tags: ['v*']` | Tag matching pattern is pushed | Publish to PyPI on release |
| Other workflow | `workflow_call:` | Called by another workflow | Reusable CI building blocks |

### Pull request event types

| Type | When it fires | Default? |
|---|---|---|
| `opened` | PR is created | Yes |
| `synchronize` | New commits pushed to PR branch | Yes |
| `reopened` | Closed PR is reopened | Yes |
| `closed` | PR is closed or merged | No |
| `labeled` | Label is added to PR | No |
| `ready_for_review` | Draft PR marked as ready | No |

Specify non-default types with:

```yaml
on:
  pull_request:
    types: [opened, synchronize, ready_for_review]
```

## Matrix strategy

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    os: [ubuntu-latest, macos-latest, windows-latest]
  fail-fast: false
```

| Option | Default | Effect |
|---|---|---|
| `fail-fast` | `true` | Cancel remaining jobs when one fails |
| `max-parallel` | unlimited | Limit concurrent jobs (saves runner minutes) |

### Excluding combinations

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.12"]
    os: [ubuntu-latest, macos-latest, windows-latest]
    exclude:
      - python-version: "3.10"
        os: windows-latest
```

### Including extra combinations

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.12"]
    include:
      - python-version: "3.13"
        os: ubuntu-latest
        experimental: true
```

## Caching strategies

| Tool | How to cache | Cache key | Typical savings |
|---|---|---|---|
| pip | `actions/setup-python` with `cache: pip` | Hashes `requirements*.txt` or `pyproject.toml` | 30-60 seconds |
| uv | `astral-sh/setup-uv` with `enable-cache: true` | Hashes `uv.lock` | 20-40 seconds |
| pip (manual) | `actions/cache` with `~/.cache/pip` | Custom key from lockfile hash | 30-60 seconds |
| Node (for docs) | `actions/setup-node` with `cache: npm` | Hashes `package-lock.json` | 15-30 seconds |

### Manual cache example

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

The `restore-keys` fallback allows partial cache hits
when the exact key doesn't match.

## Secrets management

Store sensitive values in **Settings > Secrets and
variables > Actions**.

| Secret type | Example name | How to reference |
|---|---|---|
| PyPI publish token | `PYPI_TOKEN` | `${{ secrets.PYPI_TOKEN }}` |
| Code signing key | `GPG_PRIVATE_KEY` | `${{ secrets.GPG_PRIVATE_KEY }}` |
| Service credential | `DATABASE_URL` | `${{ secrets.DATABASE_URL }}` |

**Rules:**

- Secrets are masked in logs automatically
- Secrets are not available in pull requests from forks
- Use environment-scoped secrets for deploy jobs
- Never echo secrets or pass them as command arguments

## Required status checks

After a workflow runs at least once, configure branch
protection:

| Setting | Effect |
|---|---|
| Require status checks to pass | PR cannot merge until selected jobs succeed |
| Require branches to be up to date | PR must be rebased on latest main before merge |
| Enforce for administrators | Admins cannot bypass the checks |

**Important:** The check name in branch protection must
match the exact job name GitHub reports. Run
`gh pr checks <number>` to see the actual names.

## Common actions

| Action | Version | What it does |
|---|---|---|
| `actions/checkout` | `v4` | Clones your repository |
| `actions/setup-python` | `v5` | Installs Python, optionally caches pip |
| `astral-sh/setup-uv` | `v4` | Installs uv with optional caching |
| `actions/cache` | `v4` | Caches directories between runs |
| `actions/upload-artifact` | `v4` | Saves files from a job for later download |
| `actions/download-artifact` | `v4` | Retrieves artifacts from a previous job |
| `github/codeql-action/init` | `v3` | Initializes CodeQL security analysis |
| `github/codeql-action/analyze` | `v3` | Runs CodeQL queries and uploads results |

## Timeout management

| Scope | YAML key | Default | Recommendation |
|---|---|---|---|
| Job timeout | `timeout-minutes` on the job | 360 (6 hours) | Set explicitly -- 15-30 min for most CI |
| Step timeout | `timeout-minutes` on a step | Inherits job timeout | Set on flaky or network steps |

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - run: pytest
        timeout-minutes: 15
```

Windows runners are roughly 3x slower than Ubuntu.
Budget accordingly when setting cross-platform timeouts.

## Artifact handling

### Upload artifacts

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: reports/
    retention-days: 7
```

### Download artifacts in a later job

```yaml
- uses: actions/download-artifact@v4
  with:
    name: test-results
    path: reports/
```

### Common artifact use cases

| Artifact | When to upload | When to download |
|---|---|---|
| Test reports | After test job | In a reporting or deploy job |
| Built wheel | After build job | In a publish job |
| Coverage report | After test job | In a PR comment job |
| Security scan results | After security job | For audit trail |

## Common problems

| Problem | Cause | Fix |
|---|---|---|
| Windows tests fail with encoding errors | `Path.read_text()` defaults to `cp1252` on Windows | Always use `encoding="utf-8"` on file reads |
| Job times out | Test suite too slow or runner underpowered | Increase `timeout-minutes`; split into parallel jobs |
| Missing dependency in CI | Optional dep not in install extras | Add to the right extras group in `pyproject.toml` |
| Flaky tests pass locally but fail in CI | Timing, network, or filesystem differences | Use `pytest-retry` or fix the non-determinism |
| `pip-audit` fails on unpublished version | Local version not on PyPI yet | Expected for version bump PRs; self-resolves after publish |
| Cache not restoring | Cache key changed (new deps) | Check `restore-keys` fallback; clear cache in Actions settings |
| Required check never appears | Check name in branch protection doesn't match actual name | Run `gh pr checks <PR>` and use the exact reported name |
| Secrets not available in fork PRs | GitHub security policy | Use `pull_request_target` (with caution) or skip secret-dependent steps |
| `git push --tags` rejects old tags | Pushes ALL local tags, some already exist | Push specific tags: `git push origin v1.0.0` |
| Pre-commit hooks fail differently in CI | Different tool versions or missing config | Pin pre-commit hook versions; commit `.pre-commit-config.yaml` |

## Want to learn more?

- Say **"what is CI/CD?"** for pipeline concepts, stages,
  and trade-offs
- Say **"how do I set up CI for my Python project?"**
  for the step-by-step guide
- Say **"I need CI for my Python project"** for the
  5-step quickstart
- Try **/security** to add security gates to your
  pipeline
- Try **/smart-test** to generate tests that improve
  CI coverage
- Try **/release** to add automated publish-to-PyPI
  after CI passes

## Related Topics

- **Concept**: CI/CD pipeline -- CI vs CD, pipeline
  stages, matrix builds, and what to automate
- **Task**: CI/CD pipeline -- step-by-step guide to
  setting up GitHub Actions for a Python project
- **Quickstart**: CI/CD pipeline -- 5-step guide to a
  working pipeline
