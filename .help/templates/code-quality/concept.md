---
feature: code-quality
depth: concept
generated_at: 2026-04-06T04:27:32.366031+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Code Quality

## How it works

Automated code review identifies style issues, potential bugs, and structural problems in your codebase.

The main building blocks are:

- **`CodeReviewWorkflow`** — Orchestrates four specialized subagents to perform comprehensive code analysis using the SDK-native workflow system.

## What connects to it

This feature relates to: review, quality, bugs.

Other parts of the codebase interact with
code quality through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `CodeReviewWorkflow` | Orchestrates four specialized subagents to perform comprehensive code analysis using the SDK-native workflow system. | `src/attune/workflows/code_review.py` |
