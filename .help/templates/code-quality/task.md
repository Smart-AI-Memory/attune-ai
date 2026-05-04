---
type: task
feature: code-quality
depth: task
generated_at: 2026-05-04T02:24:21.082114+00:00
source_hash: 0d2aa6913a2dae27ec39d314c14f1f9a65365582fb2ba40d7060f571d73ca77e
status: generated
---

# Extend the code quality workflow

Use this procedure when you need to customize how code reviews work or add new review capabilities to the four-subagent system.

## Prerequisites

- Access to the project source code
- Understanding of the `CodeReviewWorkflow` class in `src/attune/workflows/code_review.py`

## Examine the current workflow structure

1. Open `src/attune/workflows/code_review.py` and review the `CodeReviewWorkflow` class.

2. Note the four specialized subagents defined in `_SUBAGENT_NAMES`:
   - `security-reviewer` — finds vulnerabilities and security issues
   - `quality-reviewer` — catches style violations and likely bugs
   - `perf-reviewer` — identifies performance bottlenecks
   - `architect-reviewer` — evaluates structural design

3. Study the `_TASK_PROMPT_TEMPLATE` to understand how the subagents coordinate and produce the unified report format.

## Choose your extension approach

1. **For new review types**: Create a subclass of `CodeReviewWorkflow` that modifies `_SUBAGENT_NAMES` to include your custom reviewer.

2. **For different orchestration**: Override the `execute` method to change how subagents interact or how results are synthesized.

3. **For custom prompts**: Override `_SYSTEM_PROMPT` or `_TASK_PROMPT_TEMPLATE` to adjust the review focus or output format.

## Implement your extension

1. Create a new class inheriting from `CodeReviewWorkflow`:
   ```python
   class CustomCodeReviewWorkflow(CodeReviewWorkflow):
       _SUBAGENT_NAMES = ['security-reviewer', 'quality-reviewer', 'perf-reviewer', 'architect-reviewer', 'your-custom-reviewer']
   ```

2. Override any constants or methods you need to modify while preserving the base workflow's structure.

3. Ensure your custom subagents follow the same reporting format expected by the synthesis step.

## Test your changes

1. Run the code quality tests to verify existing functionality still works:
   ```bash
   pytest -k "code-quality"
   ```

2. Test your custom workflow with a sample codebase to confirm the new subagent integrates properly with the unified report.

## Verify success

Your extension works correctly when:
- All existing tests pass
- Your custom subagent appears in the synthesized report under the appropriate section
- The overall health score (0-100) and executive summary still generate properly
- File paths and line numbers are correctly cited in findings
