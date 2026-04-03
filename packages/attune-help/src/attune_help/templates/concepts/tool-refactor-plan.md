---
type: concept
name: tool-refactor-plan
tags: [refactoring, complexity, code-smells]
source: plugin/skills/refactor-plan/SKILL.md
---

# Refactor Plan

A refactor plan scans your code for structural problems
and builds a prioritized roadmap to fix them. It catches
the issues that accumulate quietly — a class that grew
into a god object, copy-pasted blocks that drifted apart,
a function with 12 levels of nesting that nobody wants to
touch.

## What it analyzes

| Category | What it finds |
|----------|---------------|
| **Code smells** | Long methods, god classes, feature envy, data clumps |
| **Duplication** | Copy-pasted blocks, near-duplicates, DRY violations |
| **Complexity** | High cyclomatic complexity, deep nesting, long chains |
| **Coupling** | Circular imports, tight dependencies, shotgun surgery |
| **Naming** | Abbreviations, generic names, inconsistent conventions |
| **Dead code** | Unreachable branches, unused params, vestigial modules |

## When you'd use it

Run a refactor plan when a module feels hard to change or
test, before adding features to a tangled area, after a
deep-review flags complexity hotspots, or when you need
data to justify refactoring time to stakeholders.
Refactoring without a plan leads to yak-shaving — you
start fixing one thing and end up touching 20 files. The
roadmap tells you which changes deliver the most
improvement per hour invested.

## How it prioritizes

| Factor | What it means |
|--------|---------------|
| **Severity** | How much the issue hurts readability, testability, or safety |
| **Effort** | Lines of code affected, number of files touched |
| **Impact** | How much better the code gets after the fix |
| **Risk** | Chance of introducing regressions during the change |

Items that are high-severity, low-effort, and high-impact
float to the top. Risky changes get flagged so you can
plan extra testing.

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is code quality?"** for a broader code review
- Say **"tell me about security audit"** to scan for
  vulnerabilities instead
