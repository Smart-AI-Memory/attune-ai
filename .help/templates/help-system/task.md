---
feature: help-system
depth: task
generated_at: 2026-04-04T02:25:50.376069+00:00
source_hash: cb73fad6d8cdda9b027176f7e3c046b7f6e2d022d3546db534c3ab1b0d741b0b
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
