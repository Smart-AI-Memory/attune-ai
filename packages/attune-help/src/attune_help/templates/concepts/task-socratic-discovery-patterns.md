---
type: concept
name: task-socratic-discovery-patterns
tags: [socratic, discovery, ux, patterns]
source: developer-guidance
---

# Concept: Socratic discovery patterns

## What

Socratic discovery is Attune's core UX principle: ask
questions before executing. Instead of dumping every
possible result, a Socratic skill narrows scope through
short, focused questions -- then runs only what the user
actually needs.

The pattern has three phases:

1. **Discover** -- understand the user's goal
2. **Scope** -- narrow to the right files, depth, or mode
3. **Execute** -- run the focused action and return results

## Why

| Concern | Dump everything | Socratic approach |
|---|---|---|
| Relevance | User sifts through noise | Results match the request |
| Token cost | Full codebase scanned | Only target path scanned |
| Confidence | User unsure if scope was right | User confirmed scope before execution |
| Control | System decides what matters | User decides what matters |
| Speed | Slow on large repos | Fast on focused targets |
| Trust | "What did it just do?" | "I told it what to do" |

Scoping matters because most developer tasks have hidden
ambiguity. "Run a code review" could mean the whole repo,
one file, or just staged changes. Asking first eliminates
wasted work and makes the user feel in control.

## The fast-path exception

Not every invocation needs questions. When the user
provides enough context inline, skip straight to
execution.

```
# Full context inline -- fast-path, no questions
/security src/attune/mcp/server.py

# Ambiguous -- Socratic discovery needed
/security
```

The rule is: if the skill can infer scope, depth, and
mode from the user's input alone, execute immediately.
If any of those are ambiguous, ask.

## How it works in practice

A skill receives the user's input. It checks whether the
input already contains a target path or explicit mode. If
yes, it skips to execution. If not, it uses
`AskUserQuestion` to present 2-4 options.

The question should be phrased as a natural decision the
user would make anyway -- not a system prompt. Good
questions sound like a colleague asking for clarification:

- "Which area should I focus on?"
- "How deep should the review go?"
- "What kind of tests are you looking for?"

Bad questions sound like a form:

- "Please select the target directory."
- "Choose verbosity level: 1, 2, or 3."
- "Enter the file path to analyze."

## The three scoping dimensions

Most skills need at most three pieces of information:

| Dimension | Question pattern | Example |
|---|---|---|
| **What** (target) | "Which files or area?" | `src/`, staged changes, whole repo |
| **How** (depth/mode) | "Quick scan or thorough?" | Quick pass vs multi-pass deep review |
| **Why** (focus) | "What are you looking for?" | Security issues, test gaps, style |

One question per dimension. Most skills need one or two.
Three is the maximum before the user feels interrogated.

## Want to learn more?

- "How do I add Socratic discovery to my own skill?" --
  see the **task** template for a step-by-step guide
- "Show me every scoping pattern across all 14 skills" --
  see the **reference** template for the full catalog
- "Just give me the quick version" -- see the
  **quickstart** for a 5-step guide
- Run `/attune` to experience Socratic discovery firsthand

## Related Topics

- **Task**: Socratic discovery patterns -- step-by-step
  guide for adding discovery to a skill
- **Reference**: Socratic discovery patterns -- full
  catalog of scoping questions across all skills
- **Quickstart**: Socratic discovery patterns -- 5-step
  guide to add scoping questions to a skill
