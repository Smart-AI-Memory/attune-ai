---
feature: code-quality
depth: task
generated_at: 2026-04-13T16:54:01.723098+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Work with code quality

Use the code quality workflow when you need to perform comprehensive code reviews that check for style issues, potential bugs, and structural problems using specialized AI agents.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/code_review.py

## Steps

1. **Understand the class hierarchy.**
   Read the interfaces to see how the code review workflow
   is structured before extending or modifying.
   The key class is:
   - `CodeReviewWorkflow` in `src/attune/workflows/code_review.py` — SDK-native code review with four specialized subagents.
2. **Decide whether to extend or modify.**
   If the class has subclasses, extend with a new one
   rather than changing the base. If it stands alone,
   modify directly.

3. **Make your change.**
   Follow existing patterns — naming, error handling,
   and logging style.

4. **Run the related tests.**
   Target with `pytest -k "code-quality"`.

## Key files

- `src/attune/workflows/code_review.py`
- `src/attune/workflows/code_review_*.py`

## Common modifications

Classes you are most likely to extend:

- `CodeReviewWorkflow` in `src/attune/workflows/code_review.py`
