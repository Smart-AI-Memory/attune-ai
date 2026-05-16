---
type: comparison
name: cli-comparison
feature: cli
depth: comparison
generated_at: 2026-05-16T06:19:45.834263+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Comparison: CLI vs Claude Code for attune-ai

## Overview

attune-ai exposes two surfaces: a standalone CLI (`attune`) and Claude Code skills (invoked as slash commands inside a Claude Code conversation). Both surfaces can run workflows, track costs, and access help — but they are optimized for different working styles.

## Feature comparison

| Capability | CLI (`attune`) | Claude Code skills |
|---|---|---|
| Invocation | `attune workflow run`, `attune costs`, etc. | `/security-audit` and similar slash commands |
| Scoping | CLI flags and arguments | Socratic questions; Claude infers context |
| Output rendering | Rich terminal (color panels, tables) | Markdown in the conversation thread |
| Codebase awareness | No — operates on what you pass explicitly | Yes — sees your open files and project context |
| CI/CD integration | Yes — scriptable, exits with standard codes | No |
| Cost tracking | Built-in: `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` | Via MCP tools |
| Follow-up interaction | Manual — re-run the command with new flags | Interactive — Claude can act on its own output ("fix this?") |
| Memory / lessons | `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall` | Not available directly |
| Help browsing | `attune help-docs --tags`, `attune help-docs --tag <tag>` | Not available |
| Setup | `pip install` + API key | Plugin install inside Claude Code |

## Key tradeoffs

**CLI strengths:**
- Scriptable and automatable — suitable for pre-commit hooks, CI pipelines, and scheduled jobs.
- Cost visibility is first-class: you can export cost data (`cmd_costs_export`) or reset it (`cmd_costs_reset`) without leaving the terminal.
- Cross-session memory commands (`cmd_memory_capture`, `cmd_memory_recall`) let you persist lessons between sessions without a running conversation.
- Help documentation is browsable offline with `attune help-docs`.

**CLI limitations:**
- No codebase context — you must pass files and parameters explicitly; the CLI does not infer intent from an open editor.
- No interactive follow-up — if a workflow result needs action, you write another command.

**Claude Code strengths:**
- Context-aware from the start — Claude reads your open files, so scoping a skill invocation requires less explicit input.
- Conversational follow-up — after a skill runs, you can ask Claude to act on the result immediately.

**Claude Code limitations:**
- Not scriptable — unsuitable for CI/CD or batch automation.
- Cost tracking and memory commands are not available as native skills.

## When to use each

**Use the CLI when you:**
- Run attune in CI/CD pipelines or pre-commit hooks.
- Need to export, review, or reset cost data programmatically.
- Want to capture or search cross-session memory (`cmd_memory_capture`, `cmd_memory_recall`).
- Browse or filter help documentation by tag (`attune help-docs --tag <tag>`).
- Prefer deterministic, flag-driven invocation over conversational scoping.

**Use Claude Code skills when you:**
- Are actively editing code and want attune to operate with full file context.
- Need to iterate quickly — running a skill and immediately asking Claude to act on the output.
- Do not need cost exports, memory commands, or CI integration.

For teams that script deployments or run security audits on every PR, the CLI is the right choice. For solo developers doing exploratory refactoring inside Claude Code, skills will feel more natural.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/cost_commands.py`
- `src/attune/cli_commands/help_commands.py`
- `src/attune/cli_commands/` (remaining command modules)

**Tags:** `cli`, `commands`
