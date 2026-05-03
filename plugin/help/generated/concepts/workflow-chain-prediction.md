---
name: workflow-chain-prediction
source: src/attune/workflows/suggestions.py
summary: This template documents a system feature that automatically suggests relevant
  follow-up workflows after each workflow completion by analyzing historical transition
  patterns, reducing user decision fatigue and keeping developers in flow.
tags:
- help-system
- workflow
type: concept
---

# Workflow Chain Prediction

After a workflow completes, the system analyzes historical transition patterns to suggest relevant follow-up workflows. For example, completing a `code-review` workflow might surface suggestions for `security-audit` and `test-gen` as logical next steps.

## Why This Matters

Complex development processes often involve multiple sequential workflows. Without guidance, users must remember which workflows complement each other and in what order — a cognitive burden that grows as the workflow library expands.

Workflow chain prediction reduces this decision fatigue by surfacing the right next step automatically, keeping you in flow rather than context-switching to figure out what comes next.

## How It Works

Two components work together to produce suggestions:

- **`suggestions.py`** maintains a `_TRANSITION_REGISTRY` — a mapping from each workflow to its likely follow-ups, based on observed transition patterns.
- **`get_workflow_help()`** in the engine resolves these follow-ups to displayable template IDs using the `workflow_map` defined in `cross_links.json`.

When a workflow completes, the engine queries the registry for that workflow's entry, resolves each follow-up to its template metadata, and returns the suggestions for display.

## Example Chain

```
code-review → security-audit → test-gen
```

Each arrow represents a common transition — a follow-up that users frequently run after the preceding workflow.

## Related Topics

No related topics have been linked yet. To add one, update the `cross_links.json` file with a reference to this concept.
