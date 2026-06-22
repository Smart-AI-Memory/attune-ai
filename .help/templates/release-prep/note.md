---
type: note
name: release-prep-note
feature: release-prep
depth: note
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 2e9628fb196173f4048d6aab29c024a2318abaeea4420bd4865253bdc1d46702
status: generated
---

# Note: release prep

## How the agent team is structured

Release prep runs four specialized agents in parallel, each responsible for a distinct domain. A `ReleasePrepTeam` coordinates their execution and aggregates results into a `ReleaseReadinessReport`.

| Agent | What it checks |
|---|---|
| `CodeQualityAgent` | Runs `ruff`, checks type hints and complexity |
| `TestCoverageAgent` | Runs `pytest --cov` and parses the coverage report |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence |
| `SecurityAuditorAgent` | Scans for vulnerabilities, secret leaks, and unsafe patterns |

Every agent extends `ReleaseAgent`, which handles CHEAP → CAPABLE → PREMIUM model-tier escalation automatically. The `escalated` field on `ReleaseAgentResult` records whether a given run required escalation.

## How readiness is decided

Each agent produces a `ReleaseAgentResult` with a `score`, a `confidence`, and a `findings` dict. Those results feed into a list of `QualityGate` checks. A gate has a `threshold` and an `actual` value; if `actual` falls short of `threshold` and `critical` is `True`, the gate blocks the release.

The final `ReleaseReadinessReport` rolls everything up:

- `approved` — `True` only when all critical gates pass
- `blockers` — gates or findings that must be resolved before shipping
- `warnings` — non-critical issues worth noting
- `confidence` — a string label reflecting overall certainty

Call `format_console_output()` to render a human-readable summary, or `to_dict()` to get a serializable dict for downstream tooling.

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
