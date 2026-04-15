---
type: faq
feature: release-prep
depth: faq
generated_at: 2026-04-14T14:51:00.270218+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Release Prep FAQ

## What is release prep?

A pre-release quality gate that runs automated checks before you ship code, including test coverage analysis, code quality scanning, security audits, and documentation verification.

## When should I use release prep?

Use release prep before publishing any version of your code — whether it's a patch, minor, or major release. The workflow catches quality issues, security vulnerabilities, and missing documentation that could affect users.

## What's the main entry point?

Start with one of these classes based on your needs:

- `ReleasePreparationWorkflow` — Run the full workflow with all quality checks via Agent SDK subagents
- `ReleasePrepTeam` — Coordinate multiple specialized agents in parallel for faster execution
- Individual agents like `TestCoverageAgent` or `CodeQualityAgent` — Run specific checks only

Read the docstring of your chosen class before calling any methods.

## How do the quality gates work?

Each agent runs checks and reports a score against configurable thresholds. The system aggregates results into a `ReleaseReadinessReport` that includes:

- Overall pass/fail recommendation
- Individual quality gate results (test coverage, code quality, documentation, security)
- Specific blockers that must be fixed
- Warnings for non-critical issues

## Can I customize the quality thresholds?

Yes. Pass a `quality_gates` dictionary to `ReleasePrepTeam.__init__()` to set custom thresholds for test coverage, code complexity, documentation coverage, and other metrics.

## How do I debug failed quality checks?

1. Run `pytest -k "release" -v` to verify the feature works in isolation
2. Check the `ReleaseReadinessReport.blockers` list for specific failures
3. Use `report.format_console_output()` to see detailed findings from each agent
4. Add logging to see which tier (CHEAP/CAPABLE/PREMIUM) each agent escalated to

## Where are the source files?

- `src/attune/workflows/release_prep.py` — Main workflow
- `src/attune/agents/release/` — Individual quality check agents

**Tags:** `release`, `publishing`, `quality`
