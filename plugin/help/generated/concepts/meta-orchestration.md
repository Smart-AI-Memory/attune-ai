---
type: concept
name: meta-orchestration
tags: [architecture, workflow]
source: src/attune/orchestration/
---

# Concept: Meta-orchestration patterns

## What

Six composition patterns for combining workflows into pipelines: Sequential, Parallel, Debate, Teaching, Refinement, and Adaptive.

## Why

Complex tasks require multiple analysis passes. A release prep combines security audit, test generation, and documentation review in a single orchestrated pipeline.

## How

The orchestration module composes BaseWorkflow instances using the selected pattern. Each pattern defines execution order, data flow between stages, and quality gates.

## Example

Secure Release uses Sequential: security_audit -> dependency_check -> release_prep.

## Related Topics

_No related topics yet._
