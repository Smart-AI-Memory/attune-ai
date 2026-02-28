# Redis Plugin Migration Guide

Migrating from legacy `attune.redis_*` modules to the
`attune-redis` plugin.

## Timeline

- **v3.5.0**: Legacy modules emit `DeprecationWarning`
- **v4.0.0**: Legacy modules will be removed

## Import Changes

### Memory Backend

```python
# Before (deprecated)
from attune.redis_memory import RedisShortTermMemory
memory = RedisShortTermMemory(use_mock=True)

# After
from attune_redis.memory import AMSMemoryBackend
from attune_redis.config import RedisPluginConfig

config = RedisPluginConfig.from_env()
backend = AMSMemoryBackend(config=config)
```

### Configuration

```python
# Before (deprecated)
from attune.redis_config import get_redis_config
config = get_redis_config()

# After
from attune_redis.config import RedisPluginConfig
config = RedisPluginConfig.from_env()
```

### Types

Types moved to `attune.memory.types` (no plugin
dependency needed):

```python
# Before (deprecated)
from attune.redis_memory_models import (
    AccessTier,
    AgentCredentials,
)

# After
from attune.memory.types import (
    AccessTier,
    AgentCredentials,
)
```

## API Differences

### stash/retrieve

```python
# Before: credentials required
creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
memory.stash("key", value, creds)
data = memory.retrieve("key", creds)

# After: simple key-value, optional session_id
backend.stash("key", value)
data = backend.retrieve("key")

# With session override
backend.stash("key", value, agent_id="session-1")
```

### Search (new)

```python
# Before: not available in RedisShortTermMemory

# After: semantic search via AMS long-term memory
results = backend.search("find user preferences")
```

### Promote (new)

```python
# Before: not available

# After: promote working memory to long-term
backend.promote(session_id="my-session")
```

## Environment Variables

| Before | After | Notes |
|--------|-------|-------|
| `REDIS_HOST` | `AMS_BASE_URL` | AMS server URL |
| `REDIS_PORT` | (part of URL) | Included in URL |
| `REDIS_PASSWORD` | (AMS auth) | AMS handles auth |
| `REDIS_DB` | `AMS_NAMESPACE` | Namespace isolation |
| `REDIS_URL` | `REDIS_URL` | Still used for pub/sub |

## Modules Being Removed in v4.0.0

| Module | Replacement |
|--------|-------------|
| `attune.redis_memory` | `attune_redis.memory` |
| `attune.redis_config` | `attune_redis.config` |
| `attune.redis_memory_storage` | `attune_redis.memory` |
| `attune.redis_memory_coordination` | `attune_redis.signals` |
| `attune.redis_memory_patterns` | `attune_redis.memory` |
| `attune.redis_memory_models` | `attune.memory.types` |
| `attune.memory.config` | `attune_redis.config` |
