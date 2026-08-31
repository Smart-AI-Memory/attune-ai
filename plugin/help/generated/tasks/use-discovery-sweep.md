---
type: task
name: use-discovery-sweep
tags: [skill, task]
source: plugin/skills/discovery-sweep/SKILL.md
---

# Task: Use the discovery-sweep skill

Run every audit at once and triage the findings into act-now / needs-a-look / dismissed buckets. Triggers on: run all audits, full sweep, audit everything, what should I fix, triage findings, discovery sweep, sweep the codebase.

Invoke with: `/discovery-sweep <path or directory to sweep>`

## Steps

1. **Define target path**
   "Which files or directory should I sweep?" Default to `src/` if not specified.

2. **Define speed vs. depth**
   "Fast pattern-only sweep, or include the LLM-backed sources?" (LLM sources cost budget; pattern-only is free and quick.)

3. **Define budget**
   only if including LLM sources — "Spend cap? Default is $10.00."

4. **Run the tool**
   Call the `discovery_sweep` MCP tool with the scoped path:

   ```
   discovery_sweep(path="<user-specified path>")
   ```

5. **Run tool (option 2)**
   Optional knobs:

   ```
   discovery_sweep(path="src/", no_llm=true)          # fast, free
   discovery_sweep(path="src/", budget_usd=5.0)       # cap LLM spend
   ```

6. **Run tool (option 3)**
   Or via CLI:

   ```bash
   uv run attune workflow run discovery-sweep --path <target>
   ```


## Related Topics
- **Reference**: Skill: discovery-sweep — full reference
