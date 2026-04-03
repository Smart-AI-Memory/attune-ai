---
type: quickstart
name: task-socratic-discovery-patterns
tags: [socratic, discovery, ux, patterns]
source: developer-guidance
---

# Quickstart: Add scoping questions to a skill

Five steps to go from "run everything" to focused,
user-driven execution.

## 1. List your scoping dimensions

What is ambiguous when the user invokes your skill
without arguments? Most skills have 1-2 dimensions:

- **What** -- which files or area to target
- **How** -- quick scan vs deep analysis

## 2. Write the questions

Use natural language. Sound like a colleague, not a form.

```
Which area should I focus on?
- Staged changes
- A specific path
- Everything under src/
- Other
```

Keep it to 2-4 options. Always include "Other" as the
last choice.

## 3. Add a fast-path check

Before asking, check if the user already provided
context. If they gave a path and mode, skip questions
entirely.

```
# Full context -- skip questions
/my-skill src/server.py --quick

# No context -- ask
/my-skill
```

## 4. Wire it into your SKILL.md

Describe the flow so the LLM follows it consistently:

```markdown
1. If user provided path + mode, skip to step 3.
2. Ask scoping question(s) via AskUserQuestion.
3. Execute with the scoped parameters.
4. Present results.
```

## 5. Test all three entry modes

| Input | Expected |
|---|---|
| No arguments | Asks 1-2 questions, then executes |
| Path only | Asks mode, skips target question |
| Path + mode | No questions, executes immediately |

## Verify

Run your skill three ways and confirm:

- Zero questions when full context is given
- Natural-sounding questions when context is missing
- "Other" option works for freeform answers

## Want to learn more?

- "Walk me through the full process with an example" --
  see the **task** template for a complete guide using a
  code review skill
- "Show me how every Attune skill handles scoping" -- see
  the **reference** template for the full catalog
- "Why does this pattern matter?" -- see the **concept**
  template for design principles

## Related Topics

- **Concept**: Socratic discovery patterns -- what it is,
  why scoping matters, and the fast-path exception
- **Task**: Socratic discovery patterns -- step-by-step
  implementation with a code review skill example
- **Reference**: Socratic discovery patterns -- all
  scoping patterns across Attune's 14 skills
