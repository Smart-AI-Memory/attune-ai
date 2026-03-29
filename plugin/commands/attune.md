---
name: attune
description: "Developer workflows for Claude Code — security audits, code reviews, test generation, performance analysis, and release preparation. Triggers on: attune, workflow, security, review, tests, perf, release, bugs, memory, empathy, setup."
argument-hint: "<what you need help with>"
question:
  header: "attune-ai"
  question: "What are you trying to accomplish?"
  multiSelect: false
  options:
    - label: "Run a workflow"
      description: "Security audit, code review, test generation, performance analysis, release prep"
    - label: "Manage memory"
      description: "Store, retrieve, search, or forget patterns and knowledge"
    - label: "Configure settings"
      description: "Check setup, update attune-ai, view telemetry"
    - label: "Learn what attune-ai does"
      description: "Overview of capabilities, skills, and MCP tools"
---

# attune

Single entry point for all attune-ai capabilities. Routes to the appropriate workflow based on context.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/attune security` | Run security audit |
| `/attune review` | Run code review |
| `/attune tests` | Generate tests |
| `/attune perf` | Run performance audit |
| `/attune release` | Run release preparation |
| `/attune memory` | Memory operations |
| `/attune empathy` | Get or set empathy level |
| `/attune setup` | Check environment and install prerequisites |
| `/attune update` | Check for attune-ai updates |

## Execution Instructions

When invoked with arguments, EXECUTE the corresponding action:

| Input | Action |
| ----- | ------ |
| `security` | Call `security_audit` MCP tool with current project path |
| `review` | Call `code_review` MCP tool with current project path |
| `tests` | Ask for module path, then call `test_generation` MCP tool |
| `perf` | Call `performance_audit` MCP tool with current project path |
| `release` | Call `release_prep` MCP tool with current project path |
| `bugs` | Call `bug_predict` MCP tool with current project path |
| `memory` | Route to memory-and-context skill |
| `store` | Ask for key and value, then call `memory_store` MCP tool |
| `retrieve` | Ask for key, then call `memory_retrieve` MCP tool |
| `search` | Ask for query, then call `memory_search` MCP tool |
| `forget` | Ask for key, then call `memory_forget` MCP tool |
| `empathy` | Call `attune_get_level`, offer to change with `attune_set_level` |
| `setup` | Trigger setup-guide agent |
| `update` | Check version via `version_check` module, offer upgrade if available |
| `auth` | Call `auth_status` to show current auth strategy |
| `docs` | Ask for path, then call `doc_gen` MCP tool |
| `simplify` | Ask for path, then call `simplify_code` MCP tool |
| `health` | Call `health_check` MCP tool with current project path |

## Natural Language Routing

| Pattern | Action |
| ------- | ------ |
| "security", "vulnerability", "audit", "scan" | security_audit |
| "review", "quality", "code review" | code_review |
| "test", "generate tests", "coverage" | test_generation |
| "performance", "bottleneck", "optimize" | performance_audit |
| "release", "publish", "ship", "deploy" | release_prep |
| "bug", "predict", "risk" | bug_predict |
| "memory", "store", "remember", "pattern" | memory-and-context skill |
| "forget", "remove", "delete memory" | memory_forget |
| "empathy", "level", "verbosity" | attune_get_level / attune_set_level |
| "setup", "install", "configure", "redis" | setup-guide agent |
| "version", "update", "upgrade" | version check |
| "cost", "spend", "usage", "telemetry" | telemetry_stats |
| "agents", "status" | agent heartbeat status |
| "auth", "authentication", "provider", "api key" | auth_status / auth_recommend |
| "docs", "documentation", "generate docs" | doc_gen / doc_audit |
| "simplify", "reduce complexity" | simplify_code |
| "health", "project health" | health_check |
| "dependencies", "deps", "vulnerabilities" | dependency_check |

## No-Argument Behavior

If no argument is provided, ask:

"What are you trying to accomplish?"

Based on the answer, route to the appropriate skill or MCP tool. Ask clarifying questions to narrow down the intent.

## MCP Server Not Running

If the MCP server is not responding, trigger the setup-guide agent to diagnose and resolve the issue. Common causes:

- attune-ai not installed (`pip install attune-ai`)
- Python version below 3.10
- Server process not started

## Skills Reference

| Skill | Triggers |
| ----- | -------- |
| security-audit | security, vulnerability, audit, scan, CVE, CWE |
| code-quality | review, quality, analyze, lint, bugs, code smell |
| bug-predict | predict bugs, find bugs, risky code, what might break |
| doc-gen | generate docs, documentation, docstrings, README, API docs |
| smart-test | generate tests, test gaps, coverage, untested, smart test |
| fix-test | fix test, broken test, test failure, debug test |
| planning | plan, feature, architecture, design, TDD, strategy |
| refactor-plan | refactor, restructure, tech debt, simplify, modularize |
| release-prep | release, publish, ship, deploy, version bump, changelog |
| memory-and-context | memory, store, retrieve, empathy, pattern, classification |
| workflow-orchestration | workflow, run, execute, analyze, all workflows |
