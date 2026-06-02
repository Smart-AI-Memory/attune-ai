---
type: reference
name: bug-predict-reference
feature: bug-predict
depth: reference
generated_at: 2026-06-02T10:56:02.668568+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Bug Predict reference

Predict likely bug locations based on code patterns and complexity.

## Classes

| Class | Description |
|-------|-------------|
| `BugPredictionWorkflow` | SDK-native bug prediction with three specialized subagents. |

### `BugPredictionWorkflow`

#### Constructor

| Parameters | Type | Default | Description |
|------------|------|---------|-------------|
| `system_prompt_suffix` | `str` | `''` | Text appended to the orchestrator system prompt. |
| `**kwargs` | `Any` | — | Forwarded to the parent workflow class. |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `execute` | `**kwargs: Any` | `WorkflowResult` | Run the bug prediction workflow and return structured results. |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_bug_predict_report` | `result: dict, input_data: dict` | `str` | Format bug prediction output as a human-readable report. |
| `main` | — | — | CLI entry point for the bug prediction workflow. |

## Constants

| Constant | Type | Members |
|----------|------|---------|
| `_SUBAGENT_NAMES` | `list` | `'pattern-scanner'`, `'risk-correlator'`, `'prevention-advisor'` |
| `_INTENTIONAL_KEYWORDS` | `list` | `'fallback'`, `'ignore'`, `'optional'`, `'best effort'`, `'graceful'`, `'intentional'` |
| `_SCANNER_TEST_PATTERNS` | `list` | `'test_bug_predict'`, `'test_scanner'`, `'test_security_scan'` |

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_report.py`

## Tags

`bugs`, `prediction`, `scanning`
