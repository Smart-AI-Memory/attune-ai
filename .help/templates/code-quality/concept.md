---
type: concept
feature: code-quality
depth: concept
generated_at: 2026-04-14T14:40:31.715238+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Code Quality

Code quality is an automated review system that analyzes codebases for security vulnerabilities, code quality issues, performance problems, and architectural concerns using four specialized AI reviewers.

## How it works

The system coordinates four specialized subagents that each focus on a specific review domain:

- **security-reviewer** — Scans for vulnerabilities and security anti-patterns
- **quality-reviewer** — Identifies style violations, potential bugs, and maintainability issues
- **perf-reviewer** — Analyzes performance bottlenecks and optimization opportunities
- **architect-reviewer** — Evaluates structural design and architectural patterns

Each subagent analyzes the codebase independently, then a senior orchestrator synthesizes their findings into a unified report with an overall health score (0-100) and prioritized recommendations.

## Review output structure

The automated review produces a structured markdown report with these sections:

- **Summary** — Executive overview with numeric health score
- **Security** — Vulnerability findings and security recommendations
- **Quality** — Code style, bug risks, and maintainability issues
- **Performance** — Optimization opportunities and bottlenecks
- **Architecture** — Design patterns and structural improvements
- **Suggestions** — Actionable next steps ranked by priority

## Implementation interface

| Class | Purpose | Location |
|-------|---------|----------|
| `CodeReviewWorkflow` | Orchestrates the four specialized review subagents | `src/attune/workflows/code_review.py` |
