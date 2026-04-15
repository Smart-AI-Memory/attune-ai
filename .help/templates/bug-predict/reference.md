---
type: reference
feature: bug-predict
depth: reference
generated_at: 2026-04-14T14:47:43.358870+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Bug Predict reference

## Classes

| Class | Description | Methods |
|-------|-------------|---------|
| `BugPredictionWorkflow` | SDK-native bug prediction with three specialized subagents | `__init__(**kwargs: Any) -> None`<br>`execute(**kwargs: Any) -> WorkflowResult` |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_bug_predict_report` | `result: dict, input_data: dict` | `str` | Format bug prediction output as a human-readable report |
| `main` | None | None | CLI entry point for bug prediction workflow |

## Constants

| Constant | Type | Value |
|----------|------|-------|
| `SUBAGENT_NAMES` | list | `{'pattern-scanner', 'risk-correlator', 'prevention-advisor'}` |
| `SYSTEM_PROMPT` | str | `'You are a bug prediction orchestrator. You coordinate three specialized subagents to produce a unified bug prediction report. Be thorough but concise. Cite file paths and line numbers when possible.'` |
| `TASK_PROMPT_TEMPLATE` | str | Template for analyzing codebase with structured markdown output sections |
| `INTENTIONAL_KEYWORDS` | list | `{'fallback', 'ignore', 'optional', 'best effort', 'graceful', 'intentional'}` |
| `SCANNER_TEST_PATTERNS` | list | `{'test_bug_predict', 'test_scanner', 'test_security_scan'}` |

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_*.py`

## Tags

`bugs`, `prediction`, `scanning`
