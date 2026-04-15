---
type: quickstart
feature: memory
depth: quickstart
generated_at: 2026-04-14T15:06:48.217538+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Quickstart: memory

Store and retrieve data across AI agent conversations using Redis or file-based backends.

```python
from attune.memory import get_redis_memory

# Create a memory backend
memory = get_redis_memory()

# Store a value
memory.stash("user_preference", "dark_mode", ttl=3600)

# Retrieve it later
preference = memory.retrieve("user_preference")
print(preference)  # "dark_mode"
```

## Prerequisites

- Python 3.8+
- Redis server (optional - falls back to mock backend)

## Set up memory storage

1. **Check Redis availability** and create a memory backend:

   ```python
   from attune.memory import is_redis_available, get_redis_memory

   if is_redis_available():
       memory = get_redis_memory()
       print("✓ Redis backend ready")
   else:
       print("⚠ Using mock backend (data won't persist)")
   ```

2. **Store and retrieve data** with optional time-to-live:

   ```python
   # Store with 1-hour expiration
   success = memory.stash("session_data", {"user": "alice", "theme": "dark"}, ttl=3600)

   # Retrieve the data
   data = memory.retrieve("session_data")
   print(f"Retrieved: {data}")
   ```

3. **Check connection status** to verify everything works:

   ```python
   if memory.is_connected():
       stats = memory.get_stats()
       print(f"Memory stats: {stats}")
   ```

Expected output:
```
✓ Redis backend ready
Retrieved: {'user': 'alice', 'theme': 'dark'}
Memory stats: {'keys': 1, 'memory_usage': '1.2MB', 'connected_clients': 2}
```

**Next:** Set up [Claude memory integration](claude_memory.md) to load project context automatically.
