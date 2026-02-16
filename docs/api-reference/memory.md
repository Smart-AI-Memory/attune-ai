---
description: Memory API API reference: Unified two-tier memory system for AI agent collaboration. --- ## Overview The memory system provide
---

# Memory API

Unified two-tier memory system for AI agent collaboration.

---

## Overview

The memory system provides two tiers:

| Tier | Backend | Purpose |
|------|---------|---------|
| **Short-term** | Redis | Agent coordination, working memory, TTL-based expiration |
| **Long-term** | File/SQLite | Cross-session patterns, encrypted storage, compliance |

---

## Quick Start

```python
from attune.memory import UnifiedMemory

# Initialize with environment auto-detection
memory = UnifiedMemory(user_id="agent@company.com")

# Short-term operations
memory.stash("working_data", {"key": "value"})
data = memory.retrieve("working_data")

# Long-term operations
result = memory.persist_pattern(
    content="Algorithm for X",
    pattern_type="algorithm",
)
pattern = memory.recall_pattern(result["pattern_id"])

# Pattern promotion (short-term → long-term)
staged_id = memory.stage_pattern({"content": "..."})
memory.promote_pattern(staged_id)
```

---

## UnifiedMemory

Main entry point for memory operations.

### Constructor

```python
UnifiedMemory(
    user_id: str,                      # User/agent identifier
    redis_url: str | None = None,      # Redis URL (auto-detected if None)
    encryption_key: str | None = None, # Encryption key for SENSITIVE data
    compliance_mode: str = "standard", # "standard" or "hipaa"
)
```

### Short-term Methods

| Method | Description |
|--------|-------------|
| `stash(key, value, ttl=3600)` | Store data with TTL (default 1 hour) |
| `retrieve(key)` | Get data by key |
| `delete(key)` | Remove data |
| `extend_ttl(key, seconds)` | Extend expiration time |
| `list_keys(pattern="*")` | List matching keys |

### Long-term Methods

| Method | Description |
|--------|-------------|
| `persist_pattern(content, pattern_type, classification)` | Save pattern permanently |
| `recall_pattern(pattern_id)` | Retrieve pattern by ID |
| `search_patterns(query, limit=10)` | Search patterns |
| `delete_pattern(pattern_id)` | Remove pattern |

### Pattern Promotion

| Method | Description |
|--------|-------------|
| `stage_pattern(data)` | Stage pattern in short-term |
| `promote_pattern(staged_id)` | Promote to long-term |
| `validate_pattern(staged_id)` | Validate before promotion |

---

## Short-term Memory (Redis)

Direct access to Redis-backed short-term memory.

```python
from attune.memory import RedisShortTermMemory, AccessTier

# Create with connection
memory = RedisShortTermMemory(
    redis_url="redis://localhost:6379",
    default_ttl=3600,
)

# Store with access control
memory.store(
    key="sensitive_data",
    value={"api_key": "..."},
    access_tier=AccessTier.AGENT,  # Only agents can access
)

# Retrieve
data = memory.get("sensitive_data")
```

### AccessTier

| Tier | Access Level |
|------|--------------|
| `OBSERVER` | Read-only, limited scope |
| `CONTRIBUTOR` | Read/write within scope |
| `AGENT` | Full agent-level access |
| `STEWARD` | Administrative access |

---

## Long-term Memory (Secure)

Encrypted, classified storage for sensitive patterns.

```python
from attune.memory import SecureMemDocsIntegration, Classification

# Create secure storage
storage = SecureMemDocsIntegration(
    encryption_key="your-key-here",
    compliance_mode="hipaa",
)

# Store with classification
pattern_id = storage.store_pattern(
    content="Patient data processing algorithm",
    classification=Classification.SENSITIVE,
    metadata={"domain": "healthcare"},
)

# Retrieve (auto-decrypts)
pattern = storage.get_pattern(pattern_id)
```

### Classification

| Level | Description |
|-------|-------------|
| `PUBLIC` | Shareable, no encryption |
| `INTERNAL` | Team-only access |
| `SENSITIVE` | Encrypted, audit logged |

---

## Memory Graph

Cross-workflow intelligence through graph-based pattern storage.

```python
from attune.memory import MemoryGraph, EdgeType

graph = MemoryGraph(path="memory_graph.json")

# Add findings from workflows
bug_id = graph.add_finding(
    workflow="bug-predict",
    finding={"type": "bug", "name": "Null reference"},
)

fix_id = graph.add_finding(
    workflow="code-review",
    finding={"type": "fix", "name": "Add null check"},
)

# Create relationships
graph.add_edge(bug_id, fix_id, EdgeType.FIXED_BY)

# Query related findings
fixes = graph.find_related(bug_id, edge_types=[EdgeType.FIXED_BY])
```

### EdgeType

| Type | Description |
|------|-------------|
| `FIXED_BY` | Bug fixed by fix |
| `CAUSES` | Issue causes another |
| `SIMILAR_TO` | Similar patterns |
| `CONTAINS` | Parent-child relationship |
| `DEPENDS_ON` | Dependency relationship |

---

## Security Features

### PII Scrubbing

```python
from attune.memory import PIIScrubber

scrubber = PIIScrubber()

# Scrub before storing
clean_text = scrubber.scrub(
    "Contact john@example.com or call 555-1234",
)
# Result: "Contact [EMAIL] or call [PHONE]"
```

### Secrets Detection

```python
from attune.memory import SecretsDetector

detector = SecretsDetector()

# Check for secrets before storing
secrets = detector.detect(text)
if secrets:
    raise SecurityError(f"Found secrets: {secrets}")
```

### Audit Logging

```python
from attune.memory import AuditLogger

logger = AuditLogger(log_path="audit.log")

# Log access
logger.log_access(
    user_id="agent_1",
    pattern_id="pat_123",
    action="read",
    classification="SENSITIVE",
)
```

---

## Cross-session Coordination

Coordinate between multiple agent sessions.

```python
from attune.memory import CrossSessionCoordinator

coordinator = CrossSessionCoordinator(redis_url="redis://localhost:6379")

# Register session
session_id = coordinator.register_session(
    session_type=SessionType.WORKFLOW,
    metadata={"workflow": "security-audit"},
)

# Broadcast to other sessions
coordinator.broadcast(
    channel="findings",
    message={"severity": "high", "finding": "..."},
)

# Listen for messages
async for message in coordinator.subscribe("findings"):
    process_finding(message)
```

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Redis connection URL |
| `RAILWAY_REDIS_URL` | Railway-hosted Redis |
| `ATTUNE_ENCRYPTION_KEY` | Encryption key for SENSITIVE |
| `ATTUNE_COMPLIANCE_MODE` | "standard" or "hipaa" |

### Memory Control Panel

```bash
# Start memory control panel
empathy-memory serve

# Check status
empathy-memory status

# List patterns
empathy-memory patterns
```

---

## See Also

- [Short-term Memory Guide](../reference/SHORT_TERM_MEMORY.md)
- [Getting Started - Redis Setup](../getting-started/redis-setup.md)
- [Security Architecture](../architecture/SECURE_MEMORY_ARCHITECTURE.md)
