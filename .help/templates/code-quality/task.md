---
type: task
feature: code-quality
depth: task
generated_at: 2026-04-19T18:45:35.381319+00:00
source_hash: 44a3613be3cabe60572ba20a4d4a482a2b2727856106c44e43c6eafd7e2cc42e
status: generated
---

# Extend the code quality workflow

Use this procedure when you need to customize how the code review workflow analyzes code or modify which subagents it uses.

## Prerequisites

- Access to the project source code
- Understanding of the existing `CodeReviewWorkflow` class in `src/attune/workflows/code_review.py`

## Examine the workflow structure

1. Open `src/attune/workflows/code_review.py` and locate the `CodeReviewWorkflow` class.

2. Review the four specialized subagents defined in `_SUBAGENT_NAMES`:
   - `security-reviewer` — finds security vulnerabilities
   - `quality-reviewer` — identifies style and correctness issues
   - `perf-reviewer` — spots performance problems
   - `architect-reviewer` — analyzes structural concerns

3. Note how `_TASK_PROMPT_TEMPLATE` coordinates the subagents to produce a unified report with sections for Summary, Security, Quality, Performance, Architecture, and Suggestions.

## Choose your extension approach

- **To add a new subagent**: Extend the `_SUBAGENT_NAMES` list and update `_TASK_PROMPT_TEMPLATE` to include the new domain
- **To modify the report structure**: Update `_TASK_PROMPT_TEMPLATE` to change sections or scoring criteria
- **To create a specialized workflow**: Subclass `CodeReviewWorkflow` and override the `execute` method

## Implement your changes

1. Create your modifications in `src/attune/workflows/code_review.py`.

2. If adding subagents, ensure each has a clear domain focus that doesn't overlap with existing reviewers.

3. Follow the existing patterns for system prompts — be specific about expected output format and include file path citations.

4. Test your changes by calling the `execute` method with a sample codebase path.

## Verify the workflow works

Run a test review to confirm your changes produce the expected output:

```python
workflow = CodeReviewWorkflow()
result = workflow.execute(path="src/sample")
```

You should see structured markdown output with your new sections or subagent findings integrated into the unified report.

## Key files

- `src/attune/workflows/code_review.py` — main workflow implementation
