---
type: quickstart
feature: orchestration
depth: quickstart
generated_at: 2026-04-14T15:18:25.715726+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Quickstart: orchestration

Orchestrate AI agents using built-in execution strategies.

```python
from attune.orchestration import get_strategy

# Create a sequential strategy and execute agents
strategy = get_strategy("sequential")
result = strategy.execute(agents, context={"task": "Analyze code quality"})
print(result.outputs)
```

## Run your first agent composition

1. **Create agents and a strategy**:
   ```python
   from attune.orchestration import get_strategy
   from attune.templates import get_template

   # Get pre-built agent templates
   analyzer = get_template("code_analyzer")
   reviewer = get_template("code_reviewer")
   agents = [analyzer, reviewer]

   # Choose an execution strategy
   strategy = get_strategy("sequential")
   ```

2. **Execute the composition**:
   ```python
   context = {"task": "Review Python file", "file_path": "example.py"}
   result = strategy.execute(agents, context)
   ```

3. **Check the results**:
   ```python
   print(f"Success: {result.success}")
   for i, output in enumerate(result.outputs):
       print(f"Agent {i+1}: {output.content}")
   ```

**Expected output:**
```
Success: True
Agent 1: Code analysis complete. Found 3 style issues...
Agent 2: Review complete. Code quality score: 8.5/10...
```

## Try conditional execution

Replace the sequential strategy with conditional logic:

```python
from attune.orchestration import ConditionalStrategy, Condition, Branch

condition = Condition(type="context_key", key="complexity", value="high")
then_branch = Branch(strategy="parallel", agents=[analyzer, reviewer])
else_branch = Branch(strategy="sequential", agents=[analyzer])

strategy = ConditionalStrategy(condition, then_branch, else_branch)
result = strategy.execute(agents, context={"complexity": "high"})
```

**Next:** Register a custom strategy with `register_strategy()` to define your own agent composition patterns.
