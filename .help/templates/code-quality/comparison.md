---
type: comparison
feature: code-quality
depth: comparison
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f0f1e5876a5f83b83316fb690fa9aa652fd8f63b15844a89c384083fbac424f
status: generated
---

# Comparison: Code Quality vs alternatives

## Context

Review code for style issues, likely bugs, and structural problems using four specialized subagents that examine security, quality, performance, and architecture in a single coordinated pass.

## Feature comparison

| Aspect | Code Quality Review | Traditional Linters | Security-only Scans | Manual Code Review |
|--------|-------------------|-------------------|-------------------|-------------------|
| **Coverage** | Style, bugs, security, architecture, performance | Style and basic errors only | Security vulnerabilities only | Depends on reviewer expertise |
| **Integration** | Unified report with single health score | Separate tools, separate reports | Security-focused output | Ad-hoc feedback |
| **Speed** | ~1-3 minutes depending on depth | Seconds to minutes | Minutes to hours | Hours to days |
| **Automation** | Fully automated with guided setup | Fully automated | Fully automated | Manual process |
| **Context awareness** | Four specialized subagents coordinate findings | Rule-based, no context | Security-specific context | High context, but inconsistent |
| **Actionability** | Prioritized suggestions with file/line citations | Raw violation lists | Vulnerability reports | Variable quality feedback |

## When to use code quality

Use the code quality review when you need comprehensive analysis that goes beyond what individual tools provide:

- **Before pull requests** — catch multiple issue types in one pass instead of running separate linters, security scanners, and architectural reviews
- **Inheriting unfamiliar code** — get a unified health assessment that covers security, quality, performance, and structure
- **After major refactors** — verify nothing degraded across multiple dimensions of code health
- **Regular health checks** — establish baseline scores and track improvement over time

The `CodeReviewWorkflow` with its four subagents (security-reviewer, quality-reviewer, perf-reviewer, architect-reviewer) is purpose-built for comprehensive analysis that synthesizes findings into actionable recommendations.

## When NOT to use it

Don't use code quality review when:

- **You need real-time feedback** — traditional linters are faster for immediate style checking during development
- **You only care about one dimension** — if you specifically need security analysis, use a dedicated security audit tool
- **You're working with non-standard codebases** — the four subagents are optimized for typical application code patterns
- **You need custom rule sets** — the review uses predefined criteria rather than configurable rules

## Decision guide

| Your goal | Best choice | Why |
|-----------|-------------|-----|
| Pre-commit style check | Traditional linter | Faster feedback loop |
| Comprehensive PR review | **Code quality review** | Unified analysis across all dimensions |
| Security vulnerability scan | Security-specific tool | Deeper security focus |
| Architecture assessment | **Code quality review** | Architect-reviewer subagent provides structural analysis |
| Performance bottleneck hunting | Profiling tools | Runtime analysis beats static review |
| Code health baseline | **Code quality review** | Single score tracks multiple quality factors |

**Recommendation:** Use code quality review as your primary comprehensive analysis tool, supplemented by real-time linters during development and specialized tools for deep dives into specific areas.

## Source files

- `src/attune/workflows/code_review.py`

**Tags:** `review`, `quality`, `bugs`
