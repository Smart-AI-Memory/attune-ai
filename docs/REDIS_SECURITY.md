---
description: Redis Short-Term Memory Security Guide: **Version:** 4.4.0 **Last Updated:** January 2026 This document covers security considerations, best practices, and conf
---

# Redis Short-Term Memory Security Guide

**Version:** 4.4.0
**Last Updated:** January 2026

This document covers security considerations, best practices, and configuration options for the Redis short-term memory system in the Attune AI.

---

## Table of Contents

1. [Security Features](#security-features)
2. [Configuration Options](#configuration-options)
3. [PII Scrubbing](#pii-scrubbing)
4. [Secrets Detection](#secrets-detection)
5. [Connection Security](#connection-security)
6. [Access Control](#access-control)
7. [Deployment Recommendations](#deployment-recommendations)
8. [Compliance](#compliance)

---

## Security Features

The Redis short-term memory system includes several security features:

| Feature | Default | Description |
|---------|---------|-------------|
| PII Scrubbing | ✅ Enabled | Automatically removes PII before storage |
| Secrets Detection | ✅ Enabled | Blocks storage of API keys, passwords, etc. |
| SSL/TLS Support | ❌ Disabled | Encrypts data in transit |
| Password Auth | ❌ Optional | Redis authentication |
| Access Tiers | ✅ Enabled | Role-based access control |
| TTL Expiration | ✅ Enabled | Automatic data cleanup |

---

## Configuration Options

### RedisConfig Security Settings

```python
from attune.memory.short_term import RedisConfig, RedisShortTermMemory

config = RedisConfig(
    host="localhost",
    port=6379,
    password="your-secure-password",  # Recommended for production

    # Security settings
    pii_scrub_enabled=True,           # Scrub PII before storage (default: True)
    secrets_detection_enabled=True,    # Block secrets from storage (default: True)

    # SSL/TLS (for managed Redis services)
    ssl=True,
    ssl_cert_reqs="required",
    ssl_ca_certs="/path/to/ca.crt",
)

memory = RedisShortTermMemory(config=config)
```

### Environment Variables

```bash
# Connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-password
REDIS_DB=0

# SSL/TLS
REDIS_SSL=true
REDIS_SSL_CERT_REQS=required
REDIS_SSL_CA_CERTS=/path/to/ca.crt

# Full URL (alternative)
REDIS_URL=rediss://user:password@host:port/db

# Mock mode (for testing without Redis)
ATTUNE_REDIS_MOCK=true
```

---

## PII Scrubbing

### What Gets Scrubbed

The PII scrubber automatically detects and replaces:

| PII Type | Example Input | Output |
|----------|---------------|--------|
| Email | `john@example.com` | `[EMAIL]` |
| Phone | `555-123-4567` | `[PHONE]` |
| SSN | `123-45-6789` | `[SSN]` |
| Credit Card | `4532-1234-5678-9010` | `[CC]` |
| IPv4 Address | `192.168.1.1` | `[IP]` |
| IPv6 Address | `2001:0db8:85a3::8a2e:0370:7334` | `[IP]` |
| Street Address | `123 Main Street` | `[ADDRESS]` |
| Medical Record Number | `MRN-1234567` | `[MRN]` |
| Patient ID | `PID-123456` | `[PATIENT_ID]` |

### Example

```python
from attune.memory.short_term import (
    RedisShortTermMemory,
    RedisConfig,
    AgentCredentials,
    AccessTier
)

memory = RedisShortTermMemory()
creds = AgentCredentials(agent_id="agent_1", tier=AccessTier.CONTRIBUTOR)

# Original data with PII
data = {
    "patient_notes": "Contact patient John Doe at john.doe@hospital.com",
    "phone": "555-123-4567",
    "ssn": "123-45-6789"
}

# Store - PII is automatically scrubbed
memory.stash("patient_record", data, creds)

# Retrieve - PII has been replaced
result = memory.retrieve("patient_record", creds)
# Result: {
#   "patient_notes": "Contact patient John Doe at [EMAIL]",
#   "phone": "[PHONE]",
#   "ssn": "[SSN]"
# }
```

### Disabling PII Scrubbing

For performance-critical paths where you're certain no PII is present:

```python
# Option 1: Disable globally
config = RedisConfig(pii_scrub_enabled=False)

# Option 2: Skip per-operation
memory.stash("key", data, creds, skip_sanitization=True)
```

**Warning:** Only disable PII scrubbing when you have verified the data contains no sensitive information.

---

## Secrets Detection

### What Gets Blocked

The secrets detector prevents storage of:

| Secret Type | Severity | Example Pattern |
|-------------|----------|-----------------|
| Anthropic API Key | CRITICAL | `sk-ant-api03-...` |
| OpenAI API Key | CRITICAL | `sk-...` |
| AWS Access Key | CRITICAL | `AKIA...` |
| AWS Secret Key | CRITICAL | `aws_secret_access_key=...` |
| GitHub Token | HIGH | `ghp_...`, `github_pat_...` |
| Private Keys | CRITICAL | `-----BEGIN RSA PRIVATE KEY-----` |
| JWT Tokens | MEDIUM | `eyJ...` (with valid structure) |
| Database URLs | HIGH | `postgresql://user:pass@...` |
| Generic API Keys | HIGH | `api_key=...`, `apikey=...` |

### Handling SecurityError

When secrets are detected, a `SecurityError` is raised:

```python
from attune.memory.short_term import SecurityError

try:
    memory.stash("config", {"api_key": "sk-real-secret-key"}, creds)
except SecurityError as e:
    print(f"Blocked: {e}")
    # Handle appropriately - don't log the actual secret!
```

### Disabling Secrets Detection

**Not recommended for production.** Only disable for specific use cases:

```python
# Disable globally (not recommended)
config = RedisConfig(secrets_detection_enabled=False)

# Skip per-operation (use with extreme caution)
memory.stash("key", data, creds, skip_sanitization=True)
```

---

## Connection Security

### Local Development

For local development on a password-protected machine:

```python
# Minimal config - acceptable for local dev
config = RedisConfig(host="localhost", port=6379)
```

### Production Deployment

For production, always use:

1. **Password Authentication**
2. **SSL/TLS Encryption**
3. **Network Isolation**

```python
# Production config
config = RedisConfig(
    host="redis.internal.example.com",
    port=6379,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=True,
    ssl_cert_reqs="required",
    ssl_ca_certs="/etc/ssl/certs/redis-ca.crt",
)
```

### Using Managed Redis Services

For cloud Redis services (Redis Cloud, AWS ElastiCache, etc.):

```python
# Using REDIS_URL (auto-detects SSL from rediss://)
import os
from attune.redis_config import get_redis_memory

# Set REDIS_URL=rediss://user:pass@host:port
memory = get_redis_memory()  # Auto-configures from env
```

---

## Access Control

### Access Tiers

The framework implements role-based access control:

| Tier | Level | Permissions |
|------|-------|-------------|
| OBSERVER | 1 | Read-only access |
| CONTRIBUTOR | 2 | Read + write working memory |
| VALIDATOR | 3 | + Promote staged patterns |
| STEWARD | 4 | + Admin operations, audit access |

### Usage

```python
from attune.memory.short_term import AgentCredentials, AccessTier

# Read-only agent
observer = AgentCredentials(agent_id="reader", tier=AccessTier.OBSERVER)

# Agent that can write
contributor = AgentCredentials(agent_id="worker", tier=AccessTier.CONTRIBUTOR)

# Admin agent
steward = AgentCredentials(agent_id="admin", tier=AccessTier.STEWARD)
```

---

## Deployment Recommendations

### Development Environment

```bash
# .env or shell profile
export REDIS_HOST=localhost
export REDIS_PORT=6379
# No password needed for local Redis
```

- Local Redis without password is acceptable
- Machine-level security (login password) provides protection
- Data is ephemeral (TTL-based expiration)

### Staging Environment

```bash
export REDIS_URL=redis://:staging-password@redis-staging:6379
```

- Use password authentication
- Consider SSL if Redis is on separate host
- Use separate Redis instance from production

### Production Environment

```bash
export REDIS_URL=rediss://:$REDIS_PASSWORD@redis-production:6379
```

**Required:**
- ✅ Strong password authentication
- ✅ SSL/TLS encryption
- ✅ Network isolation (VPC/private network)
- ✅ Regular security updates
- ✅ Monitoring and alerting

**Recommended:**
- Redis Sentinel or Cluster for high availability
- Regular backups (if persistence is needed)
- Connection pooling limits

---

## Compliance

### HIPAA Compliance

The short-term memory system supports HIPAA compliance through:

1. **Automatic PII Scrubbing** - PHI is removed before storage
2. **Audit Logging** - All operations are logged via structlog
3. **Access Control** - Role-based tiers limit data access
4. **Encryption in Transit** - SSL/TLS support
5. **Data Expiration** - TTL ensures data isn't retained indefinitely

**Configuration for HIPAA:**

```python
config = RedisConfig(
    pii_scrub_enabled=True,          # Required
    secrets_detection_enabled=True,   # Required
    ssl=True,                         # Required
    ssl_cert_reqs="required",         # Required
    password="strong-password",       # Required
)
```

### GDPR Compliance

- **Data Minimization:** PII scrubbing removes unnecessary personal data
- **Right to Erasure:** TTL-based expiration ensures data deletion
- **Access Logging:** Structlog provides audit trails

### SOC2 Compliance

- **Access Control:** Four-tier role system
- **Encryption:** SSL/TLS for data in transit
- **Monitoring:** Metrics tracking for security events

---

## Monitoring Security Metrics

The framework tracks security-related metrics:

```python
metrics = memory.get_metrics()

print(metrics["security"])
# {
#   "pii_scrubbed_total": 150,      # Total PII instances removed
#   "pii_scrub_operations": 45,     # Operations that had PII
#   "secrets_blocked_total": 3       # Storage attempts blocked
# }
```

Use these metrics to:
- Monitor PII exposure attempts
- Track secrets leakage attempts
- Audit security effectiveness

---

## Troubleshooting

### PII Not Being Scrubbed

1. Check `pii_scrub_enabled=True` in config
2. Verify `skip_sanitization=False` in stash call
3. Check if the PII pattern is supported (see table above)

### Secrets Not Being Blocked

1. Check `secrets_detection_enabled=True` in config
2. Verify the secret matches known patterns
3. Check severity level (only CRITICAL and HIGH are blocked)

### Connection Issues

```python
from attune.redis_config import check_redis_connection

status = check_redis_connection()
print(status)
# {
#   "connected": True,
#   "host": "localhost",
#   "port": 6379,
#   "use_mock": False,
#   "error": None
# }
```

---

## Related Documentation

- [SECURE_MEMORY_ARCHITECTURE.md](./SECURE_MEMORY_ARCHITECTURE.md) - Overall memory security design
- [ENTERPRISE_PRIVACY_INTEGRATION.md](./ENTERPRISE_PRIVACY_INTEGRATION.md) - Privacy compliance details
- [Long-Term Memory Security](./memory/README.md) - MemDocs security features

---

**Questions or Issues?**

- GitHub Issues: [Smart-AI-Memory/attune-ai](https://github.com/Smart-AI-Memory/attune-ai/issues)
- Security vulnerabilities: See [SECURITY.md](../SECURITY.md)
