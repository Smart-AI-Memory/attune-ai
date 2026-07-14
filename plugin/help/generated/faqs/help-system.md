---
name: help-system
source: content/features/help-system.md
tags:
- help
- templates
- docs
type: faq
---

# Help System FAQ

## What does the help system do?

It discovers a project's features, generates depth-layered help
templates for each, and serves them at runtime — adapting to the
audience channel and advancing depth as a user asks again.

## What are the key entry points?

`scan_project()` (discover), `generate_feature_templates()`
(generate), `populate()` (serve), `run_maintenance()` (keep in sync),
and `get_precursor_warnings()` / `get_workflow_help()` (contextual).

## How do I know if my templates are out of date?

Call `check_staleness()` from `help.staleness`; its
`StalenessReport.stale_features` **property** lists every feature whose
source hash no longer matches. Then `run_maintenance()` to regenerate.

## Is anything async?

No — every help engine entry point is synchronous.

## How do I find templates by tag?

`search_by_tag(tag)` returns template IDs; `list_tags()`
returns tag → count. Both take `sort_by_usage=True` to rank by recent
usage.

## Where are the source files?

`src/attune/help/**`.
