---
type: task
name: use-attune-hub
tags: [hub, skill, task]
source: plugin/skills/attune-hub/SKILL.md
---

# How to Use Attune Hub

## Quick start

Just describe what you need. No slash command required.

```
help me check my code for issues
```

Or invoke the hub directly:

```
/attune-hub
```

Either way, you'll be asked what you're trying to
accomplish, and the hub routes you to the right skill.

## The discovery conversation

The hub uses Socratic discovery -- it asks before it
acts. Here's a typical flow:

```
You:    /attune-hub
Hub:    What are you trying to accomplish?
          1. Run a workflow (security, review, tests...)
          2. Manage memory
          3. Configure settings
          4. Learn what attune-ai does
You:    1
Hub:    What kind of analysis do you need?
          1. Security audit
          2. Code quality review
          3. Generate tests
          4. Something else
You:    security audit
Hub:    [routes to security-audit skill]
        What path should I scan? (e.g., src/, a specific file)
```

Each question narrows the scope. You can also short-
circuit the conversation at any point by being specific:

```
You:    /attune-hub scan src/ for security issues
Hub:    [routes directly to security-audit with path=src/]
```

## Routing shortcuts

When you already know what you want, include it in your
message and the hub skips the questions:

| What you type | Where it goes |
|---------------|---------------|
| "find security vulnerabilities" | security-audit |
| "review code quality" | code-quality |
| "generate tests for src/" | smart-test |
| "fix my broken tests" | fix-test |
| "plan a new feature" | planning |
| "brainstorm and build a spec" | spec |
| "refactor this module" | refactor-plan |
| "write documentation" | doc-gen |
| "predict where bugs will be" | bug-predict |
| "prepare a release" | release-prep |
| "remember this pattern" | memory-and-context |
| "run the full workflow" | workflow-orchestration |

## Going direct (skip the hub entirely)

If you know the exact skill, call it directly:

```
/security-audit src/
/smart-test src/auth/
/code-quality src/api/handlers.py
```

Direct invocation skips all discovery questions and runs
the skill immediately. The hub is there for when you're
not sure which skill fits, or when you want to explore.

## What to do after routing

Once the hub routes you to a skill, that skill takes
over. It may ask its own scoping questions (which file?
what depth? what focus?). The hub's job is done -- it
found the right skill for your intent.

## Want to learn more?

- Say **"tell me more"** for the full reference with
  every routing keyword and skill category
- Say **"what is attune hub?"** for the concept overview
- Say **"what skills are available?"** to browse the
  complete catalog
