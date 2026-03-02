---
name: attune
description: "Developer workflows for Claude Code — security, reviews, tests, and more"
argument-hint: "<what you need help with>"
category: primary
aliases: [a]
tags: [navigation, workflows, security, review, testing]
version: "3.0.0"
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
| `empathy` | Call `empathy_get_level`, offer to change with `empathy_set_level` |
| `setup` | Trigger setup-guide agent |
| `update` | Check version via `version_check` module, offer upgrade if available |

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
| "empathy", "level", "verbosity" | empathy_get_level / empathy_set_level |
| "setup", "install", "configure", "redis" | setup-guide agent |
| "version", "update", "upgrade" | version check |
| "cost", "spend", "usage", "telemetry" | telemetry_stats |
| "agents", "status" | agent heartbeat status |

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
| memory-and-context | memory, store, retrieve, empathy, pattern, classification |
| workflow-orchestration | workflow, run, execute, agent, team, release, security |
| refactor-plan | refactor, restructure, architecture, plan |
