---
description: "Type /attune in Claude Code, answer two questions, and run a cost-optimized security audit in under a minute. Then build your own workflow in four files."
---

# Build Your First AI Workflow with Attune and Claude Code

**Date:** February 2026
**Author:** Patrick Roebuck
**Tags:** Tutorial, Getting Started, Claude Code, Workflows

---

## TL;DR

Install Attune AI, type `/attune` in Claude Code, and
describe what you need. Attune asks scoping questions,
picks the right workflow, and runs it with automatic
cost optimization across Claude's three model tiers.
12 workflows ship out of the box. Build your own in
four files.

---

## Part 1: Install and Run (Under 2 Minutes)

### Setup

Three commands:

```bash
pip install attune-ai[developer]
export ANTHROPIC_API_KEY="your-key-here"
attune setup
```

The `attune setup` wizard walks you through
configuration in 6 stages. Want to skip it? Use a
preset:

```bash
attune setup --preset code-review
```

### Your first workflow — the Socratic way

Open Claude Code in your project and type:

```text
/attune
```

Attune doesn't dump a menu. It asks what you're trying
to accomplish:

> **What are you trying to accomplish?**
>
> - **Fix or improve code** — Debug, review, refactor
> - **Validate my work** — Tests, coverage, security
> - **Ship my changes** — Plan, release, publish
> - **Create or extend** — Wizards, agents, docs

Pick "Validate my work." Attune narrows it down:

> **Which validation?**
>
> - `/testing run` — Run test suite
> - `/testing coverage` — Coverage report
> - `/workflows security` — Security scan
> - `/workflows perf` — Performance detection

Pick "Security." One more question:

> **What target?** `src/`, a specific module, or full
> project?

You type `src/attune/models/`. Attune runs the security
audit — scanning for eval, path traversal, injection
risks — and reports back with findings, severity levels,
and cost savings.

That's the core experience: **describe your goal,
answer scoping questions, get results.** No commands
to memorize.

### Skip the questions when you know what you want

Once you're familiar with the workflows, go direct:

```text
/attune security src/attune/models/
```

Or from the CLI:

```bash
attune workflow run security-audit --path src/attune/models/
```

Both run the same workflow. The Socratic path is for
discovery; the direct path is for speed.

### What's available

Attune ships with 12 workflows:

| Workflow | What it does |
|----------|-------------|
| `security-audit` | OWASP vulnerability scan with risk scoring |
| `code-review` | Tiered analysis with architectural review |
| `bug-predict` | Predicts likely bugs from code patterns |
| `perf-audit` | Bottlenecks and optimization opportunities |
| `test-gen` | Tests targeting low-coverage areas |
| `doc-gen` | Documentation via outline/write/polish |
| `refactor-plan` | Prioritizes tech debt by impact |
| `dependency-check` | Vulnerability and license auditing |
| `release-prep` | Pre-release quality gate |
| `secure-release` | Security pipeline for release approval |
| `pro-review` | Composite multi-pass review |
| `pr-review` | PR-level quality and security analysis |

All accessible through `/attune` + natural language,
or directly by name.

---

## Part 2: What's Happening Under the Hood

Every workflow runs in stages, and each stage is routed
to a different Claude model based on what the task
needs.

Take the `doc-gen` workflow. It runs three stages:

1. **Outline** — Claude Haiku (fast, $0.80/M tokens)
2. **Write** — Claude Sonnet (balanced, $3/M tokens)
3. **Polish** — Claude Opus (premium, $15/M tokens)

The result: **$0.38 per run vs $0.90 on Opus alone —
a 58% cost reduction.** Add Anthropic's automatic
prompt caching (cached tokens cost 10% of standard
price) and savings compound further.

Here's the actual workflow class:

```python
from attune.workflows.base import BaseWorkflow, ModelTier


class DocumentGenerationWorkflow(BaseWorkflow):
    name = "doc-gen"
    description = "Cost-optimized documentation generation"
    stages = ["outline", "write", "polish"]
    tier_map = {
        "outline": ModelTier.CHEAP,     # Haiku
        "write": ModelTier.CAPABLE,     # Sonnet
        "polish": ModelTier.PREMIUM,    # Opus
    }

    async def run_stage(
        self, stage_name, tier, input_data
    ):
        if stage_name == "outline":
            return await self._outline(input_data, tier)
        if stage_name == "write":
            return await self._write(input_data, tier)
        if stage_name == "polish":
            return await self._polish(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    async def _outline(self, input_data, tier):
        """Generate a doc outline with Haiku."""
        prompt = (
            "Create a documentation outline for: "
            f"{input_data['path']}"
        )
        return await self.call_llm(prompt, tier=tier)

    async def _write(self, input_data, tier):
        """Expand outline into full sections."""
        prompt = (
            "Write documentation from this outline:\n"
            f"{input_data['outline']}"
        )
        return await self.call_llm(prompt, tier=tier)

    async def _polish(self, input_data, tier):
        """Final quality pass with Opus."""
        prompt = (
            "Polish this documentation for clarity "
            f"and completeness:\n{input_data['draft']}"
        )
        return await self.call_llm(prompt, tier=tier)
```

Three things to understand:

- **`stages`** — runs in sequence. Each stage's output
  becomes the next stage's input.
- **`tier_map`** — assigns a Claude model to each
  stage. `CHEAP` = Haiku, `CAPABLE` = Sonnet,
  `PREMIUM` = Opus.
- **`run_stage()`** — the only method you implement.
  The framework handles sequencing, tier resolution,
  and cost tracking.

Every built-in workflow follows this same pattern.

---

## Part 3: Build Your Own Workflow

You've run workflows and seen the code. Now let's
build one. Every Attune workflow is four files.

### File 1: Workflow class

The code above — your stages, tier assignments, and
`run_stage()` implementation. Create it at
`src/attune/workflows/doc_gen/workflow.py`.

### File 2: Skill definition (for `/attune` discovery)

This is what makes your workflow discoverable through
natural language — the Socratic flow you experienced
in Part 1. Create `plugin/skills/docs/SKILL.md`
(`mkdir -p plugin/skills/docs`):

```yaml
---
name: documentation
description: "Generate, explain, or audit documentation"
triggers:
  - docs
  - documentation
  - readme
  - changelog
  - explain
---
```

The `triggers` array connects natural language to your
workflow. When someone types `/attune` and says
"generate docs for src/models", the router matches on
"docs" and activates this skill.

Below the frontmatter, define the scoping questions:

```markdown
## Socratic Scoping

Before running, ask:

1. "What kind of docs? API reference, README,
   changelog, or guide?"
2. "Which path should I document?"
3. "Who's reading — developers, end users, or both?"

## Follow-Up

- "Want me to export this to a file?"
- "Should I refine a specific section?"
```

### File 3: Command shortcut (for direct access)

Create `plugin/commands/attune-docs.md`
(`mkdir -p plugin/commands`):

```yaml
---
name: attune-docs
description: "Generate documentation for a path"
argument-hint: "<path>"
category: workflows
aliases: [adoc]
tags: [docs, documentation, generate]
---
```

Now your workflow has two entry points:

- `/attune` + "generate docs" — guided discovery
- `/attune-docs src/` — direct execution

### File 4: Register it

One line in `pyproject.toml`:

```toml
[project.entry-points."attune.workflows"]
doc-gen = "attune.workflows.document_gen:DocumentGenerationWorkflow"
```

### Run it

In Claude Code:

```text
/attune generate docs for src/attune/models/
```

Or from the CLI:

```bash
attune workflow run doc-gen --path src/attune/models/
```

```text
Running doc-gen workflow...
  Stage 1/3: outline (Haiku 4.5)  ✓  0.8s
  Stage 2/3: write (Sonnet 4.6)   ✓  3.2s
  Stage 3/3: polish (Opus 4.6)    ✓  5.1s

Cost: $0.38 (saved 58% vs premium-only baseline)
```

---

## What's Next

You've installed Attune, run built-in workflows through
Claude Code's Socratic interface, and built your own in
four files. From here:

- Type `/attune` and explore more workflows
- Chain workflows: lint, then test, then docs, then
  commit
- Use `/batch` for 50% additional savings on
  non-interactive runs
- Read the
  [full tutorial](../tutorials/build-a-workflow.md)
  for deeper patterns
- Browse the
  [source](https://github.com/Smart-AI-Memory/attune-ai/tree/main/src/attune/workflows)
  to see how built-in workflows work

```bash
pip install attune-ai[developer]
attune setup
```

---

Patrick Roebuck is the creator of
[Attune AI](https://github.com/Smart-AI-Memory/attune-ai),
an open-source workflow framework for Claude Code.

Version 3.1.2 | February 23, 2026
