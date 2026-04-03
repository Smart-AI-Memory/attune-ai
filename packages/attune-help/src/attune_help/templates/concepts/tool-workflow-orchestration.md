---
type: concept
name: tool-workflow-orchestration
tags: [workflows, orchestration, routing]
source: plugin/skills/workflow-orchestration/SKILL.md
---

# Workflow Orchestration

Workflow orchestration runs multiple analysis workflows in
sequence and combines the results into a unified report.
Instead of running security, code review, and test audits
one at a time and piecing together the findings yourself,
you describe what you want and it runs them back-to-back,
then hands you a single combined report.

## What it runs

| Workflow | What it does | Typical time |
|----------|-------------|-------------|
| **Security Audit** | Scans for vulnerabilities, eval/exec, path traversal, secrets | ~2 min |
| **Code Review** | Quality, correctness, style, and architecture review | ~3 min |
| **Bug Prediction** | Detects likely bug patterns and failure hotspots | ~1 min |
| **Deep Review** | Multi-pass: security + quality + test gap analysis | ~5 min |
| **Test Generation** | Creates unit tests for uncovered code | ~3 min |
| **Test Audit** | Coverage audit and gap detection | ~2 min |
| **Doc Audit** | Documentation freshness and gap analysis | ~1 min |
| **Doc Generation** | Generates docs from source code | ~2 min |
| **Performance Audit** | Bottleneck detection and optimization tips | ~2 min |
| **Release Prep** | Health checks, changelog, dependency audits | ~3 min |

## When to use it

Run workflow orchestration when one analysis isn't
enough:

- **Before a release** -- run security + test audit +
  release prep in one pass
- **Comprehensive review** -- run code review + bug
  prediction + deep review for full coverage
- **New contributor onboarding** -- run doc audit + code
  review to understand a module's state
- **CI gate** -- chain security + test audit to block
  PRs with critical findings

If you only need a single workflow, call it directly
(e.g., `/security-audit src/`). Orchestration shines
when you need two or more.

## How it works

1. You say which workflows to run (or describe what
   you need and it picks them)
2. It asks which path or files to analyze
3. It runs each workflow in sequence on that path
4. It combines findings into a single scored report
   grouped by severity

The skill runs on your Claude subscription -- no API
key or additional cost.

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is security audit?"** to learn about
  individual workflows
- Say **"what is deep review?"** for multi-pass analysis
