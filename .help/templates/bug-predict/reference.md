---
type: reference
name: bug-predict-reference
feature: bug-predict
depth: reference
generated_at: 2026-05-16T06:19:45.775437+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Bug Predict reference

Scan a codebase for code patterns and complexity signals that predict likely bug locations, then format findings into a structured risk report.

## Classes

| Class | Description |
|-------|-------------|
| `BugPredictionWorkflow` | SDK-native bug prediction with three specialized subagents. |

### `BugPredictionWorkflow`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `self, *, system_prompt_suffix: str = '', **kwargs: Any` | `None` | Initializes the workflow. |
| `execute` | `self, **kwargs: Any` | `WorkflowResult` | Runs the three-subagent prediction pipeline and returns results. |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_bug_predict_report` | `result: dict, input_data: dict` | `str` | Formats bug prediction output as a human-readable report. |
| `main` | — | — | CLI entry point for the bug prediction workflow. |

## Constants

| Constant | Type | Members |
|----------|------|---------|
| `_SUBAGENT_NAMES` | list | `'pattern-scanner'`, `'risk-correlator'`, `'prevention-advisor'` |
| `_INTENTIONAL_KEYWORDS` | list | `'fallback'`, `'ignore'`, `'optional'`, `'best effort'`, `'graceful'`, `'intentional'` |
| `_SCANNER_TEST_PATTERNS` | list | `'test_bug_predict'`, `'test_scanner'`, `'test_security_scan'` |
| `_SYSTEM_PROMPT` | str | `'You are a bug prediction orchestrator. You coordinate three specialized subagents to produce a unified bug prediction report. Be thorough but concise. Cite file paths and line numbers when possible.'` |
| `_TASK_PROMPT_TEMPLATE` | str | `'Analyze the codebase at {path} using the three specialized subagents below…'` — full template includes `## Summary`, `## Bugs`, and `## Suggestions` sections. |

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_report.py`

## Tags

`bugs`, `prediction`, `scanning`
