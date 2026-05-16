# Smart Test CLI Reference

Analyze test coverage gaps and generate pytest tests for uncovered code.

## Description

`smart-test` runs an autonomous test coverage audit and test generation workflow against a Python codebase. It parses `pytest-cov` coverage output, identifies untested functions and branches, and writes executable pytest tests with edge cases and error-path assertions. Output is a structured report covering coverage gaps, generated test files, and prioritized next steps.

## Usage

```
smart-test [OPTIONS] <PATH>
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--help` | — | Show this help message and exit |

## Output

On success, `smart-test` prints a structured Markdown report to stdout with the following sections:

```
## Summary
Overall test generation summary — how many functions were analyzed,
how many test cases were designed, and how many test files were written.

## Coverage
Current coverage analysis and areas that need testing.

## Test Gaps
Functions and modules that lack adequate test coverage.

## Suggestions
Actionable next steps for improving test coverage, ordered by priority.
```

Generated test files are written to `tests/behavioral/generated/` by default.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Workflow completed; report written to stdout |
| `1` | Workflow failed — coverage file not found, invalid coverage JSON, or missing `files` key in coverage data |

## Related commands

- `/smart-test` — invoke the same workflow as a Claude Code skill from a conversation
- `fix-test` — diagnose and repair failing pytest tests after a refactor or dependency upgrade

<!-- attune-generated: source_hash=2ed25e274258323117a16cf96fcb5bf0a40e45a9bb8c246d4abfdc74365cfabc feature=smart-test kind=cli-reference generated_at=2026-05-16 -->
