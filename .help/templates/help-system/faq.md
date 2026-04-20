---
type: faq
feature: help-system
depth: faq
generated_at: 2026-04-20T01:18:38.711695+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Help System FAQ

## What is the help system?

A template engine that provides progressive-depth help based on context, advancing from concept to task to reference as users ask for more detail.

## When should I use the help system?

Use the help system when you need context-aware documentation that adapts to user behavior. It's designed for CLI tools, development environments, and applications where users need different levels of detail depending on their experience and current task.

## How do I get started?

Start with `scan_project()` to discover features in your codebase, then use `proposals_to_manifest()` to create a features manifest. Once you have templates, use the `populate()` function to render help content for specific audiences.

## How does progressive depth work?

The system tracks session state and advances depth automatically. First lookup returns concept-level help (depth 0), second lookup provides task details (depth 1), and third lookup shows reference information (depth 2). Depth resets when you change topics.

## What's the difference between templates and populated templates?

Templates are markdown files with frontmatter that define the structure and content. Populated templates are the result of processing those templates with audience-specific context, ready for rendering to users.

## How do I test my help system?

Run template validation to ensure all markdown files parse correctly, test progressive depth advancement with repeated lookups, verify precursor warnings trigger for relevant files, and check that cross-links resolve to existing templates.

## Where are templates stored?

Templates live in the `templates/` directory within your help system package. Each template has a type (concept, task, reference, etc.) and belongs to a feature defined in `features.yaml`.

**Tags:** `help`, `templates`, `docs`
