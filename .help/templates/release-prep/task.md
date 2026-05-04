---
type: task
feature: release-prep
depth: task
generated_at: 2026-05-04T02:27:06.561642+00:00
source_hash: 154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2
status: generated
---

# Work with release prep

Use release prep when you need to customize the pre-release quality gates, add new check types, or modify the agent escalation behavior.

## Prerequisites

- Access to the project source code
- Familiarity with the agent system architecture

## Examine the existing agent structure

Review the release prep components to understand the current implementation:

- `ReleaseAgent` — Base agent with tiered escalation (CHEAP → CAPABLE → PREMIUM)
- `TestCoverageAgent` — Runs pytest with coverage analysis
- `DocumentationAgent` — Validates docstrings, README, and changelog
- `CodeQualityAgent` — Executes ruff linting and complexity checks
- `ReleasePrepTeam` — Orchestrates parallel agent execution

## Choose your modification approach

Determine whether to extend or modify the existing components:

1. **Extend with a new agent** if you need additional check types (security scanning, performance benchmarks)
2. **Modify existing agents** if you need to change thresholds, add new quality gates, or alter escalation logic
3. **Customize the team orchestration** if you need different parallel execution patterns

## Implement your changes

### Add a new specialized agent

Create a subclass of `ReleaseAgent` in the appropriate module:

```python
class SecurityAgent(ReleaseAgent):
    def __init__(self, redis_client=None, state_store=None):
        super().__init__("security-scanner", "security", redis_client, state_store)
```

### Modify quality gates

Update the `QualityGate` thresholds in `ReleasePrepTeam`:

```python
quality_gates = {
    "test_coverage": 85.0,  # Raise from default
    "complexity_score": 10.0,  # Lower threshold
}
```

### Customize escalation behavior

Override the `process` method in `ReleaseAgent` to change when tier escalation occurs.

## Validate your implementation

Run the release prep test suite to verify your changes:

```bash
pytest -k "release-prep" -v
```

Check that your modifications produce valid `ReleaseReadinessReport` outputs and maintain the go/no-go decision logic.

## Success criteria

Your release prep modifications work correctly when:
- All existing tests pass
- New agents integrate with `ReleasePrepTeam` orchestration
- The assessment report includes your custom quality gates
- Escalation behavior follows your specified tier progression
