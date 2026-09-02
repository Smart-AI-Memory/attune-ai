---
type: task
name: use-personal-memory
tags: [skill, task]
source: plugin/skills/personal-memory/SKILL.md
---

# Task: Use the personal-memory skill

Capture and recall curated cross-session personal memory — decisions, preferences, findings by topic. Triggers on: remember this for me, capture this decision, save to personal memory, my saved topics, forget topic, personal memory.

Invoke with: `/personal-memory <operation: capture|recall|topics|forget>`

## Steps

1. **Define operation**
   "Capture something, recall by query, list your topics, or forget a topic?"

2. **Run the tool**
   Call the matching MCP tool:

   ### personal_memory_capture

   Save a decision, pattern, finding, or reference to personal memory.

   **Parameters:**

   - **topic** (required): The topic to file this under.
   - **content** (required): The text to store (it is polished before
     storage).
   - **kind** (optional): A sub-category within the topic (e.g.
     `decision`, `preference`, `reference`).
   - **project_local** (optional, boolean): Store only for the current
     project instead of globally. Default is global.

   ```python
   personal_memory_capture(
       topic="release-process",
       content="Always verify the merge SHA contains the version bump before tagging.",
       kind="decision",
   )
   ```

3. **Run tool (option 2)**
   ### personal_memory_recall

   Search personal memory with a natural-language query.

   **Parameters:**

   - **query** (required): What to search for.
   - **k** (optional, integer): Max results to return.
   - **kind_filter** (optional): Restrict to a single `kind`.

   ```python
   personal_memory_recall(query="how do I tag a release", k=5)
   ```

4. **Run tool (option 3)**
   ### personal_memory_topics

   List every topic currently stored. No parameters.

   ```python
   personal_memory_topics()
   ```

5. **Run tool (option 4)**
   ### personal_memory_forget

   Delete a topic, or one `kind` within a topic.

   **Parameters:**

   - **topic** (required): The topic to remove.
   - **kind** (optional): Remove only this kind; omit to remove the
     whole topic.

   ```python
   personal_memory_forget(topic="release-process", kind="decision")
   ```


## Related Topics
- **Reference**: Skill: personal-memory — full reference
