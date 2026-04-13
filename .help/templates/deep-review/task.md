---
feature: deep-review
depth: task
generated_at: 2026-04-13T16:56:09.369743+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Work with deep review

Use deep review when you need comprehensive code analysis across multiple passes including security vulnerabilities, code quality issues, and test coverage gaps.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/deep_review.py

## Steps

1. **Understand the class hierarchy.**
   Read the interfaces to see how deep review
   is structured before extending or modifying.
   The key classes are:
   - `DeepReviewAgentSDKWorkflow` in `src/attune/workflows/deep_review.py` — Orchestrates multi-pass deep code review using Claude Agent SDK subagents.
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
