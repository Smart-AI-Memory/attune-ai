---
type: task
name: use-rag-code-gen
tags: [skill, task]
source: plugin/skills/rag-code-gen/SKILL.md
---

# Task: Use the rag-code-gen skill

RAG-grounded code generation with source citations. Triggers on: grounded code, ground this, cite sources, show me with sources, how do I with attune, reference attune docs, grounded against attune docs.

Invoke with: `/rag-code-gen <what you want generated + any specifics>`

## Steps

1. **Define what are you trying to produce?**
   Code, config, explanation, or a mix?

2. **Define any specific attune surface?**
   e.g. "the security-audit workflow", "MCP tool pattern", "BaseWorkflow subclass". Helps retrieval hit the right concept file.

3. **Define depth?**
   Default is `standard`. `quick` saves time and budget for simple asks; `deep` is for complex multi-file or architectural questions.


## Related Topics
- **Reference**: Skill: rag-code-gen — full reference
