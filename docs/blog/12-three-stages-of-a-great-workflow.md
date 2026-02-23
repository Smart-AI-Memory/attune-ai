---
description: "Build your first AI workflow with Attune — from pip install to running a cost-optimized Claude workflow in under 5 minutes, then build your own in four files."
---

# Build Your First AI Workflow with Attune

**Date:** February 2026
**Author:** Patrick Roebuck
**Tags:** Tutorial, Getting Started, Workflows, Claude

---

## TL;DR

Install Attune AI, run a built-in workflow on your
codebase in 2 minutes, then build your own custom
workflow in four files. Each workflow automatically
routes tasks to the right Claude model — Haiku for
cheap work, Sonnet for balanced tasks, Opus for
premium quality — saving 58%+ vs running everything
on Opus.

---

## Part 1: Get Running (2 Minutes)

### Install

```bash
pip install attune-ai[developer]
```

### Set your API key

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### Run your first workflow

Pick one and try it on your own codebase:

```bash
# Security audit
attune workflow run security-audit --path ./src

# Code review
attune workflow run code-review --path ./src

# Bug prediction
attune workflow run bug-predict --path ./src
```

That's it. Each workflow runs multiple stages,
automatically routing cheap tasks to Haiku and
quality-critical tasks to Opus. You'll see the cost
savings in the output.

### See what's available

```bash
attune workflow list
```

```text
Available workflows:
  security-audit    Security vulnerability scanner
  bug-predict       Bug prediction and risk analysis
  perf-audit        Performance bottleneck detection
  code-review       Code quality analysis
  test-gen          Test case generation
  release-prep      Pre-release quality gates
```

### Use natural language (in Claude Code)

If you use Claude Code, just type `/attune` and describe
what you need:

- "find security vulnerabilities in my auth code"
- "generate tests for src/models/"
- "review my last commit"

Attune asks clarifying questions, then runs the right
workflow.

---

## Part 2: Build Your Own Workflow (15 Minutes)

Every Attune workflow follows the same four-file
pattern. Let's build a documentation generator.

### File 1: The Workflow Class

Create `src/attune/workflows/doc_gen/workflow.py`:

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
  stage. `CHEAP` = Haiku ($0.80/M tokens),
  `CAPABLE` = Sonnet ($3/M), `PREMIUM` = Opus ($15/M).
- **`run_stage()`** — the only method you implement.

This workflow costs roughly **$0.38 per run** vs
**$0.90 on Opus alone** — a 58% reduction. With
Anthropic's automatic prompt caching (cached tokens
cost 10% of standard price), savings compound further.

### File 2: Skill Definition (Natural Language)

Create `plugin/skills/docs/SKILL.md`
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

The `triggers` array connects natural language to your
workflow. When someone types "generate docs for
src/models", the router matches on "docs" and activates
this skill.

### File 3: Command Shortcut

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

Now users have two paths to the same workflow:

- `/attune` + "generate docs" — guided questions first
- `/attune-docs src/` — direct execution

### File 4: Register It

Add one line to `pyproject.toml`:

```toml
[project.entry-points."attune.workflows"]
doc-gen = "attune.workflows.document_gen:DocumentGenerationWorkflow"
```

### Run it

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

You've installed Attune, run a built-in workflow, and
built your own in four files. From here:

- Browse built-in workflows: `attune workflow list`
- Chain workflows: lint, then test, then docs, then
  commit
- Use `/batch` for 50% additional savings on
  non-interactive runs
- Read the
  [full tutorial](../tutorials/build-a-workflow.md)
  for deeper patterns

Every built-in workflow follows the same four-file
pattern you just learned. Browse the
[source](https://github.com/Smart-AI-Memory/attune-ai/tree/main/src/attune/workflows)
for real-world examples.

```bash
pip install attune-ai
attune workflow list
```

---

Patrick Roebuck is the creator of
[Attune AI](https://github.com/Smart-AI-Memory/attune-ai),
an open-source workflow framework for Claude Code.

Version 3.1.2 | February 23, 2026
