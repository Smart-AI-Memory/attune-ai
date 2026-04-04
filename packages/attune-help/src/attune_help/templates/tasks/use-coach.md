---
type: task
name: use-coach
tags: [skill, help-system, task]
source: plugin/skills/coach/SKILL.md
---

# How to Use Coach

## Quick start

Ask about any topic in plain language:

```
what is security audit?
```

Or use the skill directly:

```
/coach security-audit
```

You'll get a concept-level overview. No setup, no API
key -- runs on your Claude subscription.

## Trying progressive depth

Every topic supports three levels. Say "tell me more"
to advance:

| You say | What happens |
|---------|--------------|
| "what is code review?" | Level 0: concept overview |
| "tell me more" | Level 1: step-by-step task guide |
| "tell me more" | Level 2: full reference with all options |

You can also trigger progression with "go deeper",
"explain more", or "show me the reference."

## Switching topics

Ask about a different topic at any time to reset to
the concept level:

```
what is bug prediction?
```

The engine remembers your last topic. If you come back
to it later in the same session, it picks up where you
left off.

## Jumping straight to the task level

If you just finished running a workflow, the engine
can skip the concept and start at the step-by-step:

```
I just ran security audit, tell me about the results
```

## Available topics

Use the bare topic name -- the engine resolves it to
the right template:

| You say | Topic slug |
|---------|-----------|
| security audit | `security-audit` |
| code review / code quality | `code-quality` |
| bug prediction | `bug-predict` |
| test generation / smart test | `smart-test` |
| release / release prep | `release-prep` |
| refactor | `refactor-plan` |
| doc gen | `doc-gen` |
| fix test | `fix-test` |
| planning | `planning` |
| memory | `memory-and-context` |
| spec | `spec` |

## The 4-hour session window

Your depth level and last topic persist for 4 hours
of inactivity. After that, the session resets and you
start from the concept level again. This keeps the
experience fresh -- if you come back tomorrow, you
get the overview, not the deep reference you drilled
into yesterday.

To manually reset at any time:

```
start from the beginning on security audit
```

## What to do next

- **Explore a topic** -- pick anything from the table
  above and ask about it
- **Browse all templates** -- say "what topics can I
  coach me on?"
- **Go deeper on coach itself** -- say "tell me more"
  for the complete reference with template counts,
  cross-linking, and session state details

## Want to learn more?

- Say **"tell me more"** for the full reference --
  all 11 template types, cross-link rules, tag search
- Say **"what is coach?"** to go back to the overview
- Say **"what is progressive depth?"** to understand
  how the depth engine works
