---
type: task
feature: release-prep
depth: task
generated_at: 2026-04-14T14:49:37.889046+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Work with release prep

Use the release preparation workflow when you need to validate code quality, security, and documentation before deploying a new version.

## Prerequisites

- Access to the project source code
- Python environment with pytest and ruff installed
- Redis connection (optional, for state persistence)

## Configure quality gates

1. **Set quality thresholds in your workflow initialization:**
   ```python
   quality_gates = {
       "test_coverage": 80.0,
       "code_quality": 8.0,
       "documentation": 70.0
   }
   team = ReleasePrepTeam(quality_gates=quality_gates)
   ```

2. **Define custom quality gates by extending QualityGate:**
   ```python
   gate = QualityGate(
       name="security_score",
       threshold=95.0,
       critical=True
   )
   ```

## Run release assessment

1. **Execute the full assessment workflow:**
   ```python
   from attune.workflows.release_prep import ReleasePreparationWorkflow

   workflow = ReleasePreparationWorkflow()
   result = workflow.execute(codebase_path="/path/to/project")
   ```

2. **Use the team coordinator for parallel execution:**
   ```python
   from attune.agents.release.team import ReleasePrepTeam

   team = ReleasePrepTeam()
   report = team.assess_readiness(codebase_path=".")
   ```

3. **Review the assessment results:**
   ```python
   print(report.format_console_output())

   if not report.approved:
       print("Blockers:", report.blockers)
       print("Warnings:", report.warnings)
   ```

## Extend assessment capabilities

1. **Create a custom release agent by inheriting from ReleaseAgent:**
   ```python
   class CustomSecurityAgent(ReleaseAgent):
       def __init__(self, **kwargs):
           super().__init__(
               agent_id="security-custom",
               role="Custom security validation",
               **kwargs
           )

       def process(self, codebase_path: str = ".") -> ReleaseAgentResult:
           # Your custom security checks here
           return ReleaseAgentResult(
               agent_id=self.agent_id,
               agent_role=self.role,
               success=True,
               tier_used=Tier.CHEAP
           )
   ```

2. **Add the custom agent to your team configuration:**
   ```python
   team = ReleasePrepTeam()
   team.agents.append(CustomSecurityAgent())
   ```

## Verify success

Run `pytest -k "release-prep"` to confirm your changes work correctly. The assessment passes when all critical quality gates show `passed: True` and `report.approved` returns `True`.

## Key files

- `src/attune/workflows/release_prep.py` — Main workflow orchestration
- `src/attune/agents/release/team.py` — Agent coordination and parallel execution
- `src/attune/agents/release/base_agent.py` — Base agent with tier escalation
- `src/attune/agents/release/release_models.py` — Data models and quality gates
