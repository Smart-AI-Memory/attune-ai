---
type: reference
subtype: procedural
name: skill-coach
category: skill
tags: [skill, plugin]
source: plugin/skills/coach/SKILL.md
---

# Reference: Skill: coach

Progressive help for any topic. Repeat to go deeper: concept -> procedural -> reference. Triggers on: coach, learn, explain, teach me, tell me more, how does, what is, go deeper.

**Usage:** `/coach <topic | init | status | maintain | update>`

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

## Commands



### Topic Lookup (default)

If the user provided a topic, call:

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

If the user says "tell me more" or "go deeper"
without a new topic, call `help_lookup` with the
same topic again — it auto-advances to the next
level.

If the user says "start from the beginning" or
"reset", call:

```
help_lookup(topic="<topic>", mode="progressive", reset=true)
```

If the user just finished a workflow, use
`last_workflow` to skip the concept and start at
procedural:

```
help_lookup(
    topic="<topic>",
    mode="progressive",
    last_workflow="<workflow-name>"
)
```

For file-based warnings:

```
help_lookup(
    topic="warnings",
    mode="precursor",
    file_path="<path to file>"
)
```

### Init (`/coach init`)

Bootstrap a project-local help system. Two-step
Socratic flow using the `help_init` MCP tool.

**Step 1 — Scan and propose:**

```
help_init(action="scan")
```

This returns a list of proposed features with name,
description, files, tags, confidence, and reason.

Present the proposals to the user as a table:

| Feature | Confidence | Description | Files |
|---------|------------|-------------|-------|

Ask the user (Socratic):

- Which features to keep, rename, or remove?
- Are there features the scanner missed?
- Should any features be merged or split?

**Step 2 — Accept and generate:**

Once the user confirms, pass the accepted list:

```
help_init(
    action="accept",
    accepted=[
        {
            "name": "authentication",
            "description": "User auth and sessions",
            "files": ["src/auth/**"],
            "tags": ["security", "users"]
        },
        ...
    ]
)
```

This creates `.help/features.yaml` and generates
concept, task, and reference templates for each
feature. The response includes a `preamble` for
each feature — display these so the user can
verify the generated summaries are accurate.
Tell the user: "Commit `.help/` to your repo to
share help with your team."

### Status (`/coach status`)

Show which features have stale help templates:

```
help_status()
```

Or check specific features only:

```
help_status(features=["auth", "api"])
```

Present the `report` field as markdown. If stale
features exist, ask: "Want me to regenerate the
stale ones?"

### Maintain (`/coach maintain`)

Full refresh — check all features and regenerate
stale templates.

**Preview what's stale (dry run):**

```
help_update(dry_run=true)
```

**Regenerate stale templates:**

```
help_update()
```

Report the count of stale features found, which
were regenerated, and any failures.

For plugin-internal help maintenance (attune-ai's
own templates in `plugin/help/generated/`), use the
separate `help_maintain` tool:

```
help_maintain(dry_run=false)
```

### Update (`/coach update <feature>`)

Targeted regeneration for one feature:

```
help_update(features=["<feature>"])
```

Report which templates were regenerated and the
result counts.

### Add (`/coach add <feature>`)

Add a new feature to the manifest. Ask the user:

1. Feature name (slug, e.g. "authentication")
2. Description (one line)
3. File patterns (globs)
4. Tags (optional)

Then call `help_init` with the single new feature
added to the accepted list from the existing
manifest. Or use the Write tool to append the
feature directly to `.help/features.yaml`, then
call:

```
help_update(features=["<new-feature-name>"])
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

## Related Topics

_No related topics yet._
