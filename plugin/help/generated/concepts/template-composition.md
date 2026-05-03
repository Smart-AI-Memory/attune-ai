---
name: template-composition
source: src/attune/help/engine.py
summary: This developer help template covers how template composition merges related
  content inline during rendering to provide users with complete context in a single
  view, eliminating the need to navigate between pages.
tags:
- help-system
type: concept
---

# Concept: Template Composition

Template composition allows related content to be merged inline at render time, giving users complete context in a single view.

## What Is Template Composition?

When a template is rendered, composition embeds content from related templates directly into the output. For example:

- An **Error** template embeds its linked **Tip** template, so prevention guidance appears alongside the error description.
- A **Skill** reference template embeds the **Tool** parameter table it depends on, so users see the full parameter details without leaving the page.

## Why Use Template Composition?

Navigating between related pages interrupts the user's workflow. A composed view surfaces all relevant context in one read — the user understands the issue *and* learns how to prevent recurrence without following additional links.

## How Template Composition Works

Composition is driven by two components:

- **`cross_links.json`** — stores embed rules derived from `prevented_by` and `references_tools` relationships defined across templates.
- **`populate(compose=True)`** — when called with `compose=True`, the render function reads the embed rules in `cross_links.json`, fetches the linked templates, and appends compact versions of their content to the current template's output.

**Embed depth is limited to 1.** Linked templates are embedded once; their own links are not followed further. This prevents circular references and keeps output predictable.

## Related Topics

*No related topics yet.*
