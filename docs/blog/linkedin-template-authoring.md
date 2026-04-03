# 11 Template Types That Turn Code Into a Help System

*Part 3 of a series on building living documentation
with Claude Code*

In Part 2, I showed that your code already contains the
documentation — docstrings, type hints, frontmatter,
class attributes, and CLI help strings. The question is:
what do you turn them into?

Attune AI uses 11 template types, each designed for a
different moment in a developer's workflow. This article
walks through all 11, explains when each one fires, and
shows what the generated output looks like.

## The Template Anatomy

Every template is a markdown file with YAML frontmatter.
The frontmatter is the structured metadata a generator
writes and an engine reads. The body is what the user
sees.

--- CODE START ---
---
type: concept
name: audience-adaptation
tags: [help-system, architecture]
source: src/attune/help/transformers.py
---

# Audience Adaptation

## What

Audience adaptation renders the same template
differently for Claude Code users, CLI users,
and marketplace readers...
--- CODE END ---

Four frontmatter fields are common to every template:

- **type** — which of the 11 categories this belongs to
- **name** — a URL-safe slug used for lookup and linking
- **tags** — searchable keywords for discovery
- **source** — the code file this was generated from

The source field is what keeps things honest. When that
file changes, the maintenance pipeline knows this
template is stale.

## The 11 Types

### Errors (149 templates, prefix: err-)

**When it fires:** The user hits a known error or the
help engine detects a precursor pattern in the file
being edited.

**What it contains:** Signature (the error message),
root cause, resolution steps, confidence level.

**Generated from:** Lessons Learned entries in
CLAUDE.md, exception handlers in source code.

**Example:** "Adding logger before eager imports
triggers E402 in __init__.py" — includes the exact
fix and why it happens.

### Warnings (82 templates, prefix: war-)

**When it fires:** Precursor detection identifies a
pattern that frequently leads to problems.

**What it contains:** What to watch for, why it
matters, how to prevent it.

**Generated from:** Lessons Learned entries, linter
configurations, known anti-patterns.

### Tips (95 templates, prefix: tip-)

**When it fires:** Contextually relevant advice
surfaces during related help lookups.

**What it contains:** Short, actionable guidance.
Best practices tied to specific tools or patterns.

**Generated from:** Docstrings, code comments marked
as tips, cross-linked from related errors.

### References (84 templates, prefix: ref-)

**When it fires:** Third ask in progressive depth
("tell me more" twice), or direct lookup by name.

**What it contains:** Full detail — configuration
options, edge cases, related tools, code examples.

**Generated from:** Docstrings, class attributes,
CLI help strings, YAML frontmatter.

Some references carry a `subtype` field:

- **procedural** — step-by-step instructions
- **tabular** — comparison tables, option matrices

### Tasks (51 templates, prefix: tas-)

**When it fires:** Second ask in progressive depth
("tell me more" once).

**What it contains:** How-to guide with concrete
steps, options, and examples.

**Generated from:** CLI command definitions, workflow
execute() methods, skill instructions.

### FAQs (85 templates, prefix: faq-)

**When it fires:** Tag-based search or cross-link
from a related template.

**What it contains:** Question and answer format.
Direct, concise.

**Generated from:** Common patterns in Lessons
Learned, recurring user questions, error resolutions
rephrased as Q&A.

### Notes (17 templates, prefix: not-)

**When it fires:** Supplementary context linked from
other templates.

**What it contains:** Background information,
design decisions, architectural context.

**Generated from:** Architecture docs, design
decision records, code comments explaining "why."

### Quickstarts (32 templates, prefix: qui-)

**When it fires:** First interaction with a new
feature or tool.

**What it contains:** Minimal steps to get something
working. Install, configure, run.

**Generated from:** README sections, CLI help output,
skill frontmatter.

### Concepts (50 templates, prefix: con-)

**When it fires:** First ask in progressive depth
("what is security audit?").

**What it contains:** What it is, when to use it,
how it fits into the bigger picture.

**Generated from:** Class descriptions, module
docstrings, skill descriptions.

### Troubleshooting (41 templates, prefix: tro-)

**When it fires:** Error cross-links, or direct
search for problem-solving help.

**What it contains:** Symptom, diagnosis steps,
resolution. More structured than an error template —
covers multiple possible causes.

**Generated from:** Lessons Learned clusters,
related error groups, debugging patterns.

### Comparisons (71 templates, prefix: com-)

**When it fires:** When users ask "what's the
difference between X and Y?"

**What it contains:** Side-by-side comparison of
related tools, approaches, or configurations.

**Generated from:** Pairs of related class
attributes, overlapping CLI commands, skill
descriptions with similar tags.

## How They Connect

Templates don't exist in isolation. A cross-links
index tracks relationships between all 557 templates:

- An **error** links to the **warning** that could
  have prevented it
- A **concept** links to the **task** that teaches
  you to use it
- A **reference** links to related **FAQs** and
  **troubleshooting** entries
- A **quickstart** links to the **concept** for
  deeper understanding

This is what powers progressive depth. When you say
"tell me more," the engine doesn't just show a longer
version of the same content — it follows the
cross-link to a different template type that serves a
different purpose.

--- CODE START ---
concept  (what is it?)
   |
   v  cross-link
task     (how do I use it?)
   |
   v  cross-link
reference (show me everything)
--- CODE END ---

## The Generation Pipeline

Templates are generated by type-specific scripts that
parse the five source types from Part 2:

1. **Discover** — find source files (CLAUDE.md,
   docstrings, SKILL.md, CLI definitions)
2. **Parse** — extract structured content from each
   source type
3. **Transform** — populate templates, slugify names,
   classify tags
4. **Output** — write markdown files to the generated
   directory
5. **Cross-link** — build the relationship index
6. **Validate** — verify all templates are in sync
   with sources

The entire pipeline runs via a single script. When
sources change, the maintenance workflow (covered in
Part 5) re-runs the affected generators.

## The Directory

All 557 templates live in a flat structure organized
by type:

--- CODE START ---
plugin/help/generated/
  errors/           149 templates
  warnings/          82 templates
  tips/              95 templates
  references/        84 templates
  faqs/              85 templates
  comparisons/       71 templates
  tasks/             51 templates
  concepts/          50 templates
  troubleshooting/   41 templates
  quickstarts/       32 templates
  notes/             17 templates
  cross_links.json
  source_manifest.json
--- CODE END ---

`source_manifest.json` tracks which source file
produced each template and its last-known hash. When
a source file's hash changes, the template is marked
stale.

## Try It

Install the plugin and experience the template types
directly:

--- CODE START ---
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
--- CODE END ---

- "what is security audit?" — concept template
- "tell me more" — task template
- "tell me more" — reference template
- "what's the difference between code review and
  deep review?" — comparison template

The entire help system runs on your Claude subscription
— no API key required.

This is part 3 of a series on building knowledge bases,
help systems, dynamic assistance, and context-aware
documents with Claude Code and MCP.

If you find it useful, a star on the repo helps others
discover the project:
github.com/Smart-AI-Memory/attune-ai

Next up: Dynamic assistance and context-aware documents.
