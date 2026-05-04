---
type: concept
feature: deep-review
depth: concept
generated_at: 2026-05-04T02:28:14.874596+00:00
source_hash: e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4
status: generated
---

# Deep Review

Deep review is a multi-pass code analysis workflow that examines your codebase through three specialized lenses: security vulnerabilities, code quality issues, and test coverage gaps.

## How it works

The workflow coordinates three subagents that run in parallel, each focusing on a specific domain:

- **Security reviewer** — Scans for vulnerabilities, insecure patterns, and authentication flaws
- **Quality reviewer** — Evaluates maintainability, performance, and architectural concerns
- **Test gap reviewer** — Identifies missing test coverage and edge cases

After all three subagents complete their analysis, the workflow synthesizes their findings into a single consolidated report with an overall health score (0-100) and prioritized recommendations.

## Review orchestration

The `DeepReviewAgentSDKWorkflow` class manages the entire process:

1. Spawns three specialized Claude Agent SDK subagents
2. Each subagent analyzes the codebase independently
3. Collects and correlates findings across all domains
4. Produces a structured report with sections for security, quality, test gaps, and actionable suggestions

The orchestrator ensures thoroughness while maintaining focus — each subagent operates within its expertise domain, then findings are consolidated to avoid duplication and provide clear next steps.

## Report structure

Every deep review generates a standardized report containing:

- **Summary** — Health score and executive overview with finding counts by severity
- **Security** — Vulnerabilities and security concerns, ordered by risk level
- **Quality** — Maintainability and performance issues, ordered by impact
- **Test gaps** — Missing coverage areas, ordered by priority
- **Suggestions** — Top 5-10 actionable improvements with specific file references

This structure gives you both the high-level assessment you need for planning and the detailed findings required for implementation.
