---
type: concept
name: workflow-chain-prediction
tags: [help-system, workflow]
source: src/attune/workflows/suggestions.py
---

# Concept: Workflow chain prediction

## What

After a workflow completes, the system suggests relevant follow-up workflows based on transition patterns. For example: code-review -> security-audit -> test-gen.

## Why

Reduces decision fatigue. Users don't need to remember which workflows complement each other — the system surfaces the right next step.

## How

suggestions.py maintains a _TRANSITION_REGISTRY mapping each workflow to its likely follow-ups. get_workflow_help() in the engine maps these to template IDs via workflow_map in cross_links.json.

## Related Topics

_No related topics yet._
