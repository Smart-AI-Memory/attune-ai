---
type: warning
feature: bug-predict
depth: warning
generated_at: 2026-04-14T14:48:02.836857+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Bug Predict cautions

## What to watch for

The bug prediction workflow coordinates three specialized subagents to analyze code patterns and predict potential issues. Several aspects of this multi-agent system can produce unexpected results.

## Risk areas

**False positive cascades in subagent coordination**
When one subagent misclassifies code patterns, the other two can amplify the error. The `pattern-scanner` may flag intentional fallback code as bugs, causing `risk-correlator` to inflate severity scores and `prevention-advisor` to suggest unnecessary refactoring. Check for keywords like "fallback", "ignore", "optional", and "graceful" in flagged code — these often indicate intentional design choices rather than bugs.

**Report formatting assumes structured input**
The `format_bug_predict_report()` function expects specific keys in the result dictionary (risk scores, file paths, severity levels). If subagents return malformed data or unexpected structures, the formatter fails silently or produces garbled output. Always validate that your workflow result contains the expected sections before formatting.

**CLI execution bypasses workflow validation**
The `main()` CLI entry point directly instantiates `BugPredictionWorkflow` without input validation. Malformed file paths, missing directories, or corrupted codebases can cause the workflow to hang or crash partway through analysis. The orchestrator's system prompt assumes valid code structure, so preprocessing failures propagate unpredictably through the subagent chain.

## How to avoid problems

**Validate subagent output before synthesis**
Before calling `format_bug_predict_report()`, verify that each subagent returned structured markdown with the expected sections. Missing or malformed subagent output will corrupt the final report.

**Test with intentional code patterns**
Include test cases with fallback logic, error handling, and graceful degradation patterns. The prediction system should distinguish between intentional design choices and actual bugs — failure to do so generates noisy reports that mask real issues.

**Handle workflow interruption gracefully**
The three-subagent coordination can fail at any stage. Implement timeout handling and partial result recovery in your integration code, since a hanging `risk-correlator` will block the entire prediction pipeline.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_*.py`

**Tags:** `bugs`, `prediction`, `scanning`
