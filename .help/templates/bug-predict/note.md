---
type: note
feature: bug-predict
depth: note
generated_at: 2026-04-14T14:49:00.166872+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Bug prediction workflow architecture

## Overview

The bug prediction feature uses a three-agent orchestration pattern to identify potential bug hotspots in codebases. The workflow combines pattern scanning, risk correlation, and prevention advice into a unified analysis.

## Core components

The `BugPredictionWorkflow` class coordinates three specialized subagents:

- **pattern-scanner** — Detects common bug-prone code patterns
- **risk-correlator** — Analyzes relationships between code complexity and bug likelihood
- **prevention-advisor** — Generates actionable remediation strategies

Each subagent operates independently and reports findings as structured markdown. The workflow then synthesizes these findings into a single report with risk scoring (0-100), categorized bug predictions (HIGH/MEDIUM/LOW severity), and prioritized prevention suggestions.

## Report generation

The workflow produces two output formats:

- **Programmatic**: A `WorkflowResult` object containing structured data
- **Human-readable**: Formatted reports via `format_bug_predict_report()` with file paths, line numbers, and specific refactoring advice

The CLI entry point (`main()`) provides direct command-line access to the workflow for integration with development tools.

## Pattern detection

The system recognizes intentional design patterns that might otherwise trigger false positives. Code marked with keywords like "fallback", "graceful", or "best effort" receives adjusted risk scoring to account for deliberate error handling strategies.
