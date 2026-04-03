---
name: learn
description: "Progressive help for any topic. Repeat to go deeper: concept -> procedural -> reference. Triggers on: learn, explain, tell me more, how does, what is, help with, deeper."
---
# Learn

**IMPORTANT: Start your response by telling the user:**

> **Learn** — Explains any Attune topic with progressive depth — concept, then how-to, then full reference.

## How It Works

Each depth level serves a **different type** of content,
not just more of the same:

| Level | Type | What you get |
|-------|------|-------------|
| 0 | Concept | What is it? When to use it? |
| 1 | Procedural | Step-by-step: how to run it |
| 2 | Reference | Full detail, edge cases, links |

Repeated calls on the same topic auto-advance. A new
topic resets to concept.

## Execution

1. If the user provided a topic, call:

```
help_lookup(topic="<topic>", mode="progressive")
```

Use the bare topic slug — the engine resolves the
right template type at each level:

| User says | Topic slug |
|-----------|-----------|
| security audit | `security-audit` |
| code review | `code-review` |
| code quality | `code-quality` |
| bug predict | `bug-predict` |
| test gen | `test-generation` |
| release | `release-prep` |
| refactor | `refactor-plan` |
| doc gen | `doc-gen` |

2. If the user says "tell me more" or "go deeper"
   without a new topic, call `help_lookup` with the
   same topic again — it auto-advances to the next
   level.

3. If the user says "start from the beginning" or
   "reset", call:

```
help_lookup(topic="<topic>", mode="progressive", reset=true)
```

4. If the user just finished a workflow, use
   `last_workflow` to skip the concept and start at
   procedural:

```
help_lookup(
    topic="<topic>",
    mode="progressive",
    last_workflow="<workflow-name>"
)
```

5. For file-based warnings:

```
help_lookup(
    topic="warnings",
    mode="precursor",
    file_path="<path to file>"
)
```

## Output

Present the returned `body` as-is (it's already
formatted markdown). Append the level indicator:

- Level 0: "(concept view — say 'tell me more' for
  step-by-step guide)"
- Level 1: "(procedural view — say 'tell me more'
  for full reference)"
- Level 2: "(reference view — full detail)"

If the result includes `related` entries, list them
as suggested next reads.

## Maintenance Mode

If the user says "update help", "refresh templates",
"maintain knowledge base", or "check for stale docs":

Preview what's stale:

```
help_maintain(dry_run=true)
```

Regenerate stale templates:

```
help_maintain(dry_run=false)
```

Report the count of stale templates found, which
types were regenerated, and whether validation passed.

For bulk updates (requires API key):

```
help_maintain(batch=true, dry_run=false)
```

This submits regeneration tasks asynchronously via
the Anthropic Batch API. Requires `ANTHROPIC_API_KEY`
and the `attune-ai` Python package installed.
