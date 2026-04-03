---
type: task
name: task-socratic-discovery-patterns
tags: [socratic, discovery, ux, patterns]
source: developer-guidance
---

# Task: Add Socratic discovery to a skill

Implement question-first scoping in a skill or tool so
users get focused results instead of firehose output.
This guide uses a code review skill as the running
example.

## Prerequisites

- A skill or tool that accepts user input
- Understanding of `AskUserQuestion` (2-4 options per
  question, one question at a time)

## Steps

### 1. Identify what needs scoping

List every dimension of ambiguity in your skill. For a
code review skill:

| Dimension | Ambiguity | Options |
|---|---|---|
| Target | Which files? | Staged changes, a path, whole repo |
| Depth | Quick or thorough? | Quick scan, standard, deep review |
| Focus | What matters most? | Security, quality, performance |

Most skills have 1-2 dimensions. Three is the ceiling.

### 2. Design the questions

Write each question in natural language. The user should
feel like a colleague is asking, not like a form is
demanding input.

**Good:**

```
Which area should I review?
- Staged changes only
- A specific path
- The whole src/ directory
```

**Bad:**

```
Select target directory:
1. staged
2. path
3. src/
```

Rules for question design:

- **2-4 options.** `AskUserQuestion` enforces this limit.
  If you have more than 4 choices, group them into
  categories and ask in two rounds.
- **Always include "Other."** Let the user type a custom
  answer when none of the options fit.
- **One question at a time.** Never batch two scoping
  dimensions into a single question. Ask target first,
  then depth.
- **Front-load the most common choice.** Put the option
  most users will pick first in the list.

### 3. Implement the fast-path bypass

Before asking questions, check whether the user already
provided enough context. If they did, skip straight to
execution.

```python
# In your skill's entry point:
if user_provided_path and user_provided_mode:
    # Fast-path -- no questions needed
    return run_review(path=user_provided_path,
                      mode=user_provided_mode)

# Socratic path -- ask what's missing
if not user_provided_path:
    path = ask_target_question()

if not user_provided_mode:
    mode = ask_depth_question()

return run_review(path=path, mode=mode)
```

The fast-path check inspects the user's raw input for:

- A file path or glob pattern
- Keywords that imply mode (e.g., "quick", "deep",
  "security-focused")
- Explicit flags or arguments

### 4. Wire the flow into your skill template

In the skill's SKILL.md, describe the discovery flow so
the LLM follows it consistently.

```markdown
## Flow

1. If the user provided a path and focus area, skip to
   step 4.

2. Ask: "Which area should I review?"
   - Staged changes only
   - A specific path (let them type it)
   - The whole src/ directory

3. Ask: "How thorough should the review be?"
   - Quick scan (style + obvious issues)
   - Standard review (security + quality)
   - Deep review (multi-pass, everything)

4. Run the review with the scoped parameters.

5. Present results grouped by severity.
```

### 5. Test the three paths

Verify your skill handles all entry modes:

| Entry | Expected behavior |
|---|---|
| `/code-review` (no args) | Asks target question, then depth |
| `/code-review src/server.py` (path only) | Asks depth, skips target |
| `/code-review src/server.py --deep` (full) | Fast-path, no questions |

Also test edge cases:

- User provides an invalid path -- ask again or error
  clearly
- User picks "Other" -- accept freeform input gracefully
- User answers with extra context ("review the auth
  module for injection risks") -- extract both target and
  focus from the sentence

## Verification

After implementing:

- [ ] Skill asks 0 questions when full context is inline
- [ ] Skill asks 1-2 questions when context is partial
- [ ] Skill asks 2-3 questions when no context is given
- [ ] Each question has 2-4 options
- [ ] Every question includes an "Other" or freeform
      option
- [ ] Questions use natural language, not form prompts

## Example: code review skill

```
User: /code-review

Skill: Which area should I review?
  1. Staged changes
  2. A specific file or directory
  3. Everything under src/
  4. Other

User: 2
Skill: What path?
User: src/attune/mcp/server.py

Skill: How thorough should the review be?
  1. Quick scan (5 min)
  2. Standard review
  3. Deep multi-pass review

User: 1

Skill: [runs quick code review on server.py]
```

## Want to learn more?

- "What is Socratic discovery and why does it matter?" --
  see the **concept** template for principles and
  trade-offs
- "Show me how every Attune skill scopes its questions" --
  see the **reference** template for the full catalog
- "Just the quick version" -- see the **quickstart** for a
  5-step minimal guide

## Related Topics

- **Concept**: Socratic discovery patterns -- what it is,
  why scoping matters, and the fast-path exception
- **Reference**: Socratic discovery patterns -- all
  scoping patterns across Attune's 14 skills
- **Quickstart**: Socratic discovery patterns -- 5-step
  guide to add scoping questions to a skill
