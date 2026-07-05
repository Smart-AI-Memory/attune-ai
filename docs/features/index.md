# Feature Availability

Attune AI has a modular architecture with **core features** (always available) and **optional features** (require additional dependencies).

---

## Core Features (Always Available)

These features work without any additional dependencies beyond the base install (`pip install attune-ai`):

### Memory - Core

| Feature | Description |
|---------|-------------|
| **File session storage** | Local file-based session memory in `.attune/` directory |
| **Long-term memory** | Persistent pattern storage using file-based MemDocsStorage |
| **Security features** | PII scrubbing, secrets detection, and audit logging |
| **Graph structures** | Pattern graph with nodes, edges, and relationships |
| **Encryption** | AES-256-GCM encryption for sensitive patterns |

### Telemetry - Core

| Feature | Description |
|---------|-------------|
| **Usage tracking** | Local JSON Lines usage logs in `~/.attune/telemetry/` |
| **Feedback loop** | Quality feedback collection for adaptive routing |
| **CLI commands** | All CLI features work without Redis |

### Workflows

| Feature | Description |
|---------|-------------|
| **All 17 workflows** | Work with core memory only (file-based fallback) |
| **Multi-tier routing** | Cost optimization across CHEAP/CAPABLE/PREMIUM tiers |
| **XML-enhanced prompts** | Structured prompt templates and parsing |

---

## Optional Features (Require a Redis Server)

The Redis client libraries ship with the standard install (core
dependencies as of 9.7.0 — the `[redis]` extra remains as an empty
backward-compat alias). These features activate when a Redis Stack
server is reachable:

```bash
# macOS
brew tap redis-stack/redis-stack && brew install redis-stack-server
# Linux
sudo apt install redis-stack-server
```

### Memory - Redis-Enhanced

| Feature | Description |
|---------|-------------|
| **Short-term memory** | Redis-based working memory with TTL expiration (5 min - 7 days) |
| **Cross-session coordination** | Multi-agent session management across Claude Code sessions |
| **Pattern staging** | Redis-based pattern validation workflow before promotion |
| **Agent heartbeats** | TTL-based agent liveness monitoring |

### Telemetry - Redis-Enhanced

| Feature | Description |
|---------|-------------|
| **Event streaming** | Real-time event streams via Redis Streams |
| **Agent heartbeats** | TTL-based agent liveness monitoring with auto-expiration |
| **Agent coordination** | Inter-agent signaling via Redis pub/sub |
| **Approval gates** | Workflow approval gates with Redis-backed state |

---

## Checking Feature Availability

### CLI

Show all available features with status:

```bash
attune features
```

Output example:

```
======================================================================
ATTUNE AI - FEATURE AVAILABILITY
======================================================================

📦 MEMORY FEATURES

Feature                        Status          Details
----------------------------------------------------------------------
✅ Long-term memory (file-based) Available       Core feature (always available)
✅ File session storage         Available       Core feature (always available)
⚠️ Short-term memory (Redis-based) Missing Dependency Redis package not installed
                                Install: pip install 'attune-ai[redis]'
...

💡 To enable Redis-enhanced features:
   1. Install Redis package:
      pip install 'attune-ai[redis]'

   2. Install and start Redis server:
      • macOS: brew install redis && brew services start redis
      • Linux: sudo apt install redis-server
      • Docker: docker run -d -p 6379:6379 redis:alpine
```

### Python API

Check feature availability programmatically:

```python
from attune.memory.features import MemoryFeatures

# Check if Redis is available
if MemoryFeatures.is_redis_available():
    from attune.memory import RedisShortTermMemory
    memory = RedisShortTermMemory()
else:
    from attune.memory import FileSessionMemory
    memory = FileSessionMemory()

# Get detailed feature status
info = MemoryFeatures.get_feature_status("short_term")
print(f"{info.name}: {info.status.value}")
print(info.message)
if info.install_command:
    print(f"Install: {info.install_command}")

# List all features
features = MemoryFeatures.list_all_features()
for name, info in features.items():
    status_symbol = "✅" if info.status.value == "available" else "⚠️"
    print(f"{status_symbol} {name}: {info.status.value}")
```

**Telemetry features:**

```python
from attune.telemetry.features import TelemetryFeatures

# Check specific feature
info = TelemetryFeatures.get_feature_status("event_streaming")
if info.status.value == "available":
    from attune.telemetry import EventStreamer
    streamer = EventStreamer()
    streamer.publish_event("agent_heartbeat", {"status": "running"})
else:
    print(f"Event streaming unavailable: {info.message}")

# Require Redis or raise helpful error
try:
    TelemetryFeatures.require_redis("Event streaming")
    # Use event streaming features
except ImportError as e:
    print(e)  # Shows install instructions
```

---

## Graceful Degradation

When Redis features are not available, Attune AI automatically falls back to core features:

### Automatic Fallbacks

| Component | Without Redis | With Redis |
|-----------|---------------|------------|
| **UnifiedMemory** | Uses FileSessionMemory | Uses RedisShortTermMemory |
| **Event streaming** | Logs events locally (no real-time) | Redis Streams with pub/sub |
| **Agent coordination** | File-based handoff | Redis TTL-based coordination |

### Example: UnifiedMemory Fallback

```python
from attune.memory import UnifiedMemory

# This works whether Redis is available or not
memory = UnifiedMemory(user_id="agent@company.com")

# Short-term operations (uses FileSessionMemory if Redis unavailable)
memory.stash("working_data", {"key": "value"})
data = memory.retrieve("working_data")

# Long-term operations (always available)
result = memory.persist_pattern(content="Algorithm X", pattern_type="algorithm")
pattern = memory.recall_pattern(result["pattern_id"])
```

**No configuration needed** - it just works! The system detects Redis availability at runtime and uses the best available backend.

---

## Installation Options

### Minimal Install (Core Features Only)

```bash
pip install attune-ai
```

**Includes:**
- All 17 workflows
- File-based memory (session + long-term)
- Local usage tracking
- CLI commands
- Multi-tier cost optimization

**Use when:**
- No Redis infrastructure
- Single-session usage
- CI/CD pipelines
- Simple automation scripts

### Redis Install (Multi-Session Coordination)

```bash
pip install 'attune-ai[redis]'
```

**Additional features:**
- Redis-based short-term memory
- Real-time event streaming
- Cross-session agent coordination
- Agent heartbeat monitoring

**Use when:**
- Multi-session agent coordination needed
- Real-time monitoring required
- Large-scale deployments
- Team collaboration

---

## Installation Extras

Extras combine (e.g. `'attune-ai[developer,ops,redis]'`). Keep the
quotes — zsh and bash treat square brackets as glob characters.

| Extra | Features | Install Command |
|-------|----------|-----------------|
| `developer` | Claude API provider, LangChain/LangGraph agent teams, MemDocs | `pip install 'attune-ai[developer]'` |
| `ops` | Web ops dashboard (`attune ops`) | `pip install 'attune-ai[ops]'` |
| `redis` | Redis-based short-term memory, event streaming | `pip install 'attune-ai[redis]'` |
| `author` | Help authoring (`.help/` template generation) | `pip install 'attune-ai[author]'` |
| `llm` | Anthropic LLM provider only | `pip install 'attune-ai[llm]'` |

---

## Redis Setup Guide

### macOS (Homebrew)

```bash
# Install Redis
brew install redis

# Start Redis server
brew services start redis

# Verify it's running
redis-cli ping  # Should return: PONG
```

### Linux (Ubuntu/Debian)

```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Start Redis service
sudo systemctl start redis-server

# Enable auto-start on boot
sudo systemctl enable redis-server

# Verify it's running
redis-cli ping  # Should return: PONG
```

### Linux (RHEL/CentOS)

```bash
# Install Redis
sudo yum install redis

# Start Redis service
sudo systemctl start redis

# Enable auto-start
sudo systemctl enable redis

# Verify
redis-cli ping
```

### Docker (All Platforms)

```bash
# Run Redis container
docker run -d \
  --name attune-redis \
  -p 6379:6379 \
  redis:alpine

# Verify it's running
docker exec attune-redis redis-cli ping  # Should return: PONG

# Stop Redis
docker stop attune-redis

# Start Redis (after stopping)
docker start attune-redis
```

### Windows

**Option 1: WSL (Recommended)**

```bash
# Inside WSL
sudo apt install redis-server
sudo service redis-server start
redis-cli ping
```

**Option 2: Chocolatey**

```powershell
# Install Redis via Chocolatey
choco install redis-64

# Start Redis service
net start Redis

# Verify
redis-cli ping
```

**Option 3: Docker Desktop**

```powershell
docker run -d --name attune-redis -p 6379:6379 redis:alpine
```

---

## Troubleshooting

### "Redis package not installed"

**Problem:** Feature shows "Missing Dependency"

**Solution:**

```bash
pip install 'attune-ai[redis]'
```

### "Redis server not running"

**Problem:** Feature shows "Not Configured"

**Solution:**

```bash
# Check if Redis is running
redis-cli ping

# If not running, start it (platform-specific):
# macOS:
brew services start redis

# Linux:
sudo systemctl start redis

# Docker:
docker start attune-redis
```

### Import errors after installing Redis

**Problem:** `ImportError: No module named 'redis'`

**Solution:**

```bash
# Verify installation
pip list | grep redis

# If not installed, reinstall
pip install --force-reinstall 'attune-ai[redis]'
```

### Connection errors

**Problem:** `redis.exceptions.ConnectionError: Error connecting to localhost:6379`

**Solution:**

```bash
# Check Redis is listening on correct port
redis-cli -h localhost -p 6379 ping

# Check for firewalls blocking port 6379
# macOS/Linux:
sudo lsof -i :6379

# If Redis is on different host/port, configure:
export REDIS_HOST=your-redis-host
export REDIS_PORT=6380  # If non-default port
```

---

## Feature Comparison Matrix

| Feature | Core | Redis-Enhanced |
|---------|------|----------------|
| **Memory Persistence** | ✅ File-based | ✅ File-based + Redis |
| **TTL Expiration** | ❌ | ✅ 5 min - 7 days |
| **Cross-Session** | ❌ | ✅ Multi-agent coordination |
| **Real-time Events** | ❌ | ✅ Redis Streams |
| **Agent Heartbeats** | ❌ | ✅ TTL-based monitoring |
| **Pattern Staging** | ✅ File-based | ✅ Redis workflow |
| **PII Scrubbing** | ✅ | ✅ |
| **Encryption** | ✅ AES-256-GCM | ✅ AES-256-GCM |
| **Usage Tracking** | ✅ Local files | ✅ Local files |
| **Cost Optimization** | ✅ Multi-tier | ✅ Multi-tier |
| **All Workflows** | ✅ | ✅ |

---

## API Reference

### MemoryFeatures

```python
from attune.memory.features import MemoryFeatures, FeatureStatus

# Check availability
MemoryFeatures.is_redis_available() -> bool
MemoryFeatures.is_redis_running() -> bool

# Get feature status
MemoryFeatures.get_feature_status(feature: str) -> FeatureInfo

# Require Redis or raise error
MemoryFeatures.require_redis(feature_name: str) -> None

# List all features
MemoryFeatures.list_all_features() -> dict[str, FeatureInfo]
```

### TelemetryFeatures

```python
from attune.telemetry.features import TelemetryFeatures

# Check availability
TelemetryFeatures.is_redis_available() -> bool

# Get feature status
TelemetryFeatures.get_feature_status(feature: str) -> FeatureInfo

# Require Redis or raise error
TelemetryFeatures.require_redis(feature_name: str) -> None

# List all features
TelemetryFeatures.list_all_features() -> dict[str, FeatureInfo]
```

### FeatureInfo

```python
@dataclass
class FeatureInfo:
    name: str                     # Human-readable feature name
    status: FeatureStatus         # AVAILABLE, MISSING_DEPENDENCY, NOT_CONFIGURED
    message: str                  # Status description
    install_command: str | None   # Installation command (if needed)
```

---

## Migration Guide

### Upgrading from v2.6.3 to v2.6.4+

**No breaking changes!** Feature availability checks are additive.

If you previously relied on Redis without checking:

```python
# Before (v2.6.3) - would crash if Redis missing
from attune.memory import RedisShortTermMemory
memory = RedisShortTermMemory()  # ImportError if redis package missing

# After (v2.6.4+) - graceful with helpful error
from attune.memory import RedisShortTermMemory
try:
    memory = RedisShortTermMemory()
except ImportError as e:
    print(e)  # "Short-term memory requires Redis.\n
              #  Status: Redis package not installed\n
              #  Install: pip install 'attune-ai[redis]'"
```

**Recommended pattern:**

```python
from attune.memory.features import MemoryFeatures

if MemoryFeatures.is_redis_available():
    from attune.memory import RedisShortTermMemory
    memory = RedisShortTermMemory()
else:
    from attune.memory import FileSessionMemory
    memory = FileSessionMemory()
```

---

## See Also

- [Installation Guide](../getting-started/installation.md)
- [Configuration Guide](../reference/configuration.md)
- [Architecture Overview](../ARCHITECTURE.md)

---

For the current release, see [PyPI](https://pypi.org/project/attune-ai/)
or the README version badge.
