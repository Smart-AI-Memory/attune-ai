---
name: workflows
description: Automated analysis — security audit, bug prediction, performance
category: hub
aliases: [wf, workflow]
tags: [security, bugs, performance, audit, analysis]
version: "1.0.0"
question:
  header: "Analysis Workflows"
  question: "What would you like to analyze?"
  multiSelect: false
  options:
    - label: "Security audit"
      description: "Scan for vulnerabilities: eval, path traversal, secrets"
    - label: "Bug prediction"
      description: "Detect patterns likely to produce bugs"
    - label: "Performance audit"
      description: "Find bottlenecks and optimization opportunities"
    - label: "Code review"
      description: "Comprehensive quality and style analysis"
---

# workflows

Automated analysis workflows — security audit, bug prediction, performance, and code review.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/workflows security` | Run security audit |
| `/workflows bugs` | Run bug prediction |
| `/workflows perf` | Run performance audit |
| `/workflows review <path>` | Run code review |
| `/workflows list` | List available workflows |

## Natural Language

Describe what you need:

- "find security vulnerabilities"
- "predict bugs in my code"
- "what are the performance bottlenecks?"
- "review the authentication module"
- "what workflows are available?"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST execute the workflow, not answer ad-hoc.**

### Context Gathering (ALWAYS DO FIRST)

Before executing any action below, gather current project context:

1. Run: `git status --short`
2. Run: `git log --oneline -5`
3. Run: `git branch --show-current`

Use this context to inform your analysis (e.g., recently changed files, current branch).

### Reasoning Approach

For analysis workflows, use structured reasoning before presenting results:

<analysis-steps>
1. **Severity enumeration** — Classify each finding as CRITICAL, HIGH, MEDIUM, or LOW using CWE/OWASP severity guidelines
2. **False positive checking** — Cross-reference findings against known false positives (see scanner-patterns.md): test fixtures, JavaScript .exec(), intentional broad catches with `# INTENTIONAL:` comments
3. **Impact assessment** — For each genuine finding, assess blast radius: single function, module, or system-wide
4. **Health scoring** — Calculate aggregate health score (0-100) based on: critical issues (-20 each), high (-10), medium (-5), low (-1)
5. **Actionable recommendations** — Prioritize fixes by severity × effort, separating quick wins from larger refactors
</analysis-steps>

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/workflows security` | Run Security wizard: define scope → scan → generate fixes → decompose remediation → preview |
| `/workflows security <path>` | Run Security wizard for the specified path |
| `/workflows bugs` | `uv run attune workflow run bug-predict` |
| `/workflows bugs <path>` | `uv run attune workflow run bug-predict --path <path>` |
| `/workflows perf` | `uv run attune workflow run perf-audit` |
| `/workflows perf <path>` | `uv run attune workflow run perf-audit --path <path>` |
| `/workflows review <path>` | `uv run attune workflow run code-review --path <path>` |
| `/workflows list` | `uv run attune workflow list` |

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "security", "vulnerabilities", "cwe" | Run Security wizard flow |
| "bugs", "predict", "risky code" | `uv run attune workflow run bug-predict` |
| "performance", "slow", "bottleneck" | `uv run attune workflow run perf-audit` |
| "review", "quality" | `uv run attune workflow run code-review` |
| "list", "available", "what workflows" | `uv run attune workflow list` |

**IMPORTANT:** When arguments are provided, DO NOT just display documentation. EXECUTE the CLI command.

### CLI Reference

```bash
uv run attune workflow run security-audit --path <target>
uv run attune workflow run perf-audit --path <target>
uv run attune workflow run bug-predict --path <target>
uv run attune workflow run code-review --path <target>
uv run attune workflow list
```
