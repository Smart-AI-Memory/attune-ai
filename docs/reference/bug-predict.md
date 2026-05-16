# Bug Predict CLI Reference

Predict likely bug locations based on code patterns and complexity.

## Description

`bug-predict` scans a codebase path using three specialized subagents — `pattern-scanner`, `risk-correlator`, and `prevention-advisor` — and synthesizes their findings into a unified risk report. It identifies high-risk patterns such as dangerous `eval()` usage, broad exception handling, and incomplete code markers. The report includes an overall risk score, per-finding file paths and line numbers, and prioritized prevention recommendations.

## Usage

```
bug-predict [PATH]
```

`PATH` is the file or directory to scan. Defaults to `src/` when omitted.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--help` | — | Show help and exit |

## Output

On success, `bug-predict` prints a structured markdown report to stdout:

```
Bug Prediction Report
Risk Score: 73/100 | Files: 34 | Findings: 8

## Summary
<2–3 sentence executive summary of predicted bug hotspots>

## Bugs

HIGH (2 findings)
  src/hooks/executor.py:89   dangerous_eval  eval() on user input
  src/plugins/loader.py:142  dangerous_eval  exec() in plugin loader

MEDIUM (3 findings)
  src/api/webhook.py:67      broad_exception  bare except: masks errors
  src/config.py:203          broad_exception  except Exception without logging
  src/memory/store.py:88     broad_exception  swallowed error in write path

LOW (3 findings)
  src/auth/session.py:45     incomplete_code  TODO: add token rotation
  src/api/routes.py:112      incomplete_code  FIXME: rate limiting
  src/cli_router.py:78       incomplete_code  HACK: temporary workaround

## Suggestions
1. <highest-priority refactoring recommendation>
2. <testing recommendation for flagged files>
```

Each finding includes the file path, line number, pattern type (`dangerous_eval`, `broad_exception`, or `incomplete_code`), and a plain-English description.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Scan completed and report written successfully |
| `1` | Scan failed (invalid path, workflow error, or subagent failure) |

## Related commands

- `attune help-docs ref-skill-bug-predict` — full skill reference
- `/bug-predict` — invoke the skill directly inside Claude Code
- `security-audit` — vulnerability-focused scan of the same codebase

<!-- attune-generated: source_hash=c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde feature=bug-predict kind=cli-reference generated_at=2026-05-16 -->
