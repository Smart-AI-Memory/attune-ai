---
name: utilities
description: Utility tools — profiling, dependencies, and diagnostics
category: hub
aliases: [utils, util]
tags: [utilities, profiling, dependencies, diagnostics]
version: "1.0.0"
question:
  header: "Utilities"
  question: "Which utility do you need?"
  multiSelect: false
  options:
    - label: "Dependency check"
      description: "Audit dependencies for vulnerabilities and updates"
    - label: "Research"
      description: "Investigate and synthesize information from code"
    - label: "Validate config"
      description: "Check attune configuration and API keys"
    - label: "Show features"
      description: "List available features and their status"
---

# utilities

Utility tools — dependency auditing, research, configuration
validation, and diagnostics.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/utilities deps` | Audit dependencies for vulnerabilities |
| `/utilities research <topic>` | Research and analyze a topic |
| `/utilities validate` | Validate attune configuration |
| `/utilities features` | Show available features and status |

## Natural Language

Describe what you need:

- "check my dependencies for vulnerabilities"
- "research how caching works in this project"
- "validate my config"
- "what features are available?"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST
execute the workflow, not answer ad-hoc.**

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/utilities deps` | `uv run attune workflow run dependency-check` |
| `/utilities research <topic>` | `uv run attune workflow run research --query <topic>` |
| `/utilities validate` | `uv run attune validate` |
| `/utilities features` | `uv run attune features` |

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "dependency", "deps", "outdated", "vulnerable" | Run dependency check |
| "research", "investigate", "explore", "analyze" | Run research workflow |
| "validate", "config", "check setup" | Run config validation |
| "features", "available", "status" | Show feature availability |

**IMPORTANT:** When arguments are provided, DO NOT just
display documentation. EXECUTE the action.

### CLI Reference

```bash
uv run attune workflow run dependency-check
uv run attune workflow run research --query <topic>
uv run attune validate
uv run attune features
```
