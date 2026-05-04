---
type: task
feature: spec-engine
depth: task
generated_at: 2026-05-04T02:39:14.240032+00:00
source_hash: dfb05ee79541939dac0529f016b44e21b04ef77d58372da1d6d5b857d97ef4d0
status: generated
---

# Work with spec engine

Use spec engine when you need to modify how spec-driven development orchestrates task execution, manages pipeline state, or presents plan information to users.

## Prerequisites

- Access to the project source code
- Understanding of the five-phase spec workflow (brainstorm, decompose, review, approve, execute)
- Basic familiarity with XML task blocks and quality gates

## Identify the component to modify

1. **Determine which aspect of spec engine you need to change:**
   - **Task execution flow**: Modify `PipelineOrchestrator` in `src/attune/pipeline/orchestrator.py`
   - **Plan file reading**: Modify `read_spec()` in `src/attune/pipeline/spec_reader.py`
   - **Task presentation**: Modify presenter functions in `src/attune/spec/presenter.py`
   - **State management**: Modify state functions in `src/attune/spec/state.py`
   - **Execution control**: Modify runner functions in `src/attune/spec/runner.py`

2. **Read the target function's docstring and signature** to confirm it handles your use case.

3. **Check the function's current implementation** to understand its input processing, error handling, and return format.

## Modify the implementation

4. **Update the function code** following these patterns:
   - Use the existing error handling style (raising `ValueError` or `FileNotFoundError` with descriptive messages)
   - Maintain the same return type and structure
   - Preserve existing logging and state management calls

5. **Update related dataclass fields** if your change affects `TaskResult`, `PipelineResult`, or `SpecState`.

## Verify your changes

6. **Run targeted tests** to catch regressions:
   ```bash
   pytest -k "spec" --verbose
   ```

7. **Test with a real spec file** by running a complete pipeline to ensure quality gates and state persistence work correctly.

## Success criteria

Your modification works when:
- All existing tests pass
- The spec engine correctly processes XML task blocks from plan files
- Pipeline execution maintains proper state tracking between tasks
- Quality gate results display accurately in task presentations
- No regressions appear in the five-phase workflow (brainstorm through execute)
