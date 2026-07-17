# attune-redis

Redis Agent Memory Server (AMS) plugin for
[Attune AI](https://github.com/Smart-AI-Memory/attune-ai).

Implements the `MemoryBackend` and `SearchableMemoryBackend`
protocols via the
[agent-memory-client](https://pypi.org/project/agent-memory-client/)
SDK, giving your agents persistent working memory, semantic
search over long-term memory, and pub/sub coordination.

## Installation

Nothing extra to install — this plugin is **bundled in the attune-ai
wheel**, and its dependencies (`redis`, `agent-memory-client`) are core
attune-ai dependencies:

```bash
pip install attune-ai
```

(There is no standalone `attune-redis` package on PyPI, and the former
`[redis]` extra was an empty alias, removed 2026-07-17. You only need a
running Redis / Agent Memory Server to connect to.)

## Quick start

```python
from attune_redis import AMSMemoryBackend, RedisPluginConfig

config = RedisPluginConfig(
    ams_base_url="http://localhost:8000",
    ams_namespace="my-app",
)

backend = AMSMemoryBackend(config=config)

# Working memory
backend.stash("user:prefs", {"theme": "dark"})
print(backend.retrieve("user:prefs"))

# Semantic search (long-term memory)
results = backend.search("authentication bugs", limit=5)

# Promote working memory to long-term
backend.promote(session_id="session-42")

backend.close()
```

## Configuration

All settings can be loaded from environment variables:

```bash
export AMS_BASE_URL=http://localhost:8000
export AMS_NAMESPACE=my-app
export REDIS_URL=redis://localhost:6379  # optional, enables pub/sub
```

```python
config = RedisPluginConfig.from_env()
```

| Variable | Default | Description |
|----------|---------|-------------|
| `AMS_BASE_URL` | `http://localhost:8000` | Agent Memory Server URL |
| `AMS_NAMESPACE` | `attune` | Namespace for memory ops |
| `REDIS_URL` | None | Redis URL for pub/sub signaling |

## Features

- **MemoryBackend protocol** -- `stash`, `retrieve`,
  `delete`, `keys`, `is_connected`, `get_stats`, `close`
- **SearchableMemoryBackend** -- `search` (semantic) and
  `promote` (working to long-term)
- **Pub/sub signaling** -- `RedisSignalBus` for
  inter-agent coordination via Redis channels
- **MCP tools** -- 5 tools for MCP-based agent
  integrations (store, retrieve, search, promote,
  health check)
- **Plugin auto-discovery** -- registers via
  `attune.plugins` entry point

## Requirements

- Python 3.10+
- [Redis Agent Memory Server](https://github.com/redis-developer/agent-memory-server)
  running (for memory ops)
- Redis server (optional, for pub/sub signaling)

## License

Apache 2.0 -- see
[LICENSE](https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE).
