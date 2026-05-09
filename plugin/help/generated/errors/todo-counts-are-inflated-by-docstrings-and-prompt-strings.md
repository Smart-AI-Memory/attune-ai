---
type: error
name: todo-counts-are-inflated-by-docstrings-and-prompt-strings
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: TODO counts are inflated by docstrings and
  prompt strings describing TODO markers

## Signature

TODO counts are inflated by docstrings and
  prompt strings describing TODO markers

## Root Cause

a grep-based count of `TODO|FIXME` in attune-ai reported 54 items but triage showed only 1 real blocker. The inflation came from docstring text like "Generated Python test code as a string with TODO markers", prompt instructions like "Complete ALL TODOs with:", and example-output strings inside test generators. Classify by reading surrounding context (is the `TODO` in an executable code path, or is it the string content of a docstring / prompt / example output?), not by counting matches. Only code- path TODOs are real debt.

## Resolution

1. a grep-based count of `TODO|FIXME` in attune-ai reported 54 items but triage showed only 1 real blocker

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
