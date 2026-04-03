---
type: reference
name: task-socratic-discovery-patterns
tags: [socratic, discovery, ux, patterns]
source: developer-guidance
---

# Reference: Socratic discovery patterns

Complete catalog of scoping question patterns, design
principles, AskUserQuestion format, and anti-patterns.

## Scoping patterns across Attune's 14 skills

| Skill | Question 1 (target) | Question 2 (mode/focus) | Fast-path trigger |
|---|---|---|---|
| attune-hub | "What are you trying to do?" | Routes to the matched skill | Any recognized command keyword |
| security-audit | "Which path should I scan?" | "Quick or thorough?" | Path provided inline |
| code-quality | "Which files?" | "What focus -- style, bugs, or both?" | Path provided inline |
| smart-test | "Which area has test gaps?" | -- | Path or module name inline |
| doc-gen | "What should I document?" | "Docstrings, README, or API ref?" | Path + doc type inline |
| fix-test | "Which test is failing?" | -- | Test name or file inline |
| release-prep | "Which version bump?" | "Pre-release checks?" | Version string inline |
| spec | "What mode -- brainstorm, plan, review, or execute?" | Varies by mode | Mode keyword inline |
| planning | "What are you planning?" | "Feature, architecture, or TDD?" | Goal described inline |
| refactor-plan | "Which module to refactor?" | "What smells -- duplication, complexity, coupling?" | Path provided inline |
| bug-predict | "Which path to scan?" | -- | Path provided inline |
| workflow-orchestration | "Which workflow?" | -- | Workflow name inline |
| memory-and-context | "Store, retrieve, or search?" | -- | Operation keyword inline |
| learn | "What topic?" | -- | Topic described inline |

**Pattern:** Most skills need one scoping question
(target). About half need a second (mode or focus). None
need three in practice.

## AskUserQuestion format

`AskUserQuestion` presents a multiple-choice question to
the user. Constraints:

| Property | Rule |
|---|---|
| Options count | 2 minimum, 4 maximum |
| Question style | Natural language, not form labels |
| Option ordering | Most common choice first |
| Freeform escape | Always include "Other" as last option |
| Batching | One question per turn, never combine |

### Example call

```
AskUserQuestion:
  question: "Which area should I review?"
  options:
    - "Staged changes only"
    - "A specific file or directory"
    - "Everything under src/"
    - "Other"
```

The user replies with a number or freeform text. If they
pick "Other," accept their typed input as the answer.

## Design principles

### One question at a time

Never combine two dimensions ("Which files and how
deep?") into a single question. Separate questions let the
user focus on one decision at a time and make the
conversation feel natural.

### 2-4 options, always allow "Other"

The hard limit is 4 options. If you have 6 possibilities,
group them into categories and ask in two rounds. "Other"
ensures the user is never trapped by your option list.

### Front-load the common choice

Put the option most users will select as option 1. This
reduces friction for the majority case and makes the
skill feel like it understands the user's intent.

### Questions sound like a colleague, not a form

| Good | Bad |
|---|---|
| "Which area should I focus on?" | "Select target directory:" |
| "How deep should the review go?" | "Choose verbosity level:" |
| "What kind of tests do you need?" | "Enter test type (unit/integration/e2e):" |

### Infer what you can, ask what you cannot

If the user wrote "review the auth module for security
issues," you already know the target (auth module) and
focus (security). Do not ask again. Only ask about
dimensions that are genuinely ambiguous.

## When NOT to ask

Skip questions entirely when:

| Scenario | Why |
|---|---|
| User provided a path and mode inline | All scope is resolved |
| Skill has exactly one behavior | Nothing to scope (e.g., health check) |
| Context makes the answer obvious | User said "fix the failing test" and there is exactly one failing test |
| Re-running a previous command | Same scope as last time, no need to re-ask |

The fast-path rule: if you can determine target, mode,
and focus from the input alone, execute immediately.

## Anti-patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| Too many questions (4+) | User feels interrogated | Combine or infer; max 2-3 questions |
| Asking what you could infer | User typed a path, skill asks for the path again | Parse the input before asking |
| Form-style prompts | "Enter the file path:" feels robotic | Use natural language questions |
| No "Other" option | User trapped when none of the options fit | Always include freeform escape |
| Asking for the same thing twice | Skill re-asks target after user already answered | Track conversation state |
| Asking when scope is obvious | `/fix-test test_auth.py` should not ask "which test?" | Implement fast-path check |
| Vague options | "Option A" / "Option B" tells the user nothing | Use descriptive, self-explanatory labels |

## Scoping dimension reference

The three dimensions most skills need:

| Dimension | Question | Typical options |
|---|---|---|
| **What** (target) | "Which files or area?" | Staged changes, specific path, whole repo, module name |
| **How** (depth/mode) | "Quick pass or thorough?" | Quick scan, standard, deep multi-pass |
| **Why** (focus) | "What are you looking for?" | Security, quality, performance, test gaps |

Most skills scope on **What** only. Complex skills like
code review and security audit add **How**. Almost no
skill needs all three.

## Want to learn more?

- "What is Socratic discovery and why does it matter?" --
  see the **concept** template for the design philosophy
- "Walk me through adding it to a skill" -- see the
  **task** template for a step-by-step implementation
  guide
- "Just the quick version" -- see the **quickstart** for
  a 5-step minimal guide
- Run `/attune` to experience Socratic discovery
  firsthand

## Related Topics

- **Concept**: Socratic discovery patterns -- what it is,
  the comparison table, and the fast-path exception
- **Task**: Socratic discovery patterns -- step-by-step
  guide with a code review skill example
- **Quickstart**: Socratic discovery patterns -- 5-step
  guide to add scoping questions to a skill
