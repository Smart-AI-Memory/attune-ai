---
type: concept
name: template-composition
tags: [help-system]
source: src/attune/help/engine.py
---

# Concept: Template composition

## What

Templates can inline related content at render time. An Error template embeds its prevention Tip; a Skill reference embeds its Tool parameter table.

## Why

Users get complete context without navigating between templates. A composed view answers the question and prevents recurrence in one read.

## How

cross_links.json stores embed rules derived from prevented_by and references_tools relationships. populate(compose=True) follows embed rules and appends compact versions of linked templates. Max depth: 1.

## Related Topics

_No related topics yet._
