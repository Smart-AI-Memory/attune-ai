---
name: memory
source: content/features/memory.md
tags:
- memory
- storage
type: task
---

# Two-tier memory subsystem — short-term working storage, long-term pattern lookup, and security

## Tasks

### Stash and retrieve short-term working memory

**Goal:** keep transient working state that expires on its own.

**Steps:**

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="me")
memory.stash("draft", {"step": 3}, ttl_seconds=600)  # expires in 10 min
print(memory.retrieve("draft"))                       # {"step": 3}
memory.close()
```

**Verify:** `stash` returns `True` on success; `retrieve` returns the
value or `None` if missing/expired. `ttl_seconds` is optional — omit it
to use the config default.

### Persist, search, and recall long-term patterns

**Goal:** store a durable, classified pattern and find it later by
content.

**Steps:**

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="me")
result = memory.persist_pattern(
    content="Validate file paths with _validate_file_path before writing",
    pattern_type="security",
)
hits = memory.search_patterns(query="file path validation", limit=5)
for hit in hits:
    print(hit["pattern_id"])
memory.close()
```

**Verify:** `persist_pattern` returns a dict with a `pattern_id` (or
`None` if storage is unavailable). `search_patterns` returns a list of
dicts ranked by relevance; narrow it with `pattern_type=` or
`classification=`. Classification is automatic unless you pass
`classification=`.

### Stage a pattern, then promote it

**Goal:** hold a candidate pattern for review before committing it to
durable storage.

**Steps:**

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="me")
staged_id = memory.stage_pattern(
    {"content": "Candidate: cache AST parses by file hash"},
    pattern_type="optimization",
)
# ... review memory.get_staged_patterns() ...
if staged_id:
    memory.promote_pattern(staged_id)
memory.close()
```

**Verify:** `stage_pattern` returns a staged id (or `None`);
`get_staged_patterns()` lists what's pending; `promote_pattern`
graduates it to durable storage (running classification/scrubbing) and
returns the stored pattern dict.

### Record an SBAR handoff

**Goal:** leave a structured handoff for the next session or agent.

**Steps:**

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="me")
memory.set_handoff(
    situation="Mid-refactor of the release agents",
    background="Split into focused submodules",
    assessment="Tests green; docs not yet updated",
    recommendation="Update docs/architecture/release.md next",
)
print(memory.generate_compact_state())
memory.close()
```

**Verify:** `set_handoff` takes the four SBAR fields plus arbitrary
`**extra_context`. `generate_compact_state()` returns a string snapshot;
`export_to_claude_md(path=None)` writes the state to a `CLAUDE.md`-style
file and returns the `Path`.
