---
feature: spec-engine
depth: reference
generated_at: 2026-04-13T17:03:04.656579+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Spec Engine reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `SpecState` | Tracks execution progress and completion status for a spec plan | `src/attune/spec/state.py` |
| `TaskResult` | Contains the outcome and metadata from a single pipeline task execution | `src/attune/pipeline/models.py` |
| `PipelineResult` | Provides aggregated results and summary statistics from a complete pipeline run | `src/attune/pipeline/models.py` |
| `PipelineOrchestrator` | Runs XML spec tasks sequentially with automated quality gate validation | `src/attune/pipeline/orchestrator.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `present_tasks()` | Displays all spec tasks in a structured markdown table format | `src/attune/spec/presenter.py` |
| `present_task_detail()` | Shows comprehensive details for a specific task including parameters and requirements | `src/attune/spec/presenter.py` |
| `present_task_result()` | Formats task execution outcomes with quality gate pass/fail indicators | `src/attune/spec/presenter.py` |
| `format_progress_bar()` | Generates a visual progress indicator showing task completion percentage | `src/attune/spec/presenter.py` |
| `get_pending_tasks()` | Returns only tasks that have not completed successfully | `src/attune/spec/runner.py` |
| `execute_with_approval()` | Runs spec tasks with manual approval prompts before each task execution | `src/attune/spec/runner.py` |
| `load_state()` | Extracts saved execution state from HTML comments embedded in plan files | `src/attune/spec/state.py` |
| `save_state()` | Persists current execution state as HTML comments within plan files | `src/attune/spec/state.py` |
| `clear_state()` | Deletes execution state comments from plan files to reset progress | `src/attune/spec/state.py` |
| `find_resumable_plans()` | Locates plan files containing saved execution state that can be resumed | `src/attune/spec/state.py` |
| `read_spec()` | Parses plan files to extract and validate XML task definition blocks | `src/attune/pipeline/spec_reader.py` |


## Source files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

## Tags

`spec`, `planning`
