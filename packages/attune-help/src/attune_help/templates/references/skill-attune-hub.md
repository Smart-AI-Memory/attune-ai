---
type: reference
subtype: procedural
name: skill-attune-hub
category: skill
tags: [hub, skill, plugin, reference]
source: plugin/skills/attune-hub/SKILL.md
---

# Attune Hub Reference

Complete reference for the attune-hub skill -- every
routing keyword, all available skills, and the full
discovery flow.

## Invocation

```
/attune-hub <what you need help with>
```

Or natural language (no slash command needed):

```
help me with my code
what can attune do?
I need to check something before releasing
```

**Trigger words:** attune, help me, what can you do,
workflows, setup, configure, capabilities.

## Runs on your Claude subscription

The hub and all skills run on your existing Claude
subscription. No API key needed, no additional cost.
Install with `pip install attune-ai` and start talking.

## Discovery flow

When invoked without arguments, the hub asks a scoping
question:

```
What are you trying to accomplish?
  1. Run a workflow
     Security audit, code review, test gen, perf,
     release prep
  2. Manage memory
     Store, retrieve, search, or forget patterns
  3. Configure settings
     Check setup, update attune-ai, view telemetry
  4. Learn what attune-ai does
     Overview of capabilities and skills
```

Your answer determines the next step. The hub may ask
one more question to narrow scope, then routes to the
matching skill.

## Example interaction

```
You:    /attune-hub I want to clean up some messy code
Hub:    What kind of cleanup are you looking for?
          1. Refactor — restructure, reduce complexity
          2. Code review — find quality issues and smells
          3. Fix tests — repair broken test suite
          4. Something else
You:    refactor
Hub:    [routes to refactor-plan]
        Which file or directory should I analyze?
```

The hub interprets your intent and maps it to the closest
skill. If your description is specific enough, it skips
the clarifying question entirely:

```
You:    /attune-hub refactor src/api/ to reduce duplication
Hub:    [routes directly to refactor-plan with path=src/api/]
```

## All skill categories

### Code analysis

| Skill | What it does | Routing keywords |
|-------|-------------|-----------------|
| security-audit | Scan for vulnerabilities (eval, path traversal, secrets, injection) | security, vulnerability, audit, scan, CVE |
| code-quality | Code review for quality issues, style, and bugs | review, quality, code review, lint, code smell |
| bug-predict | Predict where bugs are likely based on code patterns | predict bugs, risky code, what might break |

### Testing

| Skill | What it does | Routing keywords |
|-------|-------------|-----------------|
| smart-test | Find test gaps and generate tests for uncovered code | generate tests, test gaps, coverage, untested |
| fix-test | Auto-diagnose and fix failing tests | fix test, broken test, debug test, test fails |

### Planning and design

| Skill | What it does | Routing keywords |
|-------|-------------|-----------------|
| planning | Feature planning, TDD scaffolding, architecture review | plan, feature, architecture, design, TDD |
| spec | Spec-driven development with brainstorm, plan, and execute | spec, brainstorm, plan and execute, design doc |

### Refactoring and documentation

| Skill | What it does | Routing keywords |
|-------|-------------|-----------------|
| refactor-plan | Detect code smells, duplication, complexity; generate roadmap | refactor, tech debt, simplify, restructure |
| doc-gen | Generate docstrings, README sections, API references | docs, documentation, README, API docs |

### Release and operations

| Skill | What it does | Routing keywords |
|-------|-------------|-----------------|
| release-prep | Pre-release health checks, changelog, version bumps | release, publish, ship, deploy, version |
| workflow-orchestration | Run multi-step analysis workflows end to end | workflow, run, execute, analyze |

### Memory

| Skill | What it does | Routing keywords |
|-------|-------------|-----------------|
| memory-and-context | Store, retrieve, search, and manage persistent memory | memory, store, retrieve, remember, forget |

## Complete routing table

Every natural language pattern and where it goes:

| What you say | Routed to |
|-------------|-----------|
| "find security issues" | security-audit |
| "scan for vulnerabilities" | security-audit |
| "check for hardcoded secrets" | security-audit |
| "review this code" | code-quality |
| "find code smells" | code-quality |
| "generate tests" | smart-test |
| "find untested code" | smart-test |
| "fix my broken tests" | fix-test |
| "debug this test failure" | fix-test |
| "plan a feature" | planning |
| "design the architecture" | planning |
| "brainstorm and build" | spec |
| "write a spec" | spec |
| "refactor this module" | refactor-plan |
| "reduce tech debt" | refactor-plan |
| "simplify this code" | refactor-plan |
| "write documentation" | doc-gen |
| "generate a README" | doc-gen |
| "predict where bugs will be" | bug-predict |
| "find risky code" | bug-predict |
| "prepare a release" | release-prep |
| "publish to PyPI" | release-prep |
| "remember this pattern" | memory-and-context |
| "what do you know about me?" | memory-and-context |
| "run the full analysis" | workflow-orchestration |

## Direct skill shortcuts

Skip the hub entirely when you know what you want:

| Shortcut | Effect |
|----------|--------|
| `/security-audit src/` | Run security scan on src/ |
| `/smart-test src/auth/` | Generate tests for auth module |
| `/code-quality src/api/` | Review api code quality |
| `/fix-test` | Diagnose and fix failing tests |
| `/refactor-plan src/legacy/` | Analyze refactoring targets |
| `/doc-gen src/api/` | Generate docs for api module |
| `/release-prep` | Run pre-release checks |
| `/bug-predict src/` | Predict bug-prone areas |
| `/planning` | Start feature planning |
| `/spec` | Start spec-driven development |

## Troubleshooting

### MCP server not running

If skills are not responding:

```bash
pip install attune-ai
attune doctor
```

### Hub doesn't route correctly

Be more specific in your request. Instead of "check my
code," say "scan for security vulnerabilities in src/" or
"review code quality in the auth module." The more context
you provide, the more accurately the hub routes.

## Want to learn more?

- Say **"what is attune hub?"** for the concept overview
- Say **"how do I use attune hub?"** for step-by-step
  instructions
- Say **"run a security audit"** to try a skill directly
- Say **"what can attune do?"** to explore all
  capabilities
