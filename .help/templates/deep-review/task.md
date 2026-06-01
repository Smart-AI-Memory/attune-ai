---
feature: deep-review
depth: task
generated_at: 2026-06-01T11:59:09.446905+00:00
source_hash: c88c39a4d669dd53e0c79a38f05bf3f121d25317b59202f71eed73be8dc817a0
status: generated
---

# Work with deep review

Use deep review when you need to multi-pass deep code review — security, quality, and test gap analysis.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/deep_review.py

## Steps

1. **Understand the class hierarchy.**
   Read the interfaces to see how deep review
   is structured before extending or modifying.
   The key classes are:
   - `DeepReviewAgentSDKWorkflow` in `src/attune/workflows/deep_review.py` — Multi-pass deep code review using Claude Agent SDK subagents.
2. **Decide whether to extend or modify.**
   If the class has subclasses, extend with a new one
   rather than changing the base. If it stands alone,
   modify directly.

3. **Make your change.**
   Follow existing patterns — naming, error handling,
   and logging style.

4. **Run the related tests.**
   Target with `pytest -k "deep-review"`.

## Key files

- `src/attune/workflows/deep_review.py`

## Common modifications

Classes you are most likely to extend:

- `DeepReviewAgentSDKWorkflow` in `src/attune/workflows/deep_review.py`
