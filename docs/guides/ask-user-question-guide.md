# AskUserQuestion Guide

A practical reference for using `AskUserQuestion` in Claude Code
and in Attune AI's Socratic workflows — from basic label+description
questions up to the preview feature with rendered markdown.

---

## Table of Contents

1. [Overview](#overview)
2. [Full Parameter Reference](#full-parameter-reference)
3. [Example 1: Basic Single-Select](#example-1-basic-single-select)
4. [Example 2: Multi-Select](#example-2-multi-select)
5. [Example 3: Multiple Questions at Once](#example-3-multiple-questions-at-once)
6. [Example 4: Preview Feature](#example-4-preview-feature)
7. [Example 5: Socratic Discovery Pattern](#example-5-socratic-discovery-pattern)
8. [How Attune AI Uses This Tool](#how-attune-ai-uses-this-tool)
9. [Common Mistakes](#common-mistakes)

---

## Overview

`AskUserQuestion` presents structured questions to the user inside
VS Code / Claude Code. The UI renders each question as a chip/tag
header with a list of selectable options.

There are two rendering modes:

| Mode | When it activates | Layout |
|------|-------------------|--------|
| Standard | Default | Full-width option list |
| Preview | Any option has a `markdown` field | Left: options, Right: preview panel |

The tool accepts 1–4 questions per call. Attune AI's
`SocraticFormEngine` batches larger question sets automatically
(see [src/attune/meta_workflows/form_engine.py](../src/attune/meta_workflows/form_engine.py)).

---

## Full Parameter Reference

```python
AskUserQuestion(questions=[
    {
        # Required
        "question":    str,   # Full question text shown to user
        "header":      str,   # Short chip label — max 12 characters
        "options":     list,  # 2–4 choices (see option fields below)
        "multiSelect": bool,  # True = multiple selections allowed

        # Each option supports:
        # {
        #   "label":       str,  # Short display text (1–5 words)
        #   "description": str,  # Explanation of the choice
        #   "markdown":    str,  # Optional — triggers preview panel
        # }
    }
])
```

**Return value:** `dict` mapping each `header` string to the
user's selected `label` (or list of labels if `multiSelect=True`).

---

## Example 1: Basic Single-Select

The simplest case — one question, no preview, single answer.

### Code

```python
response = AskUserQuestion(questions=[
    {
        "question": "Which test suite should we run?",
        "header": "Test scope",
        "multiSelect": False,
        "options": [
            {
                "label": "Quick smoke",
                "description": "Unit tests only (~30 seconds)"
            },
            {
                "label": "Full suite",
                "description": "All tests including integration (~5 minutes)"
            },
            {
                "label": "CLI only",
                "description": "Just the CLI command tests"
            }
        ]
    }
])

scope = response["Test scope"]  # e.g. "Quick smoke"
```

### VS Code Appearance

```
┌─────────────────────────────────────────┐
│ Which test suite should we run?         │
│                                         │
│  ● Quick smoke                          │
│    Unit tests only (~30 seconds)        │
│                                         │
│  ○ Full suite                           │
│    All tests including integration      │
│    (~5 minutes)                         │
│                                         │
│  ○ CLI only                             │
│    Just the CLI command tests           │
│                                         │
│  [ Other ]               [ Submit ]     │
└─────────────────────────────────────────┘
```

**Reading the response:**

```python
if scope == "Quick smoke":
    run_quick_tests()
elif scope == "Full suite":
    run_all_tests()
```

---

## Example 2: Multi-Select

Allow the user to pick more than one option. Note: `multiSelect`
questions **cannot** use the preview feature.

### Code

```python
response = AskUserQuestion(questions=[
    {
        "question": "Which areas should the security audit cover?",
        "header": "Audit scope",
        "multiSelect": True,
        "options": [
            {
                "label": "src/",
                "description": "Main library source code"
            },
            {
                "label": "tests/",
                "description": "Test files and fixtures"
            },
            {
                "label": "scripts/",
                "description": "Build and utility scripts"
            },
            {
                "label": "Full project",
                "description": "Everything including docs and config"
            }
        ]
    }
])

selected = response["Audit scope"]  # e.g. ["src/", "tests/"]
```

### VS Code Appearance

```
┌─────────────────────────────────────────┐
│ Which areas should the security audit   │
│ cover?                                  │
│                                         │
│  ☑ src/                                │
│    Main library source code             │
│                                         │
│  ☑ tests/                              │
│    Test files and fixtures              │
│                                         │
│  ☐ scripts/                            │
│    Build and utility scripts            │
│                                         │
│  ☐ Full project                        │
│    Everything including docs and config │
│                                         │
│  [ Other ]               [ Submit ]     │
└─────────────────────────────────────────┘
```

**Reading the response:**

```python
for path in selected:
    run_audit(path)
```

---

## Example 3: Multiple Questions at Once

Up to 4 questions can be asked in a single call. They render
as a sequence the user works through.

### Code

```python
response = AskUserQuestion(questions=[
    {
        "question": "What kind of change is this?",
        "header": "Change type",
        "multiSelect": False,
        "options": [
            {"label": "Feature",    "description": "New functionality"},
            {"label": "Bug fix",    "description": "Fixing broken behavior"},
            {"label": "Refactor",   "description": "No behavior change"},
            {"label": "Chore",      "description": "Deps, CI, tooling"},
        ]
    },
    {
        "question": "Which files should be staged?",
        "header": "Stage files",
        "multiSelect": False,
        "options": [
            {"label": "All changes", "description": "git add -A"},
            {"label": "src/ only",   "description": "Only source files"},
            {"label": "I'll choose", "description": "Let me pick manually"},
        ]
    }
])

change_type = response["Change type"]   # e.g. "Bug fix"
staging     = response["Stage files"]   # e.g. "src/ only"
```

### Limit

The `SocraticFormEngine` in Attune AI enforces a batch size of 4:

```python
# src/attune/meta_workflows/form_engine.py:84
batches = form_schema.get_question_batches(batch_size=4)
```

If you need more than 4 questions, split them into sequential
calls.

---

## Example 4: Preview Feature

Add a `markdown` field to options when users need to see actual
content — code, config, layouts — before choosing. The UI
switches to a side-by-side panel automatically.

**Requirements:**

- `multiSelect` must be `False`
- At least one option must have a `markdown` field
- Content renders with syntax highlighting

### Code

```python
response = AskUserQuestion(questions=[
    {
        "question": "Which execution strategy should this workflow use?",
        "header": "Execution",
        "multiSelect": False,
        "options": [
            {
                "label": "Sequential",
                "description": "Steps run one at a time, stops on failure",
                "markdown": (
                    "```python\n"
                    "for step in workflow.steps:\n"
                    "    result = await step.run()\n"
                    "    if result.failed:\n"
                    "        break\n"
                    "```"
                )
            },
            {
                "label": "Parallel",
                "description": "All steps run concurrently, faster",
                "markdown": (
                    "```python\n"
                    "results = await asyncio.gather(\n"
                    "    *[step.run() for step in workflow.steps]\n"
                    ")\n"
                    "```"
                )
            },
            {
                "label": "Progressive",
                "description": "Cheap model first, escalates if needed",
                "markdown": (
                    "```python\n"
                    "result = await cheap_model.run(step)\n"
                    "if result.needs_escalation:\n"
                    "    result = await premium_model.run(step)\n"
                    "```"
                )
            }
        ]
    }
])

strategy = response["Execution"]
```

### VS Code Appearance

```
┌───────────────────────┬─────────────────────────────────────────┐
│                       │                                         │
│  ● Sequential         │  for step in workflow.steps:           │
│    Steps run one at   │      result = await step.run()         │
│    a time, stops on   │      if result.failed:                 │
│    failure            │          break                         │
│                       │                                         │
│  ○ Parallel           │                                         │
│    All steps run      │                                         │
│    concurrently,      │                                         │
│    faster             │                                         │
│                       │                                         │
│  ○ Progressive        │                                         │
│    Cheap model first, │                                         │
│    escalates if       │                                         │
│    needed             │                                         │
│                       │                                         │
├───────────────────────┴─────────────────────────────────────────┤
│  [ Other ]                                        [ Submit ]    │
└─────────────────────────────────────────────────────────────────┘
```

When the user hovers over **Parallel**, the right panel updates:

```
┌───────────────────────┬─────────────────────────────────────────┐
│                       │                                         │
│  ○ Sequential         │  results = await asyncio.gather(        │
│    ...                │      *[step.run()                       │
│                       │        for step in workflow.steps]      │
│  ● Parallel           │  )                                      │
│    All steps run      │                                         │
│    concurrently,      │                                         │
│    faster             │                                         │
│                       │                                         │
│  ○ Progressive        │                                         │
│    ...                │                                         │
└───────────────────────┴─────────────────────────────────────────┘
```

### Preview with ASCII Layout Mockup

The `markdown` field isn't limited to code blocks. You can show
ASCII UI mockups, config files, or comparison tables:

```python
{
    "label": "Dashboard layout",
    "description": "Full-width with sidebar",
    "markdown": (
        "```\n"
        "┌──────────┬──────────────────┐\n"
        "│ Sidebar  │   Main Content   │\n"
        "│          │                  │\n"
        "│ Nav item │  Chart / Table   │\n"
        "│ Nav item │                  │\n"
        "│ Nav item │  Stats row       │\n"
        "└──────────┴──────────────────┘\n"
        "```"
    )
}
```

---

## Example 5: Socratic Discovery Pattern

Attune AI uses a multi-round question pattern to discover intent
before executing anything. This is the core UX principle: ask
first, execute second.

### Pattern

```python
# Round 1: Discover the goal
round1 = AskUserQuestion(questions=[
    {
        "question": "What are you trying to accomplish?",
        "header": "Goal",
        "multiSelect": False,
        "options": [
            {"label": "Run tests",      "description": "Execute test suite"},
            {"label": "Security audit", "description": "Scan for vulnerabilities"},
            {"label": "Commit",         "description": "Stage and commit changes"},
            {"label": "Code review",    "description": "Review quality and issues"},
        ]
    }
])

goal = round1["Goal"]

# Round 2: Scope the goal (based on round 1)
if goal == "Run tests":
    round2 = AskUserQuestion(questions=[
        {
            "question": "Which tests?",
            "header": "Test scope",
            "multiSelect": False,
            "options": [
                {"label": "Quick smoke", "description": "Unit tests (~30s)"},
                {"label": "Full suite",  "description": "All tests (~5min)"},
                {"label": "CLI only",    "description": "CLI command tests"},
            ]
        }
    ])
    run_tests(round2["Test scope"])

elif goal == "Security audit":
    round2 = AskUserQuestion(questions=[
        {
            "question": "Which path to audit?",
            "header": "Audit path",
            "multiSelect": False,
            "options": [
                {"label": "src/",         "description": "Source code only"},
                {"label": "Full project", "description": "Everything"},
            ]
        }
    ])
    run_audit(round2["Audit path"])
```

### How Attune AI Implements This

The `socratic_router.py` handles round 1 intent classification
and the `SocraticFormEngine` handles the follow-up form rounds:

```
User types /attune
    → classify_intent(user_response)        # socratic_router.py
    → AskUserQuestion (intent options)      # round 1
    → SocraticFormEngine.ask_questions()    # round 2+
    → workflow execution
```

See [src/attune/socratic_router.py](../src/attune/socratic_router.py)
and [src/attune/meta_workflows/form_engine.py](../src/attune/meta_workflows/form_engine.py).

---

## How Attune AI Uses This Tool

| File | Role |
|------|------|
| [src/attune/tools.py](../src/attune/tools.py) | Wraps `AskUserQuestion` with IPC and custom handler support |
| [src/attune/meta_workflows/form_engine.py](../src/attune/meta_workflows/form_engine.py) | Batches questions (max 4), converts `FormQuestion` to AskUserQuestion format |
| [src/attune/socratic_router.py](../src/attune/socratic_router.py) | Routes natural language intent to question options |
| [src/attune/wizards/base.py](../src/attune/wizards/base.py) | Uses questions to guide multi-step wizard flows |

The `header` field doubles as the response key. The
`create_header_from_question()` helper in `form_engine.py`
auto-generates short headers from question text
(e.g. "Do you have tests?" → `"Tests"`).

---

## Common Mistakes

### 1. Using `multiSelect: True` with `markdown`

The preview feature is **single-select only**. If you add
`markdown` to options on a multi-select question, the preview
panel will not appear.

```python
# Wrong — preview won't render
{
    "multiSelect": True,
    "options": [
        {"label": "A", "markdown": "..."},  # ignored
    ]
}

# Right — use single-select for preview
{
    "multiSelect": False,
    "options": [
        {"label": "A", "markdown": "..."},  # renders
    ]
}
```

### 2. Header longer than 12 characters

The `header` is displayed as a chip/tag. Anything over 12
characters gets clipped.

```python
# Wrong
"header": "Change type here"   # 17 chars — clipped

# Right
"header": "Change type"        # 11 chars — fits
```

### 3. Asking more than 4 questions at once

The tool accepts 1–4 questions per call. Pass more than 4 and
the call will fail. Batch them:

```python
# Wrong
AskUserQuestion(questions=[q1, q2, q3, q4, q5])  # 5 — error

# Right
AskUserQuestion(questions=[q1, q2, q3, q4])
AskUserQuestion(questions=[q5])
```

### 4. Reading the response with the wrong key

The response dict is keyed by `header`, not by `question`.

```python
response = AskUserQuestion(questions=[
    {"header": "Scope", "question": "Which scope?", ...}
])

# Wrong
value = response["Which scope?"]   # KeyError

# Right
value = response["Scope"]
```

### 5. Skipping the question and executing directly

This violates the Socratic principle. Always ask before acting —
especially for destructive operations like commits, deletions,
or audits that cover a wide scope.

```python
# Wrong — assumes user wants full suite
run_all_tests()

# Right — ask first
response = AskUserQuestion(...)
if response["Test scope"] == "Full suite":
    run_all_tests()
```
