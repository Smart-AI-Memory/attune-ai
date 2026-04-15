---
type: tip
feature: spec-engine
depth: tip
generated_at: 2026-04-14T15:26:24.005828+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Use state persistence to resume interrupted spec executions

Start long-running specs with `execute_with_approval()` instead of `PipelineOrchestrator.run_all()` when you expect interruptions. The approval loop automatically saves your progress after each task completion, letting you pick up exactly where you left off.

Check for resumable work with `find_resumable_plans()` before starting new specs — you might already have partially completed plans waiting in `.claude/plans`.

## Why this matters

Large specs can take hours to complete, and manual approval means you'll step away from the terminal. Without state persistence, a single interruption forces you to restart from the beginning, wasting both time and API costs from re-executing completed tasks.
