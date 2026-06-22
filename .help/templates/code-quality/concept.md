---
type: concept
feature: code-quality
depth: concept
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f0f1e5876a5f83b83316fb690fa9aa652fd8f63b15844a89c384083fbac424f
status: generated
---

# Code Quality

Code quality analysis examines your codebase through four specialized reviewers that run in parallel: security, quality, performance, and architecture.

## Four-reviewer architecture

The `CodeReviewWorkflow` coordinates four subagents, each focusing on a specific domain:

- **Security reviewer** — Identifies vulnerabilities, unsafe patterns, and potential attack vectors
- **Quality reviewer** — Catches style violations, logical errors, and maintainability issues
- **Performance reviewer** — Spots inefficient algorithms, memory leaks, and scalability bottlenecks
- **Architecture reviewer** — Evaluates design patterns, coupling, and structural health

Each reviewer analyzes the same code independently, then their findings are synthesized into a unified report with an overall health score (0-100).

## Unified reporting format

Instead of reading four separate outputs, you get a single structured report:

| Section | Content | Source |
|---------|---------|--------|
| **Summary** | Overall health score and executive summary | Synthesized from all reviewers |
| **Security** | Vulnerabilities and safety issues | Security reviewer |
| **Quality** | Style, bugs, and maintainability | Quality reviewer |
| **Performance** | Efficiency and scalability concerns | Performance reviewer |
| **Architecture** | Design and structural analysis | Architecture reviewer |
| **Suggestions** | Actionable next steps by priority | Cross-reviewer synthesis |

## When specialized review matters

This four-reviewer approach catches issues that single-purpose tools miss. A function might pass your linter (style), have no obvious bugs (quality), but create a timing attack vulnerability (security) or scale poorly under load (performance). Running all four perspectives simultaneously gives you comprehensive coverage without the overhead of managing separate tools.
