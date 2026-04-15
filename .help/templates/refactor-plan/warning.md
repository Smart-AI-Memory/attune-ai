---
type: warning
feature: refactor-plan
depth: warning
generated_at: 2026-04-14T14:52:32.939069+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Refactor Plan cautions

## What to watch for

The refactor planning workflow orchestrates multiple subagents to analyze tech debt and generate prioritized improvement roadmaps. Watch for coordination failures between subagents and report formatting edge cases.

## Risk areas

**Subagent coordination failures in RefactorPlanWorkflow.execute()**
The workflow depends on three specific subagents ('debt-scanner', 'impact-analyzer', 'plan-generator') completing successfully. If any subagent fails or returns malformed data, the synthesis step can produce incomplete or misleading refactoring recommendations. Network timeouts or API rate limits affecting the Agent SDK can cascade into workflow failures.

**Report formatting crashes with unexpected result structures**
The `format_refactor_plan_report()` function expects specific keys in the result dictionary (Summary, Refactoring, Suggestions sections). When subagents return unexpected data structures or missing sections, the formatter can raise KeyError exceptions or generate malformed markdown that breaks downstream tools.

**CLI entry point assumes clean execution environment**
The `main()` function provides no error recovery for common deployment issues like missing configuration files, insufficient permissions, or network connectivity problems. Failed workflows leave no partial results, making it difficult to diagnose which subagent or processing step caused the failure.

## How to avoid problems

1. **Validate subagent outputs before synthesis.** Check that all three required subagents completed and returned the expected data structure before attempting to format the final report. Handle partial results gracefully when possible.

2. **Test with realistic codebase complexity.** Small test projects may not trigger the coordination edge cases that appear with large codebases or when subagents disagree about priorities. Include integration tests with real-world repository sizes.

3. **Monitor subagent execution time and failures.** Set reasonable timeouts for each subagent and log intermediate results. If the debt-scanner consistently times out on certain file types, you may need to adjust the analysis scope or exclude problematic directories.

4. **Verify report format assumptions.** The template expects structured markdown with specific section headers. If you modify the `_TASK_PROMPT_TEMPLATE`, ensure the output format remains compatible with downstream tools that consume the refactoring reports.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
