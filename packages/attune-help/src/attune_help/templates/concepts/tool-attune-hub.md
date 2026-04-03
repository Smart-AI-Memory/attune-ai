---
type: concept
name: tool-attune-hub
tags: [hub, routing, discovery]
source: plugin/skills/attune-hub/SKILL.md
---

# Attune Hub

Your starting point. The hub is the Socratic entry point
for everything Attune can do -- you describe what you need
in plain English, it asks clarifying questions, and routes
you to the right skill. No menus to memorize, no command
syntax to look up.

## How it works

When you say something like "I need to check my code
before releasing," the hub doesn't just guess. It asks
what you mean:

```
You:    I need to check my code before releasing
Hub:    What are you trying to accomplish?
          1. Run a security audit
          2. Review code quality
          3. Generate tests for gaps
          4. Prepare the release
```

You pick an option (or clarify further), and the hub
hands off to the skill that fits. You never need to know
that security-audit, code-quality, smart-test, or
release-prep exist as separate skills -- the hub finds
them for you.

## What it routes to

| Category | Skills available | What to say |
|----------|-----------------|-------------|
| **Security** | security-audit | "find vulnerabilities", "scan for secrets" |
| **Quality** | code-quality | "review this code", "find code smells" |
| **Testing** | smart-test, fix-test | "generate tests", "fix broken tests" |
| **Planning** | planning, spec | "plan a feature", "brainstorm and build" |
| **Refactoring** | refactor-plan | "simplify this module", "reduce tech debt" |
| **Documentation** | doc-gen | "write docs", "generate a README" |
| **Bugs** | bug-predict | "predict where bugs will happen" |
| **Release** | release-prep | "prepare a release", "publish to PyPI" |
| **Memory** | memory-and-context | "remember this", "what do you know about me?" |
| **Workflows** | workflow-orchestration | "run an analysis workflow" |

## When to use the hub vs. a skill directly

Use the hub when you're unsure what you need, when you
want to explore what's available, or when your goal spans
multiple skills. Go directly to a skill when you already
know exactly which one you want -- for example,
`/security-audit src/` skips the discovery conversation
and runs immediately.

The hub is never slower than going direct -- it just adds
a question or two to make sure you end up in the right
place.

## Runs on your Claude subscription

The hub uses your existing Claude subscription. No API
key, no additional cost, no configuration. Install
attune-ai and start talking.

## Want to learn more?

- Say **"tell me more"** for step-by-step usage
  instructions
- Say **"what skills are available?"** for the complete
  skill catalog with routing keywords
- Say **"run a security audit"** to skip the hub and go
  directly to a skill
