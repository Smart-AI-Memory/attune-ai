---
type: concept
name: task-help-system-testing
tags: [testing, help-system, quality, validation]
source: developer-guidance
---

# Concept: Help system testing

## What

Help system testing verifies that templates load
correctly, progressive depth advances as expected,
precursor warnings fire for the right files, cross-links
resolve to real templates, and each renderer produces
valid output. It is the quality gate between "templates
exist on disk" and "users get the right answer."

## Why

A help system with broken templates is worse than no help
system. Silent failures -- a missing frontmatter field, a
dangling cross-link, a renderer that chokes on a table --
erode trust. Users ask for help, get nothing (or garbage),
and stop asking. Testing catches these before they ship.

## What to test

| Test type | What it verifies | Example | When to run |
|---|---|---|---|
| Template loading | Every `.md` file parses without error; frontmatter has required fields | Load all 600+ templates, assert no exceptions | CI, pre-commit |
| Progressive depth | "Tell me more" advances concept -> task -> reference, then resets on topic change | Call `lookup("security-audit")` three times, check depth metadata | Unit tests |
| Precursor warnings | File extension and name maps produce relevant warnings | Pass `"models.py"` to `precursor_warnings()`, expect database-related templates | Unit tests |
| Cross-link resolution | Every template ID referenced in `cross_links.json` points to a real file | Walk the links index, assert `_find_template_file()` succeeds for each | CI |
| Renderer output | Each audience adapter (plain, CLI, Claude Code, marketplace) produces non-empty, well-formed output | Render one template per type, check for title and no stack traces | Unit tests |
| Performance | Template directory scan and cross-link cache load stay under budget | Time `HelpEngine()` construction and first lookup | Benchmark suite |

## The testing pyramid for help

Most help system bugs are caught at the bottom of the
pyramid -- fast, deterministic template validation. Only
a few require end-to-end rendering tests.

- **Base (many tests):** Frontmatter schema validation,
  required section checks, tag consistency
- **Middle (moderate):** Progressive depth cycles,
  precursor tag mapping, cross-link integrity
- **Top (few tests):** Full render pipeline per renderer,
  performance budgets

## Key insight

The help engine is stateful (progressive depth tracks
session state) and multi-layered (templates -> population
-> adaptation -> rendering). Testing must cover both the
stateless parts (template parsing, cross-link resolution)
and the stateful parts (depth advancement, topic reset,
TTL).

## Want to learn more?

- Say **"how do I test the help system?"** for the
  step-by-step guide with Python code
- Say **"show me the help system test reference"** for
  complete test patterns, CI integration, and performance
  budgets
- Say **"I need to test my help system"** for the
  5-step quickstart with runnable code

## Related Topics

- **Task**: Help system testing -- step-by-step guide to
  writing tests using HelpEngine directly
- **Reference**: Help system testing -- complete test
  patterns, CI integration, and performance budgets
- **Quickstart**: Help system testing -- 5-step guide
  with runnable Python code
