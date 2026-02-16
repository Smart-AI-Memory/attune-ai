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

### Option 3: Railway (Production)

1. Go to your Railway project dashboard
2. Click **+ New** → **Database** → **Redis**
3. Railway automatically sets `REDIS_URL` for linked services

## Configuration

### Environment Variable

Add to your `.env` file:

```bash
# Local development
REDIS_URL=redis://localhost:6379

# Railway (auto-set when Redis service is linked)
# REDIS_URL=redis://default:password@host.railway.internal:6379
```

### Verify Connection

```python
from wizards_consolidated.redis_config import redis_health_check

result = redis_health_check()
print(result)
# {'status': 'healthy', 'version': '8.4.0', 'connected_clients': 1, ...}
```

Or from command line:

```bash
python -c "from wizards_consolidated.redis_config import redis_health_check; print(redis_health_check())"
```

## Usage in Code

### Basic Usage

```python
from attune import get_redis_memory

# Auto-detects REDIS_URL, falls back to localhost, then mock mode
memory = get_redis_memory()

# Store data (expires in 1 hour by default)
memory.set("my_key", {"data": "value"}, ttl=3600)

# Retrieve data
data = memory.get("my_key")
```

### With EmpathyOS

```python
from attune import EmpathyOS, get_redis_memory

memory = get_redis_memory()

empathy = EmpathyOS(
    user_id="developer",
    short_term_memory=memory,
)

# Store working data
empathy.stash("analysis_results", {"files": 10, "issues": 3})

# Retrieve later
results = empathy.retrieve("analysis_results")
```

### Wizard Sessions

```python
from wizards_consolidated.healthcare.sbar_wizard import SBARWizard

# Sessions automatically use Redis when available
wizard = SBARWizard()
session = wizard.create_session(user_id="nurse_001")
```

## Graceful Degradation

The framework handles Redis unavailability gracefully:

- **Redis available**: Full short-term memory functionality
- **Redis unavailable**: Falls back to in-memory storage (session-only, not shared)
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
memory.set("temp_data", data, ttl=300)  # 5 minutes
memory.set("session_data", data, ttl=3600)  # 1 hour
memory.set("staging_pattern", data, ttl=86400)  # 24 hours
```

### Monitoring

```python
from wizards_consolidated.redis_config import redis_health_check

health = redis_health_check()
print(f"Memory used: {health.get('used_memory')}")
print(f"Connected clients: {health.get('connected_clients')}")
```

## Next Steps

- [Short-Term Memory Guide](../reference/SHORT_TERM_MEMORY.md) - Deep dive into memory patterns
- [Multi-Agent Philosophy](../explanation/multi-agent-philosophy.md) - Team coordination with Redis
- [Configuration Reference](../reference/configuration.md) - All configuration options
