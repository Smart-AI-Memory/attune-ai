---
type: troubleshooting
feature: agents
depth: troubleshooting
generated_at: 2026-04-14T15:09:19.904250+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Troubleshoot agents

## Before you start

The agents module provides AI-powered release preparation through parallel execution of specialized agents (test coverage, documentation, code quality) with progressive tier escalation from CHEAP to CAPABLE to PREMIUM models.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `ReleasePrepTeam.assess_readiness()` fails | Redis connection status and agent initialization parameters |
| Quality gates always fail | Threshold values in `QualityGate` configuration vs actual scores |
| Agent tier escalation not working | `ReleaseAgent.process()` escalation logic and model availability |
| Coverage reports incomplete | `TestCoverageAgent` pytest execution and coverage file parsing |
| Documentation checks missing | `DocumentationAgent` file access permissions for README/CHANGELOG |

## Step-by-step diagnosis

1. **Reproduce with minimal configuration.**
   Create a simple test case using `ReleasePrepTeam` with default quality gates:
   ```python
   from attune.agents import ReleasePrepTeam
   team = ReleasePrepTeam()
   result = team.assess_readiness(".")
   print(result.format_console_output())
   ```

2. **Check Redis connectivity.**
   If you're using Redis for state persistence, verify the connection:
   ```bash
   redis-cli ping  # Should return PONG
   ```
   Check Redis URL configuration in `ReleasePrepTeam.__init__()`

3. **Enable agent-level debugging.**
   Set debug logging and examine individual agent results:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)

   # Check individual agent execution
   result = team.assess_readiness(".")
   for agent_result in result.agent_results:
       print(f"Agent: {agent_result.agent_role}")
       print(f"Success: {agent_result.success}")
       print(f"Tier used: {agent_result.tier_used}")
   ```

4. **Verify tool dependencies.**
   Agents rely on external tools that may be missing:
   ```bash
   # For TestCoverageAgent
   pytest --version && pip show coverage

   # For CodeQualityAgent
   ruff --version

   # For DocumentationAgent
   ls -la README* CHANGELOG*
   ```

5. **Test agent decorators.**
   Check if operation decorators are causing issues:
   - `@safe_agent_operation` for error handling
   - `@retry_on_failure` for retry logic
   - `@with_cost_tracking` for API cost monitoring

## Common fixes

- **Fix Redis connection issues.**
  ```bash
  # Start Redis if not running
  redis-server

  # Or disable Redis persistence
  team = ReleasePrepTeam(redis_url=None)
  ```

- **Adjust quality gate thresholds.**
  ```python
  # Lower thresholds for stricter projects
  quality_gates = {
      "test_coverage": 0.8,  # 80% instead of default
      "documentation_score": 0.7
  }
  team = ReleasePrepTeam(quality_gates=quality_gates)
  ```

- **Install missing development tools.**
  ```bash
  pip install pytest coverage ruff
  # Ensure tools are in PATH
  which pytest ruff
  ```

- **Handle file permission issues.**
  ```bash
  # For documentation checks
  chmod +r README.md CHANGELOG.md
  # Ensure codebase_path is accessible
  ls -la /path/to/codebase
  ```

- **Force specific model tier.**
  ```python
  # Skip escalation for testing
  agent = ReleaseAgent("test", "tester")
  # Or check model availability
  from attune.agents import Tier
  # Verify CHEAP/CAPABLE/PREMIUM models are configured
  ```

## Source files

- `src/attune/agents/release_agent.py` - Base agent with tier escalation
- `src/attune/agents/test_coverage_agent.py` - Coverage analysis
- `src/attune/agents/documentation_agent.py` - Documentation checks
- `src/attune/agents/code_quality_agent.py` - Code quality analysis
- `src/attune/agents/release_prep_team.py` - Parallel agent coordination
- `src/attune/agent_factory/adapters/` - Framework integrations

**Tags:** `agents`, `ai`, `release`
