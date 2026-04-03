---
type: concept
name: task-ci-cd-pipeline
tags: [ci, cd, github-actions, automation]
source: developer-guidance
---

# Concept: CI/CD pipelines

## What

CI/CD is the practice of automatically building, testing,
and deploying your code every time you push a change.
**Continuous Integration** (CI) catches bugs early by
running checks on every commit. **Continuous Deployment**
(CD) ships verified code to production without manual
steps. Together they replace "it works on my machine"
with "it works everywhere, every time."

## Why

Without CI, bugs hide until someone manually runs the
test suite -- which might be days or weeks after the
broken code was merged. Without CD, deployments are
stressful rituals involving checklists and crossed
fingers. A pipeline turns both into boring, automatic
events that happen in the background while you keep
coding.

## CI vs CD

| Aspect | CI (Continuous Integration) | CD (Continuous Deployment) |
|---|---|---|
| **Goal** | Catch problems fast | Ship verified code automatically |
| **When it runs** | Every push or pull request | After CI passes on the main branch |
| **What it does** | Lint, test, type-check, security scan | Build artifacts, publish packages, deploy |
| **Fails if** | Any check reports an error | Build or deploy step fails |
| **Who fixes it** | The developer who pushed | The on-call or release owner |

Some teams use **Continuous Delivery** instead of
Continuous Deployment -- the pipeline builds and
verifies everything but waits for a human to press
the deploy button.

## Pipeline stages

A typical Python CI pipeline runs these stages in
order. Each stage acts as a gate -- if it fails, the
later stages never run.

| Stage | What runs | Blocks deploy? | Typical time |
|---|---|---|---|
| **Lint** | ruff, black, trailing-whitespace checks | Yes | 10-30 seconds |
| **Type check** | mypy or pyright | Optional | 30-60 seconds |
| **Unit tests** | pytest on your test suite | Yes | 1-10 minutes |
| **Security scan** | bandit, pip-audit, detect-secrets | Yes | 30-60 seconds |
| **Build** | Build wheel and sdist | Yes | 10-30 seconds |
| **Integration tests** | Tests that hit real services or databases | Sometimes | 2-15 minutes |
| **Deploy** | Publish to PyPI, push container, etc. | N/A (this IS the deploy) | 1-5 minutes |

## What to automate and why

| Automate this | Because |
|---|---|
| Linting and formatting | Eliminates style debates in code review |
| Running tests | Catches regressions before they reach main |
| Security scanning | Finds vulnerabilities before they ship |
| Dependency auditing | Catches known CVEs in your supply chain |
| Building artifacts | Ensures the package actually builds cleanly |
| Version checks | Prevents releasing with a stale version |

## GitHub Actions basics

GitHub Actions is the most common CI/CD platform for
GitHub-hosted projects. Key concepts:

- **Workflow**: A YAML file in `.github/workflows/` that
  defines when and what to run
- **Job**: A set of steps that run on a single runner
  (virtual machine)
- **Step**: One command or action within a job
- **Runner**: The machine that executes the job (Ubuntu,
  macOS, or Windows)
- **Action**: A reusable step published by the community
  (e.g., `actions/checkout`)
- **Matrix**: Run the same job across multiple
  configurations (Python versions, operating systems)

## Matrix builds

A matrix strategy runs your test suite across multiple
Python versions and operating systems in parallel:

| Dimension | Common values | Why |
|---|---|---|
| Python version | 3.10, 3.11, 3.12, 3.13 | Catch version-specific bugs |
| Operating system | ubuntu-latest, macos-latest, windows-latest | Catch platform-specific issues (encoding, paths) |
| Dependency set | minimal, full | Verify optional extras don't break core |

A 4-version x 3-OS matrix creates 12 parallel jobs.
This sounds expensive but each job runs independently,
so the total wall-clock time is roughly the time of the
slowest single job.

## Want to learn more?

- Say **"how do I set up CI for my Python project?"**
  for the step-by-step guide
- Say **"show me the GitHub Actions reference"** for
  workflow syntax, trigger events, and caching strategies
- Say **"I need CI for my Python project"** for the
  5-step quickstart
- Try **/security** to add security scanning to your
  pipeline
- Try **/smart-test** to identify which tests to run
  in CI
- Try **/release** to automate deployment checks

## Related Topics

- **Task**: CI/CD pipeline -- step-by-step guide to
  setting up GitHub Actions for a Python project
- **Reference**: CI/CD pipeline -- GitHub Actions syntax,
  triggers, caching, and common problems
- **Quickstart**: CI/CD pipeline -- 5-step guide to a
  working pipeline
