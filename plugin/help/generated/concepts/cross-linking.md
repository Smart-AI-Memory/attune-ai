---
type: concept
name: cross-linking
tags: [help-system, architecture]
source: scripts/build_cross_links.py
---

# Concept: Template cross-linking

## What

Deterministic relationships between 498 templates across 11 types. Error links to Warning, Skill links to Tool, FAQ links to Error, Task links to Reference.

## Why

Users don't navigate documentation in a linear path. Cross-links let the help system surface related content regardless of where the user starts.

## How

build_cross_links.py derives relationships from source data: slug matching (Error<->Warning), tool name extraction (Skill->Tool), token overlap (Error->Tip). Results stored in cross_links.json with a tag_index for search.

## Example

`attune help-docs --tag security` returns 37 templates across all types.

## Related Topics

_No related topics yet._
