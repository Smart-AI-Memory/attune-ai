---
feature: spec-engine
depth: task
generated_at: 2026-04-04T02:25:50.655351+00:00
source_hash: 9a5e04c503c29d581c2787038d961b7e425b0163cece10376e6b23a94fbb5aa4
status: generated
---

# Working with Spec Engine

## Overview

Common tasks for modifying or extending spec engine.

## Key Files

- `src/attune/spec/**`

- `src/attune/pipeline/**`


## Common Modifications

Functions you may need to modify:

- `present_tasks()` in `src/attune/spec/presenter.py`

- `present_task_detail()` in `src/attune/spec/presenter.py`

- `present_task_result()` in `src/attune/spec/presenter.py`

- `format_progress_bar()` in `src/attune/spec/presenter.py`

- `get_pending_tasks()` in `src/attune/spec/runner.py`

- `load_state()` in `src/attune/spec/state.py`

- `save_state()` in `src/attune/spec/state.py`

- `clear_state()` in `src/attune/spec/state.py`
