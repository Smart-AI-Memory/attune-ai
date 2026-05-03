---
name: tool-refactor-plan
source: plugin/skills/refactor-plan/SKILL.md
summary: This template guides developers through creating a prioritized refactoring
  roadmap by analyzing code smells, complexity, and coupling issues to identify the
  highest-impact improvements with effort estimates.
tags:
- refactoring
- complexity
- code-smells
type: concept
---

# Refactor Plan

## What

Performs code-level refactoring analysis and generates a prioritized roadmap. Detects code smells (long methods, god classes), duplication, cyclomatic complexity, tight coupling, and naming issues. Produces a ranked list of refactoring opportunities with effort estimates.

## Why

Refactoring without a plan leads to yak-shaving — you start fixing one thing and end up touching 20 files. A refactor plan identifies the highest-impact changes first so you get the most improvement per hour invested.

## When to Use

- When a module feels hard to change or test
- Before adding features to a tangled codebase
- After a review flags complexity hotspots
- To justify refactoring time to stakeholders with data

## What It Detects

| Smell | Indicator | Typical Fix |
|-------|-----------|-------------|
| Long method | >50 lines or high cyclomatic complexity | Extract method |
| God class | >10 distinct responsibilities | Split into focused classes |
| Duplication | >3 similar blocks across the codebase | Extract shared helper |
| Tight coupling | Circular imports or deep dependency chains | Introduce dependency injection |
| Poor naming | Abbreviations or overly generic identifiers | Rename to reflect intent |
| Dead code | Unreachable branches or unused parameters | Delete safely |

## Related Topics

- **Task**: Use the refactor-plan skill — step-by-step walkthrough
- **Reference**: Skill: refactor-plan — full reference
