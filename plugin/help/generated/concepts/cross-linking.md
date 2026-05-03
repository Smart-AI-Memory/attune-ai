---
name: cross-linking
source: scripts/build_cross_links.py
summary: This developer help template covers how to automatically establish and use
  cross-links between related templates across a documentation system to help users
  navigate from any entry point to relevant content.
tags:
- help-system
- architecture
type: concept
---

# Template Cross-Linking

## Overview

Template cross-linking establishes deterministic relationships between 498 templates across 11 template types. These relationships connect related content automatically — for example, Error templates link to Warning templates, Skill templates link to Tool templates, and FAQ templates link to Error templates.

## Why Cross-Linking Matters

Users rarely navigate documentation linearly. They arrive at any entry point — an error message, a skill description, a FAQ — and need a path to relevant content from there. Cross-linking ensures the help system can surface related templates regardless of where a user starts, reducing dead ends and repeated searches.

## How It Works

The `build_cross_links.py` script derives relationships from source data using three strategies:

| Strategy | Template Types | Method |
|---|---|---|
| Slug matching | Error ↔ Warning | Matches shared slugs between template types |
| Tool name extraction | Skill → Tool | Extracts tool names referenced in skill content |
| Token overlap | Error → Tip | Compares keyword tokens across template bodies |

Results are stored in `cross_links.json`, which also includes a `tag_index` to support tag-based search queries.

## Cross-Link Type Reference

| Source Type | Target Type | Relationship |
|---|---|---|
| Error | Warning | Related condition |
| Skill | Tool | Required tooling |
| FAQ | Error | Common cause |
| Task | Reference | Supporting detail |

## Example

Running a tag-based query returns matched templates across all linked types:

```bash
attune help-docs --tag security
```

```
37 templates matched across 6 types: Error, Warning, Skill, Tool, FAQ, Task
```

## Related Topics

_No related topics yet._
