---
feature: deep-review
depth: concept
generated_at: 2026-04-06T04:29:21.871328+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Deep Review

## How it works

Deep review conducts multi-pass analysis of your code to identify security vulnerabilities, quality issues, and test coverage gaps.

The main building blocks are:

- **`DeepReviewAgentSDKWorkflow`** — Orchestrates multiple specialized Claude Agent SDK subagents to perform comprehensive code analysis across security, quality, and testing dimensions.

## What connects to it

This feature relates to: review, security, quality, tests.

Other parts of the codebase interact with
deep review through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `DeepReviewAgentSDKWorkflow` | Orchestrates multi-pass code analysis using specialized subagents | `src/attune/workflows/deep_review.py` |
