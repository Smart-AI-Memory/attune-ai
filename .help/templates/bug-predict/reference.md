---
type: reference
feature: bug-predict
depth: reference
generated_at: 2026-05-04T02:26:43.524453+00:00
source_hash: 1686df43f96bd1cdf341101bfab34ee6e5f7f50c3733daf08c8827b94e8a7fef
status: generated
---

# Bug prediction reference

Scan codebases for patterns that historically cause production incidents and predict where failures are most likely to occur.

## Classes

| Class | Description |
|-------|-------------|
| `BugPredictionWorkflow` | Coordinates three specialized subagents to analyze code patterns, risk factors, and prevention strategies |

### BugPredictionWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the workflow with configuration options |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Run the complete bug prediction analysis |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_bug_predict_report` | `result: dict, input_data: dict` | `str` | Format prediction results as a human-readable report with severity groupings |
| `main` | | | CLI entry point for standalone bug prediction workflow |

## Constants

| Constant | Values | Description |
|----------|---------|-------------|
| `_SUBAGENT_NAMES` | `pattern-scanner`, `risk-correlator`, `prevention-advisor` | Specialized agents that analyze different aspects of bug risk |
| `_INTENTIONAL_KEYWORDS` | `fallback`, `ignore`, `optional`, `best effort`, `graceful`, `intentional` | Keywords that suppress false positives for intentionally broad exception handling |
| `_SCANNER_TEST_PATTERNS` | `test_bug_predict`, `test_scanner`, `test_security_scan` | Test file patterns excluded from bug scanning |

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_*.py`

## Tags

`bugs`, `prediction`, `scanning`, `race-condition`
