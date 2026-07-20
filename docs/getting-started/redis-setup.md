---
description: Configure Redis for Attune AI. Docker setup, persistence, monitoring. Production and development configurations included.
---

# Redis Setup Guide

Redis provides **short-term memory** for the Attune AI, enabling:
- Multi-agent coordination and state sharing
- Session persistence across requests
- Pattern staging before long-term storage
- Real-time collaboration between wizards

## Quick Start

### Option 1: Homebrew (macOS)

```bash
# Install
brew install redis

# Start as background service
brew services start redis

# Verify
redis-cli ping
# Should return: PONG
```

### Option 2: Docker

```bash
# Start Redis container
docker run -d -p 6379:6379 --name attune-redis redis:alpine

# Verify
docker exec attune-redis redis-cli ping
# Should return: PONG
```

### Option 3: Managed Redis (Production)

Managed platforms (Upstash/Vercel, Heroku, Railway, ...) provision Redis
from their dashboard and set `REDIS_URL` automatically for linked
services — Attune picks it up with no extra configuration.

## Configuration

### Environment Variable

Add to your `.env` file:

```bash
# Local development
REDIS_URL=redis://localhost:6379

# Managed Redis (auto-set when the platform links a Redis service)
# REDIS_URL=redis://default:password@your-managed-host:6379
```

### Verify Connection

```python
from attune import get_redis_memory

memory = get_redis_memory()
print(memory.is_connected())
# True

print(memory.get_stats())
# {'operations_total': 0, 'success_rate': 100.0, ...}
```

Or from command line:

```bash
python -c "from attune import get_redis_memory; print(get_redis_memory().is_connected())"
```

## Usage in Code

### Basic Usage

```python
from attune import get_redis_memory

# Auto-detects REDIS_URL, falls back to localhost,
# then mock mode
memory = get_redis_memory()

# Store data (expires in 1 hour by default)
memory.stash("my_key", {"data": "value"}, ttl=3600)

# Retrieve data
data = memory.retrieve("my_key")
```

### Storing Workflow Data

```python
from attune import get_redis_memory

memory = get_redis_memory()

# Store working data
memory.stash("analysis_results", {"files": 10, "issues": 3})

# Retrieve later
results = memory.retrieve("analysis_results")
```

### File-Based Fallback

When Redis is not available, the framework automatically
uses file-based session memory:

```python
from attune.memory.file_session import FileSessionMemory

# Works identically — same stash/retrieve interface
memory = FileSessionMemory(user_id="developer")
memory.stash("results", {"issues": 3})
data = memory.retrieve("results")
memory.close()
```

## Graceful Degradation

The framework handles Redis unavailability gracefully:

- **Redis available**: Full short-term memory functionality
- **Redis unavailable**: Falls back to file-based session memory (persistent, not shared)
- **Mock mode**: Set `REDIS_URL=""` to force in-memory mode for testing

## Troubleshooting

### Connection Refused

```
Error: Connection refused to localhost:6379
```

**Solution**: Redis isn't running. Start it:
```bash
brew services start redis
# or
docker start attune-redis
```

### Railway Internal URL Errors

```
Error connecting to redis-xxx.railway.internal:6379
```

**Solution**: Railway internal URLs only work within Railway's network. For local development:
1. Use `REDIS_URL=redis://localhost:6379` in your `.env`
2. Run Redis locally (Homebrew or Docker)

### Check What URL Is Being Used

```bash
echo $REDIS_URL
```

If it shows a Railway URL locally, override it:
```bash
export REDIS_URL=redis://localhost:6379
```

## Production Considerations

### Security

- Railway Redis is only accessible within the private network
- Use `REDIS_PRIVATE_URL` for internal communication
- Never expose Redis ports publicly

### Memory Management

```python
# Set appropriate TTLs to prevent memory bloat
memory.stash("temp_data", data, ttl=300)      # 5 min
memory.stash("session_data", data, ttl=3600)   # 1 hour
memory.stash("staging", data, ttl=86400)       # 24 hours
```

### Monitoring

```python
from attune import get_redis_memory

memory = get_redis_memory()
stats = memory.get_stats()
print(f"Operations: {stats.get('operations_total')}")
print(f"Success rate: {stats.get('success_rate')}%")
```

## Next Steps

- Multi-Agent Philosophy - Team coordination with Redis
- [Configuration Reference](../reference/configuration.md) - All configuration options
