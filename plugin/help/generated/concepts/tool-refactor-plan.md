---
type: concept
name: tool-refactor-plan
tags: [refactoring, complexity, code-smells]
source: plugin/skills/refactor-plan/SKILL.md
---

# Refactor Plan

## What

Performs code-level refactoring analysis and generates a
prioritized roadmap. Detects code smells (long methods,
god classes), duplication, cyclomatic complexity, tight
coupling, and naming issues. Produces a ranked list of
refactoring opportunities with effort estimates.

## Why

Refactoring without a plan leads to yak-shaving -- you
start fixing one thing and end up touching 20 files. A
refactor plan identifies the highest-impact changes first
so you get the most improvement per hour invested.

## When to use

- When a module feels hard to change or test
- Before adding features to a tangled codebase
- After a deep-review flags complexity hotspots
- To justify refactoring time to stakeholders with data

## What it detects

| Smell | Indicator | Typical fix |
|-------|-----------|-------------|
| Long method | >50 lines, high complexity | Extract method |
| God class | >10 responsibilities | Split into focused classes |
| Duplication | >3 similar blocks | Extract shared helper |
| Tight coupling | Circular imports, deep chains | Dependency injection |
| Poor naming | Abbreviations, generic names | Rename to intent |
| Dead code | Unreachable branches, unused params | Delete safely |

## Related Topics

- **Task**: Use the refactor-plan skill -- step-by-step
- **Reference**: Skill: refactor-plan -- full reference
