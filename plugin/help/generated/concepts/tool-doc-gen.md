---
name: tool-doc-gen
source: plugin/skills/doc-gen/SKILL.md
summary: This template explains how to automatically generate accurate, up-to-date
  documentation directly from source code, including docstrings, README sections,
  API references, and module overviews.
tags:
- documentation
- docstrings
type: concept
---

# Doc Generation

## What

Generates documentation directly from source code. Produces Google-style docstrings, README sections, API reference pages, and module overviews. Reads actual function signatures, type hints, and class hierarchies to build accurate docs rather than inferring them from descriptions.

## Why

Manually writing docstrings for every public function is tedious, and they tend to drift from the code within weeks. Doc generation reads the source of truth and produces consistent, up-to-date documentation that accurately reflects the actual API.

## When to Use

- After creating new public APIs or classes
- When onboarding contributors who need API reference material
- Before a release to refresh the README and changelog
- To generate module-level overviews for complex packages

## What It Produces

| Output | Description |
|--------|-------------|
| Docstrings | Google-style with `Args`, `Returns`, and `Raises` sections |
| README sections | Feature lists and usage examples |
| API reference | Function signatures with full type information |
| Module overview | Package-level architecture summary |

## Related Topics

- **Task:** Use the doc-gen skill — step-by-step guide
- **Reference:** Skill: doc-gen — full reference
