---
feature: deep-review
depth: concept
generated_at: 2026-06-01T11:59:09.442052+00:00
source_hash: c88c39a4d669dd53e0c79a38f05bf3f121d25317b59202f71eed73be8dc817a0
status: generated
---

# Deep Review

## How it works

Multi-pass deep code review — security, quality, and test gap analysis.

The main building blocks are:

- **`DeepReviewAgentSDKWorkflow`** — Multi-pass deep code review using Claude Agent SDK subagents.

## What connects to it

This feature relates to: review, security, quality, tests, comprehensive-review.

Other parts of the codebase interact with
deep review through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `DeepReviewAgentSDKWorkflow` | Multi-pass deep code review using Claude Agent SDK subagents. | `src/attune/workflows/deep_review.py` |
