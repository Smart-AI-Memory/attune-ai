---
feature: code-quality
depth: concept
generated_at: 2026-04-13T16:53:57.046616+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Code Quality

## How it works

Review code for style issues, likely bugs, and structural problems using an SDK-native workflow with specialized analysis agents.

The main building blocks are:

- **`CodeReviewWorkflow`** — SDK-native code review with four specialized subagents for comprehensive code analysis.

## What connects to it

This feature relates to: review, quality, bugs.

Other parts of the codebase interact with
code quality through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `CodeReviewWorkflow` | SDK-native code review with four specialized subagents for comprehensive code analysis. | `src/attune/workflows/code_review.py` |
