---
type: concept
name: task-precursor-warning-design
tags: [precursor, warnings, help-system, patterns]
source: developer-guidance
---

# Precursor Warning Design

A precursor warning is help that surfaces before you hit
a problem. Instead of waiting for an error and then
explaining what went wrong, the help system detects what
you are about to do and warns you proactively.

## Precursors vs error templates

The help system has two response modes. Understanding the
difference is the key to designing effective warnings.

| Aspect | Precursor warning | Error template |
|--------|-------------------|----------------|
| **When it fires** | Before the mistake | After the failure |
| **Trigger** | File extension, filename, content pattern | Error message, stack trace |
| **Tone** | Heads-up, advisory | Diagnostic, corrective |
| **User state** | Working normally, about to take a risk | Stuck, frustrated, needs a fix |
| **Template prefixes** | `war-`, `con-task-`, `tas-task-`, `ref-task-`, `qui-task-` | `err-` |
| **Example** | "`.env` files should never be committed -- add it to `.gitignore`" | "`ModuleNotFoundError` -- your `.env` was not loaded" |

Precursors are cheaper than errors. A one-line heads-up
at the right moment saves a developer from a 30-minute
debugging session.

## How the trigger chain works

The help engine maps files to warnings through a three-
step chain:

```
File being edited
    --> extension or filename match
    --> tags assigned
    --> templates with those tags surface
```

### Step 1: File to tags

The engine maintains two maps in `precursor_warnings()`:

| Map | Key | Example | Tags assigned |
|-----|-----|---------|---------------|
| **Extension map** | `.py` | `main.py` | `python`, `imports`, `testing`, `error-handling` |
| **Extension map** | `.env` | `.env.local` | `config`, `secrets` |
| **Extension map** | `.yml` | `ci.yml` | `ci`, `github-actions` |
| **Filename map** | `pyproject.toml` | `pyproject.toml` | `deps`, `publishing`, `packaging` |
| **Filename map** | `.gitignore` | `.gitignore` | `git` |
| **Filename map** | `dockerfile` | `Dockerfile` | `ci`, `cd` |

Both maps fire. Editing `pyproject.toml` matches the
`.toml` extension (tags: `packaging`, `python`,
`publishing`) and the filename (tags: `deps`,
`publishing`, `packaging`). Duplicate tags increase the
score, which is intentional -- more signal means more
relevance.

### Step 2: Tags to templates

The `tag_index` in `cross_links.json` maps each tag to
template IDs. Only templates with specific prefixes are
eligible for precursor warnings:

| Prefix | Template type | Verbosity |
|--------|---------------|-----------|
| `war-` | Warning | Compact |
| `err-` | Error | Compact |
| `con-task-` | Concept (task-category) | Normal |
| `tas-task-` | Task (task-category) | Normal |
| `ref-task-` | Reference (task-category) | Normal |
| `qui-task-` | Quickstart (task-category) | Normal |

### Step 3: Scoring and ranking

Each matching template gets a score:

- **+1** per matching tag
- **+10** if the template ID contains `task-` (the
  task-category boost)

Task-category templates score higher because they are
guidance -- they tell you how to do something right.
Warning and error templates are reactive; task-category
templates are educational.

## Why proactive beats reactive

When a developer opens `.env` and sees "remember to
gitignore this," the cost is zero -- they were going to
edit the file anyway. When the same developer commits
the `.env` and a secret scanner fires in CI, the cost
is a pipeline failure, a secret rotation, and 45 minutes
of cleanup.

The entire Lessons Learned section of this project's
CLAUDE.md exists because problems were not caught
proactively. Each lesson is a candidate for a precursor
warning.

## Want to learn more?

- Say **"how do I add a precursor warning?"** for the
  step-by-step guide
- Say **"show me all the mappings"** for the complete
  file-to-tag and tag-to-template reference
- Say **"I need to add a proactive warning"** for a
  5-step quickstart
- Read `engine.py:precursor_warnings()` for the
  implementation

## Related Topics

- **Task**: Precursor warning design -- step-by-step
  guide for adding a new precursor warning
- **Reference**: Precursor warning design -- all file
  mappings, tag conventions, and scoring rules
- **Quickstart**: Precursor warning design -- 5-step
  guide to add a proactive warning
