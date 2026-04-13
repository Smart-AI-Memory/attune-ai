---
feature: deep-review
depth: concept
generated_at: 2026-04-13T16:56:05.015603+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Deep Review

## How it works

Multi-pass deep code review that analyzes security vulnerabilities, code quality issues, and test coverage gaps using specialized AI agents.

The main building blocks are:

- **`DeepReviewAgentSDKWorkflow`** — Orchestrates multiple specialized Claude AI subagents that each focus on different aspects of code review (security, quality, testing).

## What connects to it

This feature relates to: review, security, quality, tests.

Other parts of the codebase interact with
deep review through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `DeepReviewAgentSDKWorkflow` | Coordinates specialized AI subagents for comprehensive code analysis across security, quality, and test dimensions | `src/attune/workflows/deep_review.py` |
