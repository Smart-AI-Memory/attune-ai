---
type: quickstart
name: memory-quickstart
feature: memory
depth: quickstart
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 7d6a88f7e825fe56e3b06e3bce6dd904fe6a75cd1c13a3a134e4b44138df245e
status: generated
---

# Quickstart: Attune Memory

Store and retrieve persistent memory across agent sessions in under five minutes.

```python
from attune.memory import is_redis_available, get_redis_memory

if is_redis_available():
    mem = get_redis_memory()
    mem.stash("greeting", "hello world")
    print(mem.retrieve("greeting"))
```

**Expected output:**
```
hello world
```

## Prerequisites

- Attune installed locally (`pip install attune`)
- Redis running, or `use_mock=True` passed to `get_redis_memory()` for local testing

## Step 1: Check your backend

Before writing anything, confirm the memory subsystem is reachable:

```python
from attune.memory import is_redis_available, check_redis_connection

print(is_redis_available())       # True if Redis is importable
print(check_redis_connection())   # Returns a status dict
```

If `is_redis_available()` returns `False`, pass `use_mock=True` to `get_redis_memory()` to use the in-memory mock backend instead.

## Step 2: Stash and retrieve a value

```python
from attune.memory import get_redis_memory

mem = get_redis_memory()          # reads REDIS_URL from environment
mem.stash("user_pref", "dark_mode", ttl=3600)
value = mem.retrieve("user_pref")
print(value)                      # dark_mode
```

`stash` accepts an optional `ttl` (seconds) and an optional `agent_id` to scope the key to a specific agent.

## Step 3: Set up project-level memory

To give Claude Code a project-level `CLAUDE.md` memory file, run:

```python
from attune.memory.claude_memory import create_default_project_memory

create_default_project_memory(".", framework="empathy")
# Creates .claude/CLAUDE.md in the current directory
```

Then load it back with `ClaudeMemoryLoader`:

```python
from attune.memory import ClaudeMemoryLoader, ClaudeMemoryConfig

config = ClaudeMemoryConfig(enabled=True, load_project=True)
loader = ClaudeMemoryLoader(config)
context = loader.load_all_memory(project_root=".")
print(context[:200])
```

**Expected output:** The contents of `.claude/CLAUDE.md`, ready to inject into a Claude Code session.

## Step 4: Verify connectivity and stats

```python
from attune.memory import MemoryControlPanel

panel = MemoryControlPanel()
print(panel.health_check())
print(panel.get_statistics())
```

A healthy system returns a dict with no error keys from `health_check()`.

**Next:** Explore semantic search and long-term pattern storage with `SearchableMemoryBackend.search()` and `SearchableMemoryBackend.remember()`. Run `/memory-and-context search` in Claude Code to try it interactively.
