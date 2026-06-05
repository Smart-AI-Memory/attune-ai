---
type: comparison
name: cli-comparison
feature: cli
depth: comparison
generated_at: 2026-06-04T23:39:47.667247+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# Comparison: CLI vs Claude Code skills

The attune CLI (`attune`) and Claude Code skills are both entry points into attune's workflows and memory system. They share underlying functionality but are optimized for completely different working styles.

## Feature comparison

| Feature | CLI (`attune`) | Claude Code skills |
| --- | --- | --- |
| Invocation | `attune workflow run`, `attune costs`, `attune memory` | `/skill-name` slash commands |
| Routing | `HybridRouter` with learned `RoutingPreference` records | Socratic prompting inside conversation |
| Output format | Terminal (supports `--json` via `json_mode`) | Conversation markdown |
| Codebase context | Not available — you supply input explicitly | Full visibility into open files and project |
| CI/CD use | Yes — `run_workflow_with_exit_code()` returns a contract exit code for pipeline integration | No |
| Follow-up interaction | Manual — re-run with adjusted flags | Interactive — Claude can propose and apply fixes inline |
| Cost tracking | Built-in: `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` | Available via MCP tools |
| Memory commands | `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic` | Via skill invocation |
| Learned routing preferences | `HybridRouter.learn_preference()` stores `RoutingPreference` (keyword, skill, args, usage_count, confidence) | Not applicable |
| Autocomplete suggestions | `HybridRouter.get_suggestions(partial)` | Not applicable |
| Setup | `pip install` + API key, then `attune setup` / `attune doctor` | Plugin install inside Claude Code |

## Key tradeoffs

**Explicitness vs. context-awareness.** The CLI requires you to supply all input data explicitly — it has no view of your codebase. Claude Code skills can read open files and infer context, which reduces the setup cost for exploratory or iterative tasks.

**Scripting and reliability.** `run_workflow_with_exit_code()` returns a well-defined integer exit code, making it straightforward to gate CI/CD steps on workflow outcomes. Claude Code skills have no equivalent contract for automated pipelines.

**Routing intelligence.** The CLI's `HybridRouter` learns from your behavior: `learn_preference()` persists a `RoutingPreference` record (with `confidence` and `usage_count` fields) that improves routing over time. `get_suggestions()` provides prefix-based completions. Claude Code skills rely on conversational disambiguation instead.

**Cost and memory management.** Cost tracking (`cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset`) and the full memory command set (`cmd_remember` through `cmd_memory_forget_topic`) are first-class CLI commands with discrete exit codes. These operations are less directly accessible in a conversational context.

## Use the CLI when…

- You are integrating attune into a CI/CD pipeline and need `run_workflow_with_exit_code()` to return a reliable exit code.
- You want to script batch workflow runs with explicit input data and JSON output (`json_mode=True`).
- You need direct control over cost data — exporting with `cmd_costs_export`, resetting with `cmd_costs_reset`, or reviewing a daily summary with `cmd_costs_today`.
- You are managing cross-session memory programmatically (`cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`).
- You want to build or inspect learned routing preferences via `HybridRouter.learn_preference()` and `HybridRouter.get_suggestions()`.
- You are validating your setup with `cmd_validate` or `cmd_doctor` outside of a conversation.

## Use Claude Code skills when…

- You want attune to see your open files and infer context without you describing the project manually.
- Your task is exploratory and you expect to ask follow-up questions or have Claude apply changes interactively.
- You are already working inside Claude Code and the overhead of switching to a terminal outweighs the benefits of explicit input control.

The CLI is the stronger default for any automated or repeatable workflow. Claude Code skills have the advantage for interactive, context-heavy tasks where the conversation itself carries useful state.

**Tags:** `cli`, `commands`
