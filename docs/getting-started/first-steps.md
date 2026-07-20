---
description: Run your first Attune AI AI workflow in 5 minutes. Security audit, bug prediction, and code review with CLI or Python. See immediate results.
---

# First Steps

Run your first AI workflow and see results in under 5 minutes.

---

## Your First Workflow

Let's run a **security audit** on some code. This workflow scans for vulnerabilities and provides actionable recommendations.

### Option 1: CLI (Fastest)

```bash
# Scan your source directory
attune workflow run security-audit --path ./src

# Or scan current directory
attune workflow run security-audit --path .
```

**Example output:**
```
Security Audit Results
======================
Status: completed
Findings: 3

[HIGH] SQL query vulnerable to injection
  File: src/database.py:45
  Fix: Use parameterized queries

[MEDIUM] Hardcoded API key in config
  File: src/config.py:12
  Fix: Move to environment variable

[LOW] Missing input validation
  File: src/handlers/user.py:28
  Fix: Validate user input before processing

Cost: $0.0850
```

### Option 2: Python

```python
from attune.workflows import SecurityAuditWorkflow
import asyncio

async def audit():
    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(path="./src")

    print(f"Success: {result.success}")
    print(result.summary or result.final_output)
    print(f"\nCost: ${result.cost_report.total_cost:.4f}")

asyncio.run(audit())
```

---

## Try More Workflows

Attune AI includes 20 built-in workflows. Here are the most
popular:

| Workflow | Command | What It Does |
|----------|---------|--------------|
| Security Audit | `attune workflow run security-audit` | Find vulnerabilities |
| Bug Prediction | `attune workflow run bug-predict` | Predict likely bugs |
| Code Review | `attune workflow run code-review` | Tiered code analysis |
| Test Generation | `attune workflow run test-gen` | Generate missing tests |
| Release Prep | `attune workflow run release-prep` | Pre-release checklist |
| Dependency Check | `attune workflow run dependency-check` | Find outdated deps |
| Perf Audit | `attune workflow run perf-audit` | Find bottlenecks |

```bash
# List all available workflows
attune workflow list

# Get help for a specific workflow
attune workflow run security-audit --help
```

---

## Understanding the Output

Every workflow returns:

| Field | Description |
|-------|-------------|
| `success` | `True` if the workflow completed without error |
| `summary` | Human-readable summary of the run |
| `final_output` | The workflow's primary result (analysis text) |
| `cost_report` | API costs and cache hit rate (`.total_cost`, ...) |
| `metadata` | Timing, model used, etc. |

### Cost Tracking

```bash
# See your usage
attune telemetry show

# See cost breakdown
attune telemetry savings --days 7
```

All telemetry data stays local in `~/.attune/telemetry/`.

---

## What Just Happened?

When you ran the security audit:

1. **File scanning** - The workflow read your source files
2. **Tiered analysis** - Simple files used a cheap model, complex ones used a capable model
3. **Pattern matching** - Known vulnerability patterns were detected
4. **Report generation** - Results were formatted and returned

This is the **tiered model** approach - automatically routing to the right model based on task complexity.

---

## Interactive Wizards (Claude Code)

If you're using Claude Code, try the guided wizards for a
more interactive experience:

```bash
/wizard run debug       # Step-by-step debugging
/wizard run security    # Guided security audit
/wizard run refactor    # Refactoring with analysis
/wizard run test-gen    # Test generation wizard
/wizard run release-prep  # Release readiness check
```

Wizards ask questions, adapt to your answers, and produce
structured action plans. They use the same workflows under
the hood but guide you through the process interactively.

---

## Next Step

Now that you've run a workflow, it's time to
[Choose Your Path](choose-your-path.md) based on how you
want to use the framework.

---

## See Also

- [Choose Your Path](choose-your-path.md) - Decide between Quick Start, Tutorial, or Deep Dive
- [Installation Guide](installation.md) - Package options and configuration
- [MCP Integration](mcp-integration.md) - Connect to Claude Code for IDE integration
- [Multi-Agent Coordination](../reference/multi-agent.md) - Build agent teams
- [Configuration Reference](../reference/config.md) - Customize framework behavior

---

## Quick Reference

```bash
# Run workflows
attune workflow run <name> --path <path>
attune workflow list

# Check status
attune telemetry show
attune telemetry savings

# Get help
attune --help
attune workflow --help
```
