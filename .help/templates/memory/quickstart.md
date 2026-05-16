---
type: quickstart
name: memory-quickstart
feature: memory
depth: quickstart
generated_at: 2026-05-16T06:14:13.801704+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Quickstart: Attune Memory

Store and retrieve persistent memory in your project using Redis or file-backed sessions.

```python
from attune.memory import is_redis_available, get_redis_memory

if is_redis_available():
    mem = get_redis_memory()
    mem.stash("my_key", {"result": 42})
    print(mem.retrieve("my_key"))  # → {'result': 42}
```

**Result:** `{'result': 42}` printed to your console confirms the memory backend is connected and writing correctly.

## Prerequisites

- Project cloned and installed locally (`src/attune/memory/` present)
- Redis running locally, or `USE_MOCK=true` set in your environment to use a mock backend

## Step 1: Check your backend

```python
from attune.memory import is_redis_available, check_redis_connection

print(check_redis_connection())
```

You should see a dict with `"connected": true`. If Redis is unavailable, pass `use_mock=True` to `get_redis_memory()` to continue without it.

## Step 2: Stash and retrieve a value

```python
from attune.memory import get_redis_memory

mem = get_redis_memory()
mem.stash("session_note", "first run complete", ttl=3600)
value = mem.retrieve("session_note")
print(value)  # → 'first run complete'
```

`ttl=3600` expires the key after one hour. Omit it to keep the value indefinitely.

## Step 3: Set up project memory files

To load persistent `CLAUDE.md` memory files into your project:

```python
from attune.memory.claude_memory import ClaudeMemoryLoader, ClaudeMemoryConfig

config = ClaudeMemoryConfig(enabled=True, load_project=True)
loader = ClaudeMemoryLoader(config)
combined = loader.load_all_memory(project_root=".")
print(combined[:200])
```

**Result:** The combined content of all discovered `CLAUDE.md` files, printed to confirm they loaded correctly. Use `loader.get_loaded_files()` to see which paths were included.

**Next:** Explore the `MemoryControlPanel` to inspect backend statistics, manage stored patterns, and run health checks — see `attune help-docs ref-memory`.
