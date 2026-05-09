---
type: concept
name: sync-paradigm
tags: [architecture, documentation]
source: scripts/generate_all.py
---

# Concept: The sync paradigm

## What

A six-step pattern for generating documentation from code: Discover, Parse, Transform, Validate, Output, Verify. Every generator in the doc stack follows this pattern.

## Why

Ensures consistency, idempotency, and verifiability. The --check mode can validate that generated content matches its source without regenerating.

## How

1. Discover — find source files (SKILL.md, tool_schemas.py). 2. Parse — extract structured data from source. 3. Transform — convert to template dataclass. 4. Validate — check schema compliance. 5. Output — render via Jinja2 to generated/ directory. 6. Verify — --check mode compares output to existing files.

## Example

`python scripts/generate_all.py --check` verifies all 498 templates in sync.

## Related Topics

_No related topics yet._
