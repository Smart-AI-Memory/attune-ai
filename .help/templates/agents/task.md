---
type: task
feature: agents
depth: task
generated_at: 2026-04-14T15:07:52.649507+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Work with agents

Use agents when you need to assess release readiness, run automated code quality checks, or integrate AI agents with external frameworks like LangChain or AutoGen.

## Prerequisites

- Access to the project source code
- Python environment with pytest and ruff installed
- Redis instance (optional, for agent state persistence)

## Create a release preparation workflow

1. **Initialize the ReleasePrepTeam with quality gates:**
   ```python
   from attune.agents import ReleasePrepTeam

   team = ReleasePrepTeam(
       quality_gates={
           'test_coverage': 0.8,
           'code_quality': 0.9,
           'documentation': 0.7
       }
   )
   ```

2. **Run the release readiness assessment:**
   ```python
   report = team.assess_readiness(codebase_path='./my-project')
   ```

3. **Check the results:**
   ```python
   if report.approved:
       print("Release approved!")
   else:
       print(f"Blockers: {report.blockers}")
       print(report.format_console_output())
   ```

## Set up individual release agents

1. **Create specialized agents for specific checks:**
   ```python
   from attune.agents import TestCoverageAgent, DocumentationAgent, CodeQualityAgent

   # Test coverage analysis
   test_agent = TestCoverageAgent()

   # Documentation completeness check
   doc_agent = DocumentationAgent()

   # Code quality and complexity analysis
   quality_agent = CodeQualityAgent()
   ```

2. **Configure agent state persistence (optional):**
   ```python
   import redis
   from attune.agents import AgentStateStore

   redis_client = redis.Redis.from_url('redis://localhost:6379')
   state_store = AgentStateStore(redis_client)

   agent = TestCoverageAgent(
       redis_client=redis_client,
       state_store=state_store
   )
   ```

## Integrate with external AI frameworks

1. **Connect to LangChain:**
   ```python
   from attune.agent_factory import get_langchain_adapter

   adapter = get_langchain_adapter()
   # Use adapter to integrate LangChain agents
   ```

2. **Wrap existing wizards as agents:**
   ```python
   from attune.agent_factory import wrap_wizard

   my_wizard = SomeWizardClass()
   agent = wrap_wizard(my_wizard, name="custom-agent", model_tier="capable")
   ```

3. **Apply operation decorators for reliability:**
   ```python
   from attune.agent_factory import safe_agent_operation, retry_on_failure

   @retry_on_failure(max_attempts=3)
   @safe_agent_operation("code_analysis")
   def analyze_code(path):
       # Your agent operation here
       pass
   ```

## Verify success

The release readiness assessment succeeds when:
- `report.approved` returns `True`
- All quality gates in `report.quality_gates` show `passed: True`
- The `report.blockers` list is empty
- Coverage reports generate without errors (for TestCoverageAgent)
- Docstring analysis completes (for DocumentationAgent)

Run `pytest -k "agents"` to verify agent functionality through the test suite.
