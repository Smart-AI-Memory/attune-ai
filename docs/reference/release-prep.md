# Release Prep CLI reference

Run a preflight readiness assessment before publishing a release.

## Description

`release-prep` coordinates a team of specialized agents — `health-checker`, `security-scanner`, `changelog-generator`, and `release-assessor` — to assess whether a codebase is ready to ship. Each agent inspects its domain in parallel, and the results are synthesized into a `ReleaseReadinessReport` containing a go/no-go verdict, quality gate results, blockers, and warnings. The report is printed to stdout via `ReleaseReadinessReport.format_console_output()`.

## Usage

```
release-prep [OPTIONS] [PATH]
```

`PATH` is the path to the codebase root. Defaults to `.` (the current directory).

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--help` | — | Show this help message and exit |

## Output

The command prints the formatted `ReleaseReadinessReport` to stdout. The report includes a verdict, per-gate results, blockers, and warnings:

```
Release Readiness Assessment
Verdict: NO-GO
Confidence: medium
Timestamp: 2024-11-15T14:32:07.841200

Quality Gates
  health        FAIL   actual=0.72  threshold=0.80  Tests failing in CI
  security      PASS   actual=0.95  threshold=0.80
  changelog     PASS   actual=1.00  threshold=1.00
  code-quality  PASS   actual=0.88  threshold=0.75

Blockers (1)
  health — Tests failing in CI: 3 test failures in tests/test_core.py

Warnings (1)
  security — 2 advisory findings (non-critical)

Summary
  Release is NOT approved. Resolve 1 blocker before publishing.

Duration: 18.42s  |  Cost: $0.0031
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Assessment completed. Check the `Verdict` field in the report — `NO-GO` is still exit code `0`. |
| `1` | Command failed before producing a report (for example, invalid path or agent initialization error). |

## Related commands

- `attune help-docs ref-skill-release-prep` — full skill reference, including quality gate configuration
- `/release-prep check` — invoke the skill directly from Claude Code
- `attune help-docs skill-release-prep` — quickstart for running release prep interactively

<!-- attune-generated: source_hash=154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2 feature=release-prep kind=cli-reference generated_at=2026-06-02 -->
