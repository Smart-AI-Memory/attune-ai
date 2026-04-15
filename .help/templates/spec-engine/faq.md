---
type: faq
feature: spec-engine
depth: faq
generated_at: 2026-04-14T15:26:02.812942+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Spec Engine FAQ

## What is the spec engine?

The spec engine executes XML specifications as a series of tasks, with quality gates and approval loops for each step. It manages execution state so you can resume interrupted runs.

## When should I use the spec engine?

Use the spec engine when you want to run specifications with human oversight. It's designed for cases where you need to review and approve each task before proceeding to the next one.

## How do I run a spec with approvals?

Call `execute_with_approval()` with your spec path. This function will pause after each task and wait for your approval before continuing.

## How do I see what tasks are in my spec?

Use `present_tasks()` to get a markdown table of all tasks, or `present_task_detail()` to see the full details of a single task.

## Can I resume a partially completed spec?

Yes. The spec engine saves execution state in your plan files. Use `find_resumable_plans()` to see which specs have incomplete runs, then call `load_state()` to restore where you left off.

## How do I run a spec without approvals?

Create a `PipelineOrchestrator` and call `run_all()`. This executes the entire spec automatically without stopping for approval.

## What happens if a task fails its quality gates?

The task result will show `quality_gate_passed: False` and include details in the `gate_details` field. You can examine the failure and decide whether to continue or fix the issue.

## How do I skip quality gates or tests?

Pass `skip_gates=True` or `skip_tests=True` to either `execute_with_approval()` or the `PipelineOrchestrator` constructor.

## Where are the source files?

- `src/attune/spec/**`
- `src/attune/pipeline/**`

**Tags:** `spec`, `planning`
