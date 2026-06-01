---
feature: bug-predict
depth: concept
generated_at: 2026-06-01T11:47:06.406248+00:00
source_hash: cc510a144b48d7a571de765708d61c6c9bd34809866c35bf40d3568682dc0f7c
status: generated
---

# Bug Predict

## How it works

Predict likely bug locations based on code patterns and complexity.

The main building blocks are:

- **`BugPredictionWorkflow`** — SDK-native bug prediction with three specialized subagents.

Under the hood, this feature spans 3 source
files covering:

- Bug Prediction Pattern Detection Helpers.
- Bug Prediction Report Formatting and CLI Entry Point.

## What connects to it

This feature relates to: bugs, prediction, scanning, race-condition.

Other parts of the codebase interact with
bug predict through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `BugPredictionWorkflow` | SDK-native bug prediction with three specialized subagents. | `src/attune/workflows/bug_predict.py` |
