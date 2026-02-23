---
description: "The Three Stages of a Great AI Workflow: cut costs with Haiku, simplify with Sonnet, polish with Opus. Build your own in four files."
---

# The Three Stages of a Great AI Workflow

**Date:** February 2026
**Author:** Patrick Roebuck
**Tags:** Workflows, Claude, Cost Optimization, Tutorial

---

## TL;DR

Every good AI workflow has three layers: **cut costs**
(route cheap tasks to Haiku), **simplify the work**
(let the framework handle orchestration), and **polish
the output** (spend Opus tokens where quality matters).
This maps directly to Claude's three model tiers — and
to the four-file pattern every Attune workflow uses.
Build your own in ~15 minutes.

---

## The Problem: One Model for Everything

Most developers start with a single Claude API call.
It works. Then they add another. Then five more. Before
long, they're spending $20/month on Opus calls for tasks
that Haiku could handle in 200 milliseconds.

We noticed this pattern in our own work, so we built
Attune AI around a simple idea: **every good AI workflow
has three layers.** Not coincidentally, those layers map
to the three tiers of Claude models — and to the three
things developers actually care about.

---

## Stage 1: Cut the Cost

The first thing you notice when you start routing tasks
to the right model is how much money you were wasting.

Claude Haiku 4.5 costs $0.80 per million input tokens.
Claude Opus 4.6 costs $15.00. That's nearly **19x more
expensive** — and for tasks like generating an outline,
extracting metadata, or triaging inputs, Haiku does the
job in a fraction of the time.

In Attune, every workflow declares a `tier_map` that
assigns a Claude model to each stage:

```python
tier_map = {
    "outline": ModelTier.CHEAP,     # Haiku
    "write":   ModelTier.CAPABLE,   # Sonnet
    "polish":  ModelTier.PREMIUM,   # Opus
}
```

A 10,000-token documentation job costs roughly **$0.38
with tier routing** vs **$0.90 on Opus alone** — a 58%
reduction. Add Anthropic's automatic prompt caching
(cached tokens cost 10% of standard price) and the
savings compound further.

**The lesson:** Don't pay premium prices for commodity
work. Route cheap tasks to cheap models. Save your
budget for the stages that actually need it.

---

## Stage 2: Simplify the Work

Cost savings get your attention. Ease of use is what
keeps you building.

The hardest part of any multi-model workflow isn't the
API call — it's the orchestration. Which model handles
which step? How does output flow between stages? What
happens when a stage fails?

Attune handles this with a single method: `run_stage()`.
You implement it once, and the execution engine handles
sequencing, tier resolution, and error recovery:

```python
class DocumentGenerationWorkflow(BaseWorkflow):
    name = "doc-gen"
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
```

That's the entire workflow. No orchestration library.
No DAG configuration. No YAML pipeline definitions.
One class, one method, and the framework runs it:

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

**The lesson:** Good tooling makes the right thing the
easy thing. When tier routing is baked into the
framework, you don't have to think about it — you just
define your stages and the costs take care of themselves.

---

## Stage 3: Polish the Output

Here's where Opus earns its price.

The first two stages are about efficiency: spend less,
build faster. The third stage is about quality — and
it's the one that separates a useful tool from a great
one.

In a documentation workflow, the polish stage rewrites
for clarity, fixes inconsistencies, and ensures the
output reads like it was written by a human who cares.
In a security audit, it's the stage that catches the
subtle vulnerability the cheaper models missed. In a
code review, it's the nuanced feedback about
architecture that goes beyond "add a docstring here."

You don't need Opus for everything. But when you need
it, nothing else will do.

The tier system makes this tradeoff explicit:

```python
# Fast and cheap: Haiku handles the scaffolding
"scan":    ModelTier.CHEAP

# Balanced: Sonnet does the heavy lifting
"analyze": ModelTier.CAPABLE

# Premium: Opus delivers the final judgment
"report":  ModelTier.PREMIUM
```

**The lesson:** Spend your premium tokens where they
have the most impact. One stage of Opus polish on top
of two stages of efficient work produces better output
than three stages of Opus alone — because the final
pass has cleaner input to work with.

---

## The Pattern Behind the Pattern

If the structure of this post felt familiar, that's
because it follows the same three-stage pattern we've
been describing:

1. **Hook** (fast and cheap) — Cost savings grabbed
   your attention
2. **Substance** (balanced) — Ease of use gave you
   something to work with
3. **Polish** (premium) — Quality of output made you
   want to try it

That's not an accident. The best workflows — whether
they're generating documentation, reviewing code, or
writing blog posts — follow this shape. Start broad and
cheap, narrow with capable work, finish with premium
quality.

Every Attune workflow is built from four files:

1. **A workflow class** — stages, tiers, and one method
2. **A skill definition** — natural language triggers
   for Socratic discovery
3. **A command shortcut** — direct access for power
   users
4. **An entry point** — one line in `pyproject.toml`

If you want to build your own, the
[Build a Workflow](../tutorials/build-a-workflow.md)
tutorial walks through each layer. The whole thing
takes about 15 minutes.

---

## Try It

```bash
pip install attune-ai
attune workflow list
attune workflow run security-audit --path ./src
```

Browse the source, build a workflow, and see what three
stages can do.

---

**About the Author**

Patrick Roebuck is the creator of Attune AI, an
open-source workflow framework for Claude Code.

**Framework Version:** 3.1.2
**Published:** February 23, 2026
