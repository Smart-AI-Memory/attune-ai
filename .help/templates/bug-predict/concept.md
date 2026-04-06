---
feature: bug-predict
depth: concept
generated_at: 2026-04-06T04:28:33.570227+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Bug Predict

## How it works

Predict likely bug locations based on code patterns and complexity.

The main building blocks are:

- **`BugPredictionWorkflow`** — SDK-native bug prediction with three specialized subagents that analyze code patterns, complexity metrics, and historical bug data.

Under the hood, this feature spans 3 source
files covering:

- Bug prediction pattern detection helpers that identify code smells and complexity indicators.
- Bug prediction report formatting and CLI entry point for command-line usage.

## What connects to it

This feature relates to: bugs, prediction, scanning.

Other parts of the codebase interact with
bug predict through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `BugPredictionWorkflow` | SDK-native bug prediction with three specialized subagents that analyze code patterns and complexity. | `src/attune/workflows/bug_predict.py` |
