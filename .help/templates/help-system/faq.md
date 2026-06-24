---
type: faq
name: help-system-faq
feature: help-system
depth: faq
status: manual
---

# Help System FAQ

## What does the help system do?

It scans your project to discover features, generates depth-layered help
templates for each one, and serves those templates at runtime — adapting
content to the audience channel and tracking session state so users
automatically receive more detail each time they ask the same question.

## When should I use it?

Use the help system when you need to generate, maintain, or serve
contextual help templates for project features. If you only need to look
up a single template by ID, start with `populate()` in `help.templates`.
If you need to keep templates in sync as source files change, start with
`run_maintenance()` in `help.maintenance`.

## What are the key entry points?

The right starting point depends on what you want to do:

| Goal | Function | Module |
|---|---|---|
| Discover features in a project | `scan_project()` | `help.bootstrap` |
| Turn discovered features into a manifest | `proposals_to_manifest()` | `help.bootstrap` |
| Serve a template to a user | `populate()` | `help.templates` |
| Serve with progressive depth | `populate_progressive()` | `help.progression` |
| Re-generate stale templates | `run_maintenance()` | `help.maintenance` |
| Find templates relevant to a file | `get_precursor_warnings()` | `help.feedback` |
| Find templates relevant to a workflow | `get_workflow_help()` | `help.feedback` |

The `attune.help.engine` facade re-exports all of these in one place, so
`from attune.help.engine import populate, run_maintenance, …` also works.

## How are template IDs formed?

A template ID is `<type-prefix>-<name>` — for example
`con-progressive-depth` addresses the *concept* named
`progressive-depth`. The prefixes are `con` (concept), `tas` (task),
`ref` (reference), `qui` (quickstart), `err` (error), `war` (warning),
`tip`, `not` (note), `faq`, `tro` (troubleshooting), `com` (comparison).
`populate()` returns `None` if the ID resolves to no file.

## How does progressive depth work?

Each time a user asks about the same topic, `populate_progressive()`
advances the depth level — from concept to task to reference — so they
get more detail without being overwhelmed on the first request. The
session state is stored per topic and resets when the topic changes.
Call `reset_session()` from `help.session` to clear state manually.

## How do I know if my templates are out of date?

Call `check_staleness()` from `help.staleness`, passing your manifest
and project root. It returns a `StalenessReport` whose `stale_features`
**property** (no parentheses) lists every feature whose source hash no
longer matches the stored hash. Then call `run_maintenance()` to
regenerate only the stale ones. Features marked `status: manual` in the
manifest are skipped.

## Is generating templates from the engine the right path?

No — `generate_feature_templates()` in `help.generator` is **deprecated**
(it writes only three depths and emits a `DeprecationWarning`); it
survives as an internal escape hatch for the MCP `help_update` tool. The
current generation path is the single-source authoring pipeline
(`attune-author generate <feature> --all-kinds`, then the projector).

## How do I record feedback on a template?

Call `record_template_feedback(template_id, rating)` from
`help.feedback`. It returns the updated confidence score as a float. You
can retrieve the current score at any time with
`get_template_confidence(template_id)`.

## How do I find templates by tag?

Use `search_by_tag(tag)` to get a list of template IDs for a given tag,
or `list_tags()` to see every tag and how many templates it covers. Both
functions accept `sort_by_usage=True` to rank results by recent usage.

## How do I debug a failing template?

1. Confirm the manifest loads: `load_manifest(".help")`.
2. Confirm the ID resolves: `populate("<id>")` is not `None`.
3. Call `check_staleness()` to rule out stale source hashes.
4. If cross-links are involved, call `invalidate_cross_links_cache()`
   from `help.templates` and retry — a stale cache is a common source of
   resolution failures.

For renderer-specific failures, pass the `PopulatedTemplate` to
`render_cli()`, `render_claude_code()`, or `render_marketplace()`
individually to isolate which renderer is at fault.

## Is any of the help engine async?

No — every help engine entry point is synchronous.

## Where are the source files?

- `src/attune/help/**`
