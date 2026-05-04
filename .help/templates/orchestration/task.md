---
type: task
feature: orchestration
depth: task
generated_at: 2026-05-04T02:35:58.086720+00:00
source_hash: 15dce809a43de06ae9f042882afecc50f3b625050abdca81b878a832140002f0
status: generated
---

# Work with orchestration

Use orchestration when you need to coordinate multi-agent teams, compose dynamic workflows, or manage distributed task execution.

## Prerequisites

- Access to the project source code
- Python development environment set up
- Understanding of multi-agent patterns and workflow composition

## Configure the coordination layer

1. **Set up an AgentCoordinator for your team.**
   Create a Redis-backed coordinator to manage task distribution:
   ```python
   from attune.orchestration import AgentCoordinator, AgentTask

   coordinator = AgentCoordinator(short_term_memory, team_id="my_team")
   coordinator.register_agent("agent_1", capabilities=["analysis", "testing"])
   ```

2. **Define tasks for agent execution.**
   Create AgentTask instances with clear descriptions and priorities:
   ```python
   task = AgentTask(
       task_id="analyze_code",
       task_type="analysis",
       description="Analyze Python code quality",
       priority=3,
       context={"file_path": "src/main.py"}
   )
   coordinator.add_task(task)
   ```

## Set up workflow strategies

1. **Choose an execution strategy.**
   Select from available strategies based on your coordination needs:
   ```python
   from attune.orchestration import get_strategy

   # For sequential processing
   strategy = get_strategy("sequential")

   # For parallel execution
   strategy = get_strategy("parallel")

   # For hierarchical delegation
   strategy = get_strategy("delegation_chain")
   ```

2. **Register custom workflows if needed.**
   Create reusable workflow definitions:
   ```python
   from attune.orchestration import register_workflow, WorkflowDefinition

   workflow = WorkflowDefinition(
       workflow_id="code_review",
       steps=[...],  # Define your workflow steps
   )
   register_workflow(workflow)
   ```

## Manage agent templates

1. **Retrieve agents by capability.**
   Find agents suited for specific tasks:
   ```python
   from attune.orchestration import get_templates_by_capability

   testing_agents = get_templates_by_capability("testing")
   security_agents = get_templates_by_capability("security")
   ```

2. **Register custom agent templates.**
   Add specialized agents to the registry:
   ```python
   from attune.orchestration import register_custom_template, AgentTemplate

   custom_agent = AgentTemplate(
       template_id="custom_analyzer",
       capabilities=["custom_analysis"],
       # ... other template properties
   )
   register_custom_template(custom_agent)
   ```

## Handle conflicts and priorities

1. **Configure conflict resolution.**
   Set up a ConflictResolver with team priorities:
   ```python
   from attune.orchestration import ConflictResolver, TeamPriorities

   priorities = TeamPriorities(
       security_weight=0.4,
       performance_weight=0.3,
       readability_weight=0.3
   )
   resolver = ConflictResolver(team_priorities=priorities)
   ```

2. **Resolve pattern conflicts.**
   When multiple agents propose conflicting solutions:
   ```python
   resolution = resolver.resolve_patterns(
       patterns=[pattern1, pattern2, pattern3],
       context={"file_type": "python", "complexity": "high"}
   )
   print(f"Winning pattern: {resolution.winning_pattern}")
   ```

## Test your orchestration

Run orchestration-specific tests to verify your setup:
```bash
pytest -k "orchestration" -v
```

## Verify success

Your orchestration setup works correctly when:
- Agents can claim and complete tasks through the coordinator
- Workflows execute using your chosen strategy
- Conflict resolution produces consistent, reasonable results
- All orchestration tests pass without errors
