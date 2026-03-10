# Build a Workflow from Scratch

Every Attune workflow follows the same pattern: a Python
class with staged execution, a skill file for discovery,
and an entry point for registration. This tutorial walks
through each layer using our documentation generator as
the running example.

By the end you'll know how to build, register, and run
your own cost-optimized workflow.

## What You'll Build

A three-stage documentation workflow that:

1. **Outlines** with Claude Haiku (cheap, fast)
2. **Writes** with Claude Sonnet (balanced)
3. **Polishes** with Claude Opus (highest quality)

Four files make it work:

| File | Purpose |
|------|---------|
| `src/attune/workflows/doc_gen/workflow.py` | Workflow class |
| `plugin/skills/docs/SKILL.md` | Socratic discovery |
| `plugin/commands/attune-docs.md` | Quick-access command |
| `pyproject.toml` | Entry point registration |

## Step 1: Define the Workflow Class

Every workflow extends `BaseWorkflow` and declares three
things: `stages`, `tier_map`, and `run_stage()`.

```python
from attune.workflows.base import BaseWorkflow, ModelTier


class DocumentGenerationWorkflow(BaseWorkflow):
    name = "doc-gen"
    description = "Cost-optimized documentation generation"
    stages = ["outline", "write", "polish"]
    tier_map = {
        "outline": ModelTier.CHEAP,
        "write": ModelTier.CAPABLE,
        "polish": ModelTier.PREMIUM,
    }

    async def run_stage(self, stage_name, tier, input_data):
        if stage_name == "outline":
            return await self._outline(input_data, tier)
        if stage_name == "write":
            return await self._write(input_data, tier)
        if stage_name == "polish":
            return await self._polish(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    async def _outline(self, input_data, tier):
        """Generate a doc outline with Haiku (fast, cheap)."""
        prompt = f"Create a documentation outline for: {input_data['path']}"
        return await self.call_llm(prompt, tier=tier)

    async def _write(self, input_data, tier):
        """Expand the outline into full sections with Sonnet."""
        prompt = f"Write documentation from this outline:\n{input_data['outline']}"
        return await self.call_llm(prompt, tier=tier)

    async def _polish(self, input_data, tier):
        """Final quality pass with Opus."""
        prompt = f"Polish this documentation for clarity and completeness:\n{input_data['draft']}"
        return await self.call_llm(prompt, tier=tier)
```

Three concepts to understand:

- **`stages`** is an ordered list. The execution engine
  runs them in sequence, passing each stage's output to
  the next.
- **`tier_map`** assigns a Claude model to each stage.
  `CHEAP` routes to Claude Haiku, `CAPABLE` to Claude
  Sonnet, and `PREMIUM` to Claude Opus.
- **`run_stage()`** is the only method you implement.
  It receives the stage name, the resolved tier, and
  the input data from the previous stage.

### Why tiers matter

Without tier routing, every stage runs on Claude Opus.
With it, you spend Opus tokens only where quality
demands it:

| Stage | Tier | Claude Model | Input $/1M | Output $/1M |
|-------|------|--------------|------------|-------------|
| outline | CHEAP | Claude Haiku 4.5 | $0.80 | $4.00 |
| write | CAPABLE | Claude Sonnet 4.6 | $3.00 | $15.00 |
| polish | PREMIUM | Claude Opus 4.6 | $15.00 | $75.00 |

A 10,000-token doc generation job costs roughly **$0.38
with tier routing** vs **$0.90 on Claude Opus alone** —
a 58% reduction. Add Anthropic's automatic prompt caching
(cached tokens cost 10% of standard price) and savings
compound further. Scale that across hundreds of workflow
runs and the numbers add up fast.

## Step 2: Create a Skill Definition

Skills give your workflow Socratic discovery -- instead
of memorizing CLI flags, users describe what they need
and the skill asks clarifying questions.

Create `plugin/skills/docs/SKILL.md` (create the
directories if they don't exist yet —
`mkdir -p plugin/skills/docs`):

```yaml
---
name: documentation
description: "Generate, explain, or audit documentation"
triggers:
  - docs
  - documentation
  - readme
  - changelog
  - api reference
  - explain
---
```

Below the frontmatter, define the interaction flow:

```markdown
## Socratic Scoping

Before running, ask:

1. **Type**: "What kind of docs? API reference, README,
   changelog, or a general guide?"
2. **Scope**: "Which path should I document?"
3. **Audience**: "Who's reading -- developers, end users,
   or both?"

## Execution

Call the `document_generation` MCP tool with the scoped
parameters:

document_generation(path="<path>", doc_type="<type>")

## Output Format

Present a summary followed by the generated content:

**Generated:** <doc_type> | **Sections:** N | **Tokens:** X

## Follow-Up

After presenting results, offer:

- "Want me to export this to a file?"
- "Should I refine a specific section?"
- "Want a changelog based on recent commits?"
```

The `triggers` array is what connects natural language
to your skill. When a user types "generate docs for
src/models", the router matches on "docs" and activates
this skill.

> **Pattern reference:**
> [plugin/skills/security-audit/SKILL.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/plugin/skills/security-audit/SKILL.md)

## Step 3: Add a Command Shortcut

Commands bypass Socratic discovery for users who know
exactly what they want. Create
`plugin/commands/attune-docs.md`
(`mkdir -p plugin/commands` if needed):

```yaml
---
name: attune-docs
description: "Generate documentation for a path"
argument-hint: "<path>"
category: workflows
aliases: [adoc]
tags: [docs, documentation, generate]
version: "3.0.0"
---
```

```markdown
# attune-docs

Quick-access command for documentation generation.
Bypasses Socratic discovery when you know the target.

## Execution

1. If a path argument is provided, use it. Otherwise
   ask: "Which path should I document?"
2. Call the `document_generation` MCP tool with the path.
3. Present results using the format from the docs skill.

## Examples

/attune-docs src/attune/models/
/attune-docs src/attune/workflows/
/attune-docs .
```

Now users have two paths to the same workflow:

- `/attune` + "generate docs" -- guided discovery
- `/attune-docs src/` -- direct execution

> **Pattern reference:**
> [plugin/commands/attune-security.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/plugin/commands/attune-security.md)

## Step 4: Register the Entry Point

Add your workflow to `pyproject.toml` so the CLI can
discover it:

```toml
[project.entry-points."attune.workflows"]
doc-gen = "attune.workflows.document_gen:DocumentGenerationWorkflow"
```

Verify it's registered:

```bash
attune workflow list
```

You should see your workflow in the output:

```text
Available workflows:
  security-audit    Security vulnerability scanner
  bug-predict       Bug prediction and risk analysis
  perf-audit        Performance bottleneck detection
  code-review       Code quality analysis
  doc-gen           Cost-optimized documentation generation  ← yours
```

Run it:

```bash
attune workflow run doc-gen --path src/attune/models/
```

Expected output:

```text
Running doc-gen workflow...
  Stage 1/3: outline (Haiku 4.5)  ✓  0.8s
  Stage 2/3: write (Sonnet 4.6)   ✓  3.2s
  Stage 3/3: polish (Opus 4.6)    ✓  5.1s

Cost: $0.38 (saved 58% vs premium-only baseline)
```

The CLI loads your class, instantiates it, calls
`execute()`, and formats the result — including cost
savings vs a premium-only baseline.

## Step 5: Build Your Own

You now know every layer of the system. To build your
own workflow:

1. **Pick your stages.** What are the distinct steps?
   A code reviewer might use `scan`, `analyze`, `report`.
2. **Assign tiers.** Which stages need Claude Opus
   (PREMIUM) vs Claude Haiku speed (CHEAP)?
3. **Implement `run_stage()`.** Each stage receives the
   previous stage's output.
4. **Add a SKILL.md.** Define triggers and Socratic
   questions.
5. **Register in pyproject.toml.** One line.

Browse existing workflows for inspiration:

```bash
attune workflow list
```

### Ideas to try

- Chain workflows: lint, then test, then docs, then
  commit
- Use `/bulk` for 50% savings on non-interactive runs
- Add custom mixins for shared logic across workflows

## Recap

You built a complete workflow in four files:

1. **Workflow class** — staged execution with tier routing
2. **Skill definition** — Socratic discovery via triggers
3. **Command shortcut** — direct access for power users
4. **Entry point** — one line in `pyproject.toml`

Every built-in Attune workflow follows this same pattern.
Browse the source for `security-audit`, `code-review`, or
`perf-audit` to see real-world variations — then build
your own.
