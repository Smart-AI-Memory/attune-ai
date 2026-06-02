# Deep Review CLI reference

Multi-pass deep code review — security, quality, and test gap analysis.

## Description

`deep-review` runs a multi-pass code review by coordinating three specialized subagents: a security reviewer, a quality reviewer, and a test-gap reviewer. Each subagent analyzes the target path independently, then the orchestrator synthesizes their findings into a single consolidated report. The report includes an overall code health score, severity-ordered findings per domain, and a prioritized list of actionable next steps.

## Usage

```
attune workflow run deep-review --path PATH
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path PATH` | required | Path to the directory or file to review |
| `--help` | — | Show this message and exit |

## Output

The command prints a structured Markdown report to stdout:

```
## Summary
Code health score: 74/100
3 critical findings, 7 warnings, 12 informational. The codebase has
adequate structure but contains two authentication-related vulnerabilities
and significant gaps in unit test coverage for the payments module.

## Security
[CRITICAL] src/auth/session.py:42 — Session token not rotated after privilege escalation.
[WARNING]  src/api/endpoints.py:118 — User-supplied input passed to subprocess without sanitization.

## Quality
[WARNING]  src/payments/processor.py:87 — Cyclomatic complexity exceeds threshold (score: 24).
[INFO]     src/utils/formatters.py:12 — Dead code block unreachable after early return.

## Test Gaps
[HIGH]     src/payments/ — No unit tests for refund and chargeback paths.
[MEDIUM]   src/auth/ — Integration tests do not cover token expiry edge cases.

## Suggestions
1. Rotate session tokens on privilege escalation (addresses session.py:42).
2. Sanitize subprocess inputs in endpoints.py:118.
3. Add unit tests for payments refund and chargeback paths.
...
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Review completed and report written to stdout |
| `1` | Workflow failed — path not found, subagent error, or unhandled exception |

## Related commands

- `attune workflow run code-review` — Single-pass code quality review
- `attune workflow run security-audit` — Security-focused audit without quality or test-gap passes

<!-- attune-generated: source_hash=e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4 feature=deep-review kind=cli-reference generated_at=2026-06-02 -->
