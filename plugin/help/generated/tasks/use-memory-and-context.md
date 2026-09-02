---
type: task
name: use-memory-and-context
tags: [skill, task]
source: plugin/skills/memory-and-context/SKILL.md
---

# Task: Use the memory-and-context skill

Store, retrieve, search, and manage persistent memory across sessions. Triggers on: store memory, save this, retrieve, forget, manage memory, context, pattern.

Invoke with: `/memory-and-context <operation: store|retrieve|search|forget>`

## Steps

1. **Define operation**
   "What do you need? Store, retrieve, search, or forget?"

2. **Define key/query**
   "What key or search term?"

3. **Define classification**
   (store only): "PUBLIC, INTERNAL, or SENSITIVE?"

4. **Review memory-and-context execution guidance**
   ### Shared command workspace (preferred)

   Open adapter `memory-and-context` with the selected operation and scoped
   arguments. Present its widget or returned Markdown and collect its bound
   action before calling the existing memory tool. Store and forget are external
   writes and require explicit confirmation; retrieve and search remain
   read-only. Publish the exact tool response as `operation_result`.

   After a successful store or forget, follow the workspace's returned
   `memory_retrieve` verification request and publish it as
   `verification_result`. Store succeeds only when the same value and
   classification are retrieved; forget succeeds only when the post-delete read
   misses. Never render stored values—especially SENSITIVE values—in the
   workspace. A failed backend call must say “did not complete.” Preserve these
   decisions and verification receipts in compact text when the shared tools are
   unavailable.

   Based on the user's answer, call the appropriate MCP
   tool:

   - Store: `memory_store(key, value, classification)`
   - Retrieve: `memory_retrieve(key)`
   - Search: `memory_search(query, pattern_type)`
   - Forget: `memory_forget(key, scope)`

   attune-ai's memory system sits ABOVE Anthropic's native
   memory features. It provides security-classified storage,
   cross-agent pattern sharing, and a structured pattern
   lifecycle that native memory
   does not offer. Use the decision table below to determine
   which system to use for a given task.


## Related Topics
- **Reference**: Skill: memory-and-context — full reference
