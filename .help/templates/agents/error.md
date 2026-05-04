---
depth: error
feature: agents
generated_at: 2026-04-14 15:08:45.078322+00:00
manual: true
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
type: error
---

# Agents errors

This page covers failures in the Attune AI agent system, including release preparation agents, state management, and agent factory adapters.

## Common error signatures

**Agent operation failures:**
- `AgentOperationError` — Raised by the `@safe_agent_operation` decorator when agent operations fail
- `ValueError: Input must be a dict, got {type}` — Input validation failure from `@validate_input`
- `ValueError: Missing required fields: {fields}` — Required field validation failure

**State and persistence errors:**
- Redis connection errors when `redis_client` is misconfigured
- State store serialization failures during agent state persistence
- Recovery manager errors when restoring agent execution state

**Adapter initialization failures:**
- Import errors from lazy-loaded framework adapters (`get_langchain_adapter`, `get_langgraph_adapter`, etc.)
- Missing dependencies for AutoGen, Haystack, or other framework integrations
- Configuration errors in `WizardAgent` wrapper initialization

**Release preparation failures:**
- Quality gate threshold violations in `ReleasePrepTeam.assess_readiness()`
- Command execution failures in specialized agents (pytest, ruff, coverage tools)
- Tier escalation timeouts during CHEAP -> CAPABLE -> PREMIUM progression

## Where errors originate

Agent system errors typically originate from these key operations:

- **Agent processing**: `ReleaseAgent.process()` and specialized agent implementations (`TestCoverageAgent`, `DocumentationAgent`, `CodeQualityAgent`)
- **Team coordination**: `ReleasePrepTeam.assess_readiness()` during parallel agent execution
- **State management**: Agent state store operations and Redis persistence
- **Framework adapters**: Lazy imports in `get_*_adapter()` functions and `wrap_wizard()` calls
- **Input validation**: Decorator-enforced validation in agent operations

## How to diagnose

1. **Check agent execution logs.** The `@safe_agent_operation` decorator logs all failures with context. Look for agent operation names and error details in your logs.

2. **Verify codebase path and permissions.** Release preparation agents run external tools (pytest, ruff) on the codebase. Ensure the `codebase_path` parameter points to a readable directory with proper permissions.

3. **Test Redis connectivity.** If using state persistence, verify your Redis connection with a simple ping. State store errors often cascade from Redis connectivity issues.

4. **Validate quality gate configuration.** `ReleasePrepTeam` failures often stem from misconfigured quality gates. Check that threshold values are reasonable for your project (coverage percentages, complexity scores).

5. **Check tier escalation limits.** Review your model tier configuration if agents are failing during escalation. Budget limits or API rate limits can cause tier progression failures.

6. **Verify framework dependencies.** Adapter import errors indicate missing optional dependencies. Install the required package for your target framework (langchain, autogen, etc.).

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

**Tags:** `agents`, `ai`, `release`
