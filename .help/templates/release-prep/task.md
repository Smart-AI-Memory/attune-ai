---
type: task
name: release-prep-task
feature: release-prep
depth: task
generated_at: 2026-06-04T23:45:26.692536+00:00
source_hash: 154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2
status: generated
---

# Work with Release Prep

Use `ReleasePrepTeam` when you need to run a full preflight assessment — test coverage, code quality, security, and documentation — before publishing a release.

## Prerequisites

- Access to the project source code
- The following modules available in your environment:
  - `release.release_prep_team` — `ReleasePrepTeam`, `ReleasePrepTeamWorkflow`
  - `release.release_models` — `ReleaseReadinessReport`, `QualityGate`, `ReleaseAgentResult`
  - `release.release_agents` — `CodeQualityAgent`, `DocumentationAgent`, `SecurityAuditorAgent`, `TestCoverageAgent`

## Run a readiness assessment

1. **Import `ReleasePrepTeam` and instantiate it.**

   ```python
   from release.release_prep_team import ReleasePrepTeam

   team = ReleasePrepTeam()
   ```

   To enforce custom thresholds, pass a `quality_gates` dict. Each key is a gate name and each value is the minimum passing threshold:

   ```python
   team = ReleasePrepTeam(quality_gates={"coverage": 0.90, "security": 1.0})
   ```

   To enable shared state across agents, pass a `redis_url`:

   ```python
   team = ReleasePrepTeam(redis_url="redis://localhost:6379")
   ```

2. **Call `assess_readiness` against your codebase path.**

   ```python
   report = team.assess_readiness(codebase_path=".")
   ```

   This runs `TestCoverageAgent`, `CodeQualityAgent`, `DocumentationAgent`, and `SecurityAuditorAgent` in parallel, then aggregates their results into a `ReleaseReadinessReport`.

3. **Print the formatted report to the console.**

   ```python
   print(report.format_console_output())
   ```

4. **Check the go/no-go verdict.**

   ```python
   if report.approved:
       print("GO — safe to tag and publish.")
   else:
       print("NO-GO — resolve the following blockers:")
       for blocker in report.blockers:
           print(f"  • {blocker}")
   ```

5. **Review warnings and per-agent results.**

   Warnings do not block release but indicate issues worth addressing:

   ```python
   for warning in report.warnings:
       print(f"  ⚠ {warning}")
   ```

   Inspect individual agent results to trace findings back to a specific check:

   ```python
   for result in report.agent_results:
       print(f"{result.agent_role}: score={result.score}, escalated={result.escalated}")
   ```

6. **Retrieve total cost across all agents.**

   ```python
   cost = team.get_total_cost()
   print(f"Assessment cost: ${cost:.4f}")
   ```

7. **Run the related tests to confirm nothing regressed.**

   ```
   pytest -k "release-prep"
   ```

## Extend the assessment with a custom quality gate

1. **Instantiate a `QualityGate` with your threshold.**

   ```python
   from release.release_models import QualityGate

   gate = QualityGate(
       name="docstring_coverage",
       threshold=0.80,
       critical=True,
   )
   ```

2. **Pass the gate to `ReleasePrepTeam` via `quality_gates`.**

   The `quality_gates` dict maps gate names to threshold floats:

   ```python
   team = ReleasePrepTeam(quality_gates={"docstring_coverage": 0.80})
   ```

3. **Verify the gate appears in the report after assessment.**

   ```python
   report = team.assess_readiness()
   for gate in report.quality_gates:
       print(f"{gate.name}: threshold={gate.threshold}, actual={gate.actual}, passed={gate.passed}")
   ```

## Add a custom release agent

1. **Subclass `ReleaseAgent` and implement `process`.**

   `process` must return a `ReleaseAgentResult`:

   ```python
   from release.base_agent import ReleaseAgent
   from release.release_models import ReleaseAgentResult

   class MyCustomAgent(ReleaseAgent):
       def process(self, codebase_path: str = ".") -> ReleaseAgentResult:
           # Your check logic here
           ...
   ```

2. **Instantiate the agent and call `process` directly to test it in isolation.**

   ```python
   agent = MyCustomAgent(agent_id="my-check", role="custom-checker")
   result = agent.process(codebase_path=".")
   print(result.score, result.findings)
   ```

3. **Run the test suite to confirm your agent behaves as expected.**

   ```
   pytest -k "release-prep"
   ```

## Verify success

The task succeeds when:

- `report.approved` is `True` and `report.blockers` is an empty list, or
- `report.approved` is `False` and `report.blockers` lists every issue you expected — confirming the gates caught real problems before you publish.

Call `report.to_dict()` to serialize the full result for logging or CI artifact storage.

## Key files

| File | Purpose |
|------|---------|
| `release/release_prep_team.py` | `ReleasePrepTeam` and `ReleasePrepTeamWorkflow` — orchestrates all agents |
| `release/release_models.py` | `ReleaseReadinessReport`, `QualityGate`, `ReleaseAgentResult`, `Tier` |
| `release/base_agent.py` | `ReleaseAgent` — base class with CHEAP → CAPABLE → PREMIUM escalation |
| `release/coverage_agent.py` | `TestCoverageAgent` — runs `pytest --cov` and parses the coverage report |
| `release/quality_agent.py` | `CodeQualityAgent` — runs `ruff`, checks type hints and complexity |
| `release/documentation_agent.py` | `DocumentationAgent` — checks docstring coverage, README currency, and CHANGELOG presence |
| `release/security_agent.py` | `SecurityAuditorAgent` — scans for vulnerabilities and secret leaks |
| `workflows/release_prep.py` | `ReleasePreparationWorkflow` — CLI-registry workflow wrapper |
