---
type: comparison
feature: spec-engine
depth: comparison
generated_at: 2026-04-14T15:26:41.222572+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Spec engine vs manual task execution

## Overview

The spec engine automates XML-defined task pipelines with quality gates and approval workflows. You can either run tasks manually or let the orchestrator handle execution, state persistence, and progress tracking.

## Feature comparison

| Feature | Spec engine | Manual execution |
|---------|-------------|------------------|
| **Task presentation** | Human-readable markdown tables via `present_tasks()` | Custom formatting required |
| **Progress tracking** | Built-in progress bars and state persistence | Manual progress management |
| **Quality gates** | Automated gate execution with pass/fail scoring | Manual quality checks |
| **Approval workflow** | Per-task approval loop with `execute_with_approval()` | Custom approval logic |
| **State recovery** | Resume interrupted pipelines with `find_resumable_plans()` | No built-in resumption |
| **Error handling** | Structured error capture in `TaskResult` | Custom error management |
| **Cost tracking** | Per-task and total cost aggregation | Manual cost accounting |
| **Test integration** | Optional test execution per task | Separate test runner needed |

## Performance characteristics

The spec engine adds ~10-20ms overhead per task for state management and presentation formatting. For pipelines with quality gates, this overhead is negligible compared to gate execution time. The orchestrator processes tasks sequentially, not in parallel.

## Use spec engine when

- You have XML specs defining multi-step tasks
- You need quality gates with automatic scoring
- You want approval workflows for sensitive operations
- You require state persistence for long-running pipelines
- You need detailed cost and execution tracking
- You want structured error reporting across tasks

## Use manual execution when

- You're prototyping single tasks without formal specs
- You need parallel task execution (orchestrator runs sequentially)
- You're building one-off scripts that don't justify spec overhead
- You need custom task presentation beyond markdown tables
- You're working outside the XML spec format

## Recommendation

Use the spec engine for production pipelines where you need reliability, auditability, and human oversight. The `PipelineOrchestrator` provides the most complete feature set, while individual functions like `present_tasks()` work well for custom workflows that still want structured presentation.

For exploratory work or simple automation, manual execution with selective use of presentation functions strikes a better balance between simplicity and structure.

## Source files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

**Tags:** `spec`, `planning`
