---
type: concept
feature: agents
depth: concept
generated_at: 2026-04-14T15:07:39.750580+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Agents

The agents system orchestrates AI-powered release preparation by running specialized agents that assess code quality, test coverage, and documentation completeness before determining if your codebase is ready for release.

## Architecture

The system centers around the `ReleasePrepTeam`, which coordinates parallel execution of specialized agents. Each agent inherits from `ReleaseAgent` and implements progressive tier escalation — starting with cheaper AI models and escalating to more capable (and expensive) models when initial attempts fail.

**Core agent types:**
- **`TestCoverageAgent`** — Executes `pytest --cov` and analyzes coverage reports to ensure adequate test coverage
- **`DocumentationAgent`** — Validates docstring coverage, README currency, and CHANGELOG presence
- **`CodeQualityAgent`** — Runs `ruff` linting and examines type hints and code complexity metrics

**Tier escalation system:**
- **`CHEAP`** — Fast, cost-effective models for initial assessment
- **`CAPABLE`** — Mid-tier models when cheap models struggle
- **`PREMIUM`** — Advanced models for complex analysis requiring high accuracy

## Release readiness assessment

The `ReleasePrepTeam.assess_readiness()` method runs all agents in parallel and aggregates results into a `ReleaseReadinessReport`. This report includes:

- **Quality gates** — Pass/fail thresholds for coverage percentages, documentation completeness, and code quality scores
- **Agent results** — Individual findings from each specialized agent, including confidence scores and execution costs
- **Release approval** — Binary decision on whether the codebase meets release standards
- **Blockers and warnings** — Specific issues that prevent release or require attention

## Framework integrations

The system provides adapters for popular AI agent frameworks through lazy-loaded functions like `get_langchain_adapter()`, `get_autogen_adapter()`, and `get_haystack_adapter()`. You can also wrap existing wizards as agents using `wrap_wizard()`.

State persistence ensures agent operations can recover from failures, while decorators like `@safe_agent_operation` and `@retry_on_failure` provide robust error handling and automatic retry logic with exponential backoff.
