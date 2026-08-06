---
description: Unified Memory System: *A single API for short-term (Redis) and long-term (persistent) memory* --- ## Overview The Attune AI provides a **two-tier memor
---

# Unified Memory System

*A single API for short-term (Redis) and long-term (persistent) memory*

---

## Overview

The Attune AI provides a **two-tier memory architecture** that mirrors how humans think:

| Memory Tier | Purpose | Backend | Lifetime |
|-------------|---------|---------|----------|
| **Short-Term** | Working memory, task coordination | Redis | Minutes to hours (TTL-based) |
| **Long-Term** | Cross-session patterns, validated knowledge | Persistent storage | Months to years |

The `UnifiedMemory` class provides a single interface to both tiers, with automatic environment detection and pattern promotion workflows.

---

## Quick Start

### Basic Usage

```python
from attune.memory import UnifiedMemory

# Create the unified memory interface (auto-configured)
memory = UnifiedMemory(user_id="analyst@company.com")

# Short-term memory (working data, expires)
memory.stash("current_task", {"files": ["api.py"], "status": "analyzing"})
task = memory.retrieve("current_task")

# Long-term memory (persistent patterns)
result = memory.persist_pattern(
    content="When handling API errors, always include request_id for tracing",
    pattern_type="best_practice"
)
pattern = memory.recall_pattern(result["pattern_id"])
```

### Checking Tier Health

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="analyst@company.com")

# Check health of both tiers
health = memory.health_check()
print(f"Short-term available: {health['short_term']['available']}")
print(f"Long-term available: {health['long_term']['available']}")
print(f"Environment: {health['environment']}")
```

---

## Environment Configuration

The memory system auto-detects its environment and configures storage accordingly:

### Automatic Detection

```python
from attune.memory import UnifiedMemory, MemoryConfig

# Auto-detect from environment variables
memory = UnifiedMemory(user_id="agent@company.com")
# Checks: REDIS_URL, ATTUNE_ENV, ATTUNE_STORAGE_DIR
```

### Manual Configuration

```python
from attune.memory import UnifiedMemory, MemoryConfig, Environment

# Development (mock Redis, local storage)
dev_config = MemoryConfig(
    environment=Environment.DEVELOPMENT,
    redis_mock=True,
    storage_dir="./dev_storage",
    encryption_enabled=False
)

# Production (real Redis, encrypted storage)
prod_config = MemoryConfig(
    environment=Environment.PRODUCTION,
    redis_url="redis://user:pass@host:6379",
    storage_dir="/var/attune/patterns",
    encryption_enabled=True
)

memory = UnifiedMemory(user_id="agent@company.com", config=prod_config)
```

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `ATTUNE_ENV` | Environment tier | `development`, `staging`, `production` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379` |
| `ATTUNE_REDIS_MOCK` | Force mock mode | `true` |
| `ATTUNE_STORAGE_DIR` | Long-term storage | `./patterns` |
| `ATTUNE_ENCRYPTION` | Enable encryption | `true` |
| `ATTUNE_CLAUDE_MEMORY` | Load Claude memory | `true` |

---

## Short-Term Memory Operations

Short-term memory is for **working data** that expires automatically.

### Stash and Retrieve

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="analyst@company.com")

# Store with default TTL (1 hour)
memory.stash("analysis_results", {
    "files_reviewed": 10,
    "issues_found": 3,
    "timestamp": "2025-12-10T10:00:00"
})

# Store with custom TTL (24 hours)
memory.stash("weekly_summary", {"summary": "..."}, ttl_seconds=86400)

# Retrieve
results = memory.retrieve("analysis_results")
```

### Stage Patterns for Validation

Before committing patterns to long-term memory, stage them for review:

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="analyst@company.com")

# Stage a discovered pattern
staged_id = memory.stage_pattern(
    pattern_data={
        "content": "Always validate user input at API boundaries",
        "code_example": "def validate(input): ...",
        "metadata": {"discovered_in": "pr_review_42"}
    },
    pattern_type="security",
    ttl_hours=24  # Auto-expires if not promoted
)

# View all staged patterns
staged = memory.get_staged_patterns()
for p in staged:
    print(f"Pattern: {p['pattern_type']} - Confidence: {p.get('confidence', 'N/A')}")
```

---

## Long-Term Memory Operations

Long-term memory is for **validated patterns** that persist across sessions.

### Persist Patterns

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="analyst@company.com")

# Basic pattern storage
result = memory.persist_pattern(
    content="Use dependency injection for testable code",
    pattern_type="architecture"
)
print(f"Pattern ID: {result['pattern_id']}")
print(f"Classification: {result['classification']}")  # AUTO-DETECTED

# With explicit classification
result = memory.persist_pattern(
    content="Redact account numbers before storing support tickets",
    pattern_type="data_handling",
    classification="SENSITIVE",  # Forces encryption
    metadata={"author": "platform_team"}
)
```

### Recall Patterns

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="analyst@company.com")

# Retrieve by ID
pattern = memory.recall_pattern("pat_abc123")
if pattern:
    print(f"Content: {pattern['content']}")
    print(f"Type: {pattern['pattern_type']}")
    print(f"Created: {pattern['created_at']}")
```

### Classification Levels

Patterns are automatically classified based on content:

| Classification | Description | Encryption | Retention |
|----------------|-------------|------------|-----------|
| `PUBLIC` | General patterns, shareable | No | 365 days |
| `INTERNAL` | Proprietary patterns | Optional | 180 days |
| `SENSITIVE` | PII-bearing patterns | **Required** (AES-256) | 90 days |

```python
from attune.memory import UnifiedMemory, Classification

memory = UnifiedMemory(user_id="analyst@company.com")

# Auto-classification (recommended)
result = memory.persist_pattern(
    content="JWT refresh pattern for auth tokens",
    pattern_type="security",
    auto_classify=True  # Default
)
# Result: {"classification": "INTERNAL"}

# Explicit classification
result = memory.persist_pattern(
    content="Customer record handoff protocol",
    pattern_type="data_handling",
    classification=Classification.SENSITIVE
)
# Result: {"classification": "SENSITIVE", "encrypted": True}
```

---

## Pattern Promotion Workflow

The pattern promotion workflow moves validated patterns from short-term to long-term memory:

```mermaid
flowchart LR
    D["Discovery (agent)<br/>contributor discovers"]
    S["Staging (review)<br/>validator reviews and promotes"]
    L["Long-term (library)<br/>anyone can recall"]
    D --> S --> L
```

### Example Workflow

```python
from attune import AccessTier
from attune.memory import UnifiedMemory

# 1. Contributor discovers a pattern
contributor = UnifiedMemory(
    user_id="code_reviewer",
    access_tier=AccessTier.CONTRIBUTOR
)

staged_id = contributor.stage_pattern(
    pattern_data={
        "content": "Use connection pooling for database access",
        "confidence": 0.92,
        "discovered_in": "performance_review"
    },
    pattern_type="optimization"
)
print(f"Pattern staged: {staged_id}")

# 2. Validator reviews and promotes
validator = UnifiedMemory(
    user_id="senior_architect",
    access_tier=AccessTier.VALIDATOR
)

# Review staged patterns
staged = validator.get_staged_patterns()
for p in staged:
    if p.get("confidence", 0) > 0.85:
        # Promote to long-term storage
        result = validator.promote_pattern(
            staged_pattern_id=p["pattern_id"],
            classification="INTERNAL",  # Optional override
        )
        print(f"Promoted: {result['pattern_id']}")
```

---

## Security Integration

The unified memory system includes enterprise-grade security controls.

### PII Scrubbing

Content is automatically scrubbed before storage:

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="analyst@company.com")

# PII in content is automatically redacted
result = memory.persist_pattern(
    content="User john.doe@company.com reported issue with SSN 123-45-6789",
    pattern_type="support_pattern"
)
# Stored as: "User [EMAIL] reported issue with SSN [SSN]"
```

### Secrets Detection

Secrets are detected and blocked:

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="analyst@company.com")

# This will trigger a security warning
result = memory.persist_pattern(
    content="API key: sk-proj-abc123...",
    pattern_type="api_integration"
)
# Result: {"error": "secrets_detected", "blocked": True}
```

### Audit Logging

All operations are logged for traceability:

```python
# Audit events are automatically generated for:
# - Pattern storage/retrieval
# - Classification decisions
# - Access control checks
# - Security violations

# View audit events programmatically
from attune.memory.security import AuditLogger
logger = AuditLogger(log_file="/var/log/attune/audit.jsonl")
```

---

## Complete Example: Multi-Agent Knowledge Building

```python
"""
Multi-agent system where agents discover and share patterns.
"""
import asyncio
from attune import AccessTier
from attune.memory import UnifiedMemory

async def knowledge_building_demo():
    # Specialist agents discover patterns. Each UnifiedMemory
    # instance auto-wires a shared Redis short-term backend.
    security_agent = UnifiedMemory(
        user_id="security_specialist",
        access_tier=AccessTier.CONTRIBUTOR
    )

    performance_agent = UnifiedMemory(
        user_id="performance_specialist",
        access_tier=AccessTier.CONTRIBUTOR
    )

    # Lead architect validates and promotes
    architect = UnifiedMemory(
        user_id="lead_architect",
        access_tier=AccessTier.VALIDATOR
    )

    # 1. Security agent discovers a pattern
    security_agent.stage_pattern(
        pattern_data={
            "content": "Always sanitize SQL inputs using parameterized queries",
            "code": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
            "confidence": 0.95,
            "source": "code_review_auth_module"
        },
        pattern_type="security"
    )
    print("Security pattern staged")

    # 2. Performance agent discovers a pattern
    performance_agent.stage_pattern(
        pattern_data={
            "content": "Use bulk operations for batch database updates",
            "code": "session.bulk_insert_mappings(Model, data_list)",
            "confidence": 0.88,
            "source": "performance_analysis_q4"
        },
        pattern_type="optimization"
    )
    print("Performance pattern staged")

    # 3. Architect reviews all staged patterns
    staged = architect.get_staged_patterns()
    print(f"\nPatterns awaiting review: {len(staged)}")

    for p in staged:
        print(f"\n--- {p['pattern_type'].upper()} Pattern ---")
        print(f"Content: {p['content'][:50]}...")
        print(f"Confidence: {p.get('confidence', 'N/A')}")

        # Promote high-confidence patterns
        if p.get('confidence', 0) > 0.85:
            result = architect.promote_pattern(p['pattern_id'])
            print(f"PROMOTED -> Long-term ID: {result['pattern_id']}")
        else:
            print("NEEDS MORE VALIDATION")

    # 4. Check long-term library
    health = architect.health_check()
    print(f"\n=== Memory Health ===")
    print(f"Short-term: {health['short_term']['available']}")
    print(f"Long-term: {health['long_term']['available']}")
    print(f"Environment: {health['environment']}")

if __name__ == "__main__":
    asyncio.run(knowledge_building_demo())
```

---

## Migration from Legacy APIs

### Sharing a short-term backend directly

```python
# Manual short-term backend (advanced)
from attune import get_redis_memory
backend = get_redis_memory()
backend.stash("current_task", {"status": "analyzing"})

# Recommended: let UnifiedMemory wire the backend for you
from attune.memory import UnifiedMemory
memory = UnifiedMemory(user_id="agent")
memory.stash("current_task", {"status": "analyzing"})
```

### From `attune.security`

```python
# OLD (still works via re-exports)
from attune.security import PIIScrubber, SecretsDetector

# NEW (recommended)
from attune.memory import PIIScrubber, SecretsDetector
from attune.memory.security import AuditLogger
```

---

## Next Steps

- **[Security Architecture](./security-architecture.md)**: PII scrubbing, audit logging
- **[API Reference: Memory](../reference/multi-agent.md)**: Complete class documentation

---

*The unified memory system was introduced in v1.10.0 as part of the MemDocs consolidation effort. It combines the best of short-term Redis coordination with long-term pattern persistence.*
