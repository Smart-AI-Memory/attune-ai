---
feature: spec-engine
depth: reference
generated_at: 2026-04-04T02:25:50.655437+00:00
source_hash: 9a5e04c503c29d581c2787038d961b7e425b0163cece10376e6b23a94fbb5aa4
status: generated
---

# Spec Engine Reference

## Classes

| Class | Description | File |

|-------|-------------|------|

| `SpecState` | Execution state for a spec plan. | `src/attune/spec/state.py` |

| `TaskResult` | Result of executing a single pipeline task. | `src/attune/pipeline/models.py` |

| `PipelineResult` | Aggregated result from a full pipeline run. | `src/attune/pipeline/models.py` |

| `PipelineOrchestrator` | Executes tasks from an XML spec with quality gates. | `src/attune/pipeline/orchestrator.py` |


## Functions

| Function | Description | File |

|----------|-------------|------|

| `present_tasks()` | Format all tasks as a human-readable markdown table. | `src/attune/spec/presenter.py` |

| `present_task_detail()` | Format a single task with full details. | `src/attune/spec/presenter.py` |

| `present_task_result()` | Format a task's execution result with quality gate status. | `src/attune/spec/presenter.py` |

| `format_progress_bar()` | Visual progress indicator for task execution. | `src/attune/spec/presenter.py` |

| `get_pending_tasks()` | Filter tasks to only those not yet completed. | `src/attune/spec/runner.py` |

| `load_state()` | Read spec-state from an HTML comment in a plan file. | `src/attune/spec/state.py` |

| `save_state()` | Write or update the spec-state comment in a plan file. | `src/attune/spec/state.py` |

| `clear_state()` | Remove the spec-state comment from a plan file. | `src/attune/spec/state.py` |

| `find_resumable_plans()` | Find plan files with incomplete execution state. | `src/attune/spec/state.py` |

| `read_spec()` | Read a plan file and extract XML task blocks. | `src/attune/pipeline/spec_reader.py` |


## Source Files

- `src/attune/spec/**`

- `src/attune/pipeline/**`


## Tags

`spec`, `planning`
