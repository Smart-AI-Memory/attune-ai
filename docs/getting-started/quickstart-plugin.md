---
description: Get started with the Attune AI plugin for Claude Code in 5 minutes — install it, then drive code review, security audits, and spec-driven development with plain English. No CLI, no API key.
---

# Quickstart: The Plugin (Claude Code)

The fastest way to use Attune AI is as a **Claude Code plugin**. Install it
once, then drive everything — code review, security audits, test generation,
spec-driven development — with plain English in your normal Claude Code
session.

No CLI to learn. No Python package. No separate API key — the plugin runs
inside the Claude Code session you already have.

!!! tip "Prefer the CLI or Python?"
    This page is the plugin-first path. If you'd rather run workflows from a
    terminal or from code, start with [First Steps](first-steps.md) instead —
    it covers the `attune` CLI and the Python API.

---

## What you get

The plugin ships <!-- cap:skill_count -->**25 auto-triggering skills**<!-- /cap -->. You don't memorize commands —
you describe what you want, and the right skill activates.

| Say something like… | Skill that activates | What it does |
|---------------------|----------------------|--------------|
| "review this file for quality issues" | `code-quality` | Code review + bug prediction |
| "scan src/ for vulnerabilities" | `security-audit` | eval/exec, secrets, injection, path traversal |
| "what tests am I missing?" | `smart-test` | Finds coverage gaps, generates tests |
| "this test keeps failing" | `fix-test` | Diagnoses and fixes, up to 3 attempts |
| "help me plan this feature" | `planning` | Architecture + TDD planning |
| "let's build X from a spec" | `spec` | Brainstorm → plan → execute with quality gates |
| "what can attune do?" | `attune-hub` | Routes you to the right skill |

---

## Step 1 — Install the plugin (1 min)

In Claude Code:

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

That's it. The skills are now available in every Claude Code session — no API
key, no config file.

---

## Step 2 — Orient yourself (30 sec)

Ask the hub what's available:

```
what can attune do?
```

The `attune-hub` skill activates and routes you to the workflow that fits your
goal. Use this whenever you're not sure which capability you want.

---

## Step 3 — Run your first real workflow (3 min)

Point it at code you actually care about. Two good first runs:

**Code review** — open a file (or just name it) and ask:

```
review src/payments.py for quality issues and likely bugs
```

The `code-quality` skill spins up a small team of specialist subagents, reads
your real source, and returns prioritized findings with file/line references
and suggested fixes.

**Security audit** — for a vulnerability-focused pass:

```
do a security audit on the src/ directory
```

The `security-audit` skill scans for `eval`/`exec` misuse, hardcoded secrets,
path traversal, and injection risks, then reports each finding with severity
and a fix.

Either one shows you the core pattern in a couple of minutes: **describe the
goal → specialist agents review your real code → you get actionable,
cited findings.**

---

## Step 4 — Go deeper (optional)

Once the basics click, the highest-leverage skill is **spec-driven
development**:

```
/spec
```

This walks you from a rough idea through requirements, design, and an ordered
task list — with human approval gates between phases — then executes the tasks.
It's the recommended path for anything non-trivial.

Other skills worth trying by name or description:

- `smart-test` — "find untested code in this module and write tests for it"
- `refactor-plan` — "this file has too much going on, plan a refactor"
- `release-prep` — "get me ready to cut a release"
- `recall` — "did I hit this problem in a past session?"

---

## What's next

| If you want to… | Go to |
|-----------------|-------|
| Run workflows from a terminal or Python | [First Steps](first-steps.md) |
| Add the full MCP toolset <!-- cap:mcp_registered_tool_count -->(55 tools)<!-- /cap --> + CLI | [MCP Integration](mcp-integration.md) |
| Pick a longer learning path | [Choose Your Path](choose-your-path.md) |
| See every workflow | [First Steps → Try More Workflows](first-steps.md#try-more-workflows) |

!!! note "Plugin vs. package"
    The **plugin** gives you the <!-- cap:skill_count -->25 natural-language skills<!-- /cap --> with zero setup.
    Installing the **Python package** (`pip install attune-ai`) adds the
    `attune` CLI, the MCP server, and <!-- cap:mcp_registered_tool_count -->55 MCP tools<!-- /cap --> on top. You can start with
    the plugin today and add the package later — they layer cleanly.
