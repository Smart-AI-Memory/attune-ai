---
type: reference
subtype: procedural
name: skill-personal-memory
category: skill
tags: [skill, plugin]
source: plugin/skills/personal-memory/SKILL.md
---

# Reference: Skill: personal-memory

Capture and recall curated cross-session personal memory — decisions, preferences, findings by topic. Triggers on: remember this for me, capture this decision, save to personal memory, my saved topics, forget topic, personal memory.

**Usage:** `/personal-memory <operation: capture|recall|topics|forget>`

## How this differs from the other memory skills

attune has three memory surfaces; pick the right one:

| You want to… | Use |
|--------------|-----|
| Deliberately save a decision/preference/finding to recall later, by topic | **this skill** (`personal_memory_*`) |
| Store a classified or cross-agent *pattern* in project memory | `memory-and-context` (`memory_*`) |
| Pull findings auto-stashed from past sessions + the lessons corpus | `recall` (`session_stash`) |

This skill is the curated, intentional store: content is polished and
filed under a `topic` (and optional `kind`), not auto-captured.

## Scoping

Before running, ask which operation the user needs:

1. **Operation**: "Capture something, recall by query, list your
   topics, or forget a topic?"
2. For **capture**: "What topic should it live under, and is this
   global or project-local?"
3. For **recall**: "What should I search for?"

## Execution

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

### personal_memory_recall

Search personal memory with a natural-language query.

**Parameters:**

- **query** (required): What to search for.
- **k** (optional, integer): Max results to return.
- **kind_filter** (optional): Restrict to a single `kind`.

```python
personal_memory_recall(query="how do I tag a release", k=5)
```

### personal_memory_topics

List every topic currently stored. No parameters.

```python
personal_memory_topics()
```

### personal_memory_forget

Delete a topic, or one `kind` within a topic.

**Parameters:**

- **topic** (required): The topic to remove.
- **kind** (optional): Remove only this kind; omit to remove the
  whole topic.

```python
personal_memory_forget(topic="release-process", kind="decision")
```

## Output

- **capture**: confirm the topic (and kind) it was filed under.
- **recall**: present hits newest/most-relevant first, annotated with
  their topic and kind.
- **topics**: render the topic list, grouped if kinds are present.
- **forget**: confirm exactly what was removed.

## Anti-Patterns

- DO NOT use this for auto-captured session findings — that is the
  `recall` skill's job.
- DO NOT use this for classified or cross-agent patterns — use
  `memory-and-context` (`memory_store` with a classification).
- DO NOT capture secrets or PII — personal memory is not an encrypted
  store; use `memory_store(classification="SENSITIVE")` for that.

## Related Topics
- **Reference**: Tool: Memory Store (`memory_store`)
