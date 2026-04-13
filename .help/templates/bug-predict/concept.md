---
feature: bug-predict
depth: concept
generated_at: 2026-04-13T16:55:07.884620+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Bug Predict

## How it works

Predict likely bug locations based on code patterns and complexity.

The main building blocks are:

- **`BugPredictionWorkflow`** — SDK-native bug prediction with three specialized subagents that analyze code for potential issues.

Under the hood, this feature spans 3 source
files covering:

- Bug Prediction Pattern Detection Helpers.
- Bug Prediction Report Formatting and CLI Entry Point.

## What connects to it

This feature relates to: bugs, prediction, scanning.

Other parts of the codebase interact with
bug predict through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `BugPredictionWorkflow` | SDK-native bug prediction with three specialized subagents. | `src/attune/workflows/bug_predict.py` |
