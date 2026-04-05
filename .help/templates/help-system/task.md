---
feature: help-system
depth: task
generated_at: 2026-04-04T13:00:34.144447+00:00
source_hash: b3961a69a2834514dc7e777ba16f67fd57a9770e63c41fd38219fcf1994682c6
status: generated
---

# Working with Help System

## Overview

Common tasks for modifying or extending help system.

## Key Files

- `src/attune/help/**`

- `packages/attune-help/src/attune_help/**`


## Common Modifications

Functions you may need to modify:

- `scan_project()` in `src/attune/help/bootstrap.py`

- `proposals_to_manifest()` in `src/attune/help/bootstrap.py`

- `record_template_feedback()` in `src/attune/help/feedback.py`

- `get_template_confidence()` in `src/attune/help/feedback.py`

- `get_usage_weights()` in `src/attune/help/feedback.py`

- `search_by_tag()` in `src/attune/help/feedback.py`

- `list_tags()` in `src/attune/help/feedback.py`

- `get_workflow_help()` in `src/attune/help/feedback.py`
