---
type: concept
name: tool-doc-gen
tags: [documentation, docstrings]
source: plugin/skills/doc-gen/SKILL.md
---

# Doc Generation

## What

Generates documentation directly from source code. Produces
Google-style docstrings, README sections, API reference
pages, and module overviews. Reads the actual function
signatures, type hints, and class hierarchies to build
accurate docs rather than hallucinating from descriptions.

## Why

Manually writing docstrings for every public function is
tedious and they drift from the code within weeks. Doc-gen
reads the source of truth and produces consistent,
up-to-date documentation that matches the actual API.

## When to use

- After creating new public APIs or classes
- When onboarding contributors who need API docs
- Before a release to refresh the README and changelog
- To generate module-level overviews for complex packages

## What it produces

| Output | Description |
|--------|-------------|
| Docstrings | Google-style with Args, Returns, Raises |
| README sections | Feature lists, usage examples |
| API reference | Function signatures with type info |
| Module overview | Package-level architecture summary |

## Related Topics

- **Task**: Use the doc-gen skill -- step-by-step
- **Reference**: Skill: doc-gen -- full reference
