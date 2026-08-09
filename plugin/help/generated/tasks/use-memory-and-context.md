---
type: task
name: use-memory-and-context
tags: [skill, task]
source: plugin/skills/memory-and-context/SKILL.md
---

# Task: Use the memory-and-context skill

Store, retrieve, search, and manage persistent memory across sessions. Triggers on: store memory, save this, retrieve, forget, manage memory, context, pattern.

Invoke with: `/memory-and-context <operation: store|retrieve|search|forget|empathy>`

## Steps

1. **Define operation**
   "What do you need? Store, retrieve, search, forget, or adjust empathy level?"

2. **Define key/query**
   "What key or search term?"

3. **Define classification**
   (store only): "PUBLIC, INTERNAL, or SENSITIVE?"

4. **Execute the memory-and-context workflow**
   Based on the user's answer, call the appropriate MCP
tool: - Store: `memory_store(key, value, classification)`
- Retrieve: `memory_retrieve(key)`
- Search: `memory_search(query, pattern_type)`
- Forget: `memory_forget(key, scope)`
- Get level: `attune_get_level()`
- Set level: `attune_set_level(level)` attune-ai's memory system sits ABOVE Anthropic's native
memory features. It provides security-classified storage,
cross-agent pattern sharing, empathy-level modulation,
and a structured pattern lifecycle that native memory
does not offer. Use the decision table below to determine
which system to use for a given task.


## Related Topics
- **Reference**: Skill: memory-and-context — full reference
