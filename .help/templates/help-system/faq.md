---
type: faq
name: help-system-faq
feature: help-system
depth: faq
generated_at: 2026-07-14T15:58:52.811230+00:00
source_hash: ca01c2128b2f7c655e8b49be4eed5c98e84af405f64d43f1ed48adce237ea1ab
status: generated
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
