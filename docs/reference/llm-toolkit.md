---
description: LLM Toolkit API reference - Claude integration with PII scrubbing, secrets detection, and audit logging.
---

# LLM Toolkit

Claude integration with security controls: PII scrubbing,
secrets detection, and audit logging.

## Overview

The LLM Toolkit provides:

- **Anthropic Integration**: Claude API via `EmpathyLLM`
- **Security Controls**: PII scrubbing, secrets detection
- **Audit Logging**: JSONL audit trail of LLM interactions
- **Claude Memory Integration**: CLAUDE.md support for
  persistent context

## Key Features

### Anthropic Integration

```python
import os
from attune.llm import EmpathyLLM

# Anthropic Claude (the only supported provider)
llm = EmpathyLLM(
    provider="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-sonnet-4-5",
    target_level=4,
)
```

### Automatic Security Controls

- **PII Scrubbing**: Removes SSN, credit cards, phone
  numbers, addresses
- **Secrets Detection**: Flags API keys, tokens, passwords
- **Audit Logging**: JSONL audit trail of interactions

## Class Reference

### EmpathyLLM

::: attune.llm.core.EmpathyLLM
    options:
      show_root_heading: false
      show_source: false
      heading_level: 4

Main LLM interface. Enable the built-in security pipeline
with `enable_security=True`.

**Example:**

```python
import os
from attune.llm import EmpathyLLM

# Initialize with the built-in security pipeline
llm = EmpathyLLM(
    provider="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    enable_security=True,
)

# Secure interaction
response = llm.interact(
    user_id="user_123",
    user_input="Help me debug this API issue",
    context={},
)
```

### PIIScrubber

Detect and scrub personally identifiable information.

**Detects:**

- SSN (Social Security Numbers)
- Credit card numbers
- Phone numbers (US and international)
- Email addresses
- Physical addresses
- Names (when enabled)
- Healthcare identifiers (MRN, Patient ID)

**Example:**

```python
from attune.memory import PIIScrubber

scrubber = PIIScrubber()

# Text with PII
text = """
John Doe (SSN: 123-45-6789)
called from 555-123-4567 about his
credit card ending in 4532.
"""

# scrub() returns (scrubbed_text, detections)
scrubbed, detections = scrubber.scrub(text)
print(scrubbed)
# Output:
# John Doe (SSN: [SSN])
# called from [PHONE] about his
# credit card ending in 4532.

# Inspect what was detected
for item in detections:
    print(f"Confidence: {item.confidence}")
```

### SecretsDetector

Detect API keys, tokens, and credentials.

**Detects:**

- API keys (AWS, Stripe, GitHub, etc.)
- OAuth tokens
- Private keys
- Database connection strings
- JWT tokens

**Example:**

```python
from attune.memory import SecretsDetector

detector = SecretsDetector()

# Code with secrets
code = """
# Config
STRIPE_KEY = "sk_live_51HxJ..."
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG..."
DB_CONN = "postgresql://user:pass@localhost/db"
"""

# Check for secrets
secrets = detector.detect(code)
if secrets:
    print("Secrets detected!")
    for secret in secrets:
        print(f"  confidence: {secret.confidence}")
        print(f"  context: {secret.context_snippet}")
else:
    print("No secrets detected")
```

### AuditLogger

JSONL audit logging of LLM interactions and security
events.

**Logs:**

- LLM interactions
- PII scrubbing and secrets counts
- Security policy violations
- Pattern store/retrieve events

**Example:**

```python
from attune.memory.security import AuditLogger

logger = AuditLogger(log_dir="logs")

# Log an LLM interaction
logger.log_llm_request(
    user_id="user_123",
    empathy_level=4,
    provider="anthropic",
    model="claude-sonnet-4-5",
    memory_sources=[],
    pii_count=2,
    secrets_count=0,
)

# Log a security policy violation
logger.log_security_violation(
    user_id="user_123",
    violation_type="blocked_secret",
    severity="high",
    details={"reason": "API key in prompt"},
)
```

## Security Features

### PII Scrubbing Patterns

```python
from attune.memory import PIIScrubber

# Default patterns (includes MRN and Patient ID)
scrubber = PIIScrubber()

# Add a custom pattern
scrubber.add_custom_pattern(
    name="employee_id",
    pattern=r"\bEMP\d{6}\b",
    replacement="[EMP_ID]",
)

text = "Employee EMP123456 accessed MRN: 987654"
scrubbed, _ = scrubber.scrub(text)
print(scrubbed)
# Output: Employee [EMP_ID] accessed [MRN]
```

### Secrets Detection Configuration

```python
from attune.memory import SecretsDetector

detector = SecretsDetector(
    entropy_threshold=4.5,  # Lower = more sensitive
)

# Custom secret pattern
detector.add_custom_pattern(
    name="internal_api_key",
    pattern=r"INTERNAL_[A-Za-z0-9]{32}",
    severity="high",
)

# Check code before committing
with open("config.py") as f:
    code = f.read()

secrets = detector.detect(code)
if secrets:
    print("Do not commit! Secrets detected:")
    for secret in secrets:
        print(f"  confidence {secret.confidence}")
```

### Audit Logging Format

```json
{
  "timestamp": "2025-01-20T15:30:00Z",
  "event_type": "llm_request",
  "user_id": "user_123",
  "provider": "anthropic",
  "model": "claude-sonnet-4-5",
  "empathy_level": 4,
  "pii_count": 2,
  "secrets_count": 0,
  "duration_ms": 1234
}
```

## Claude Memory Integration

### CLAUDE.md Support

```python
import os
from attune.llm import EmpathyLLM
from attune.memory import ClaudeMemoryConfig

# Configure Claude Memory
memory_config = ClaudeMemoryConfig(
    enabled=True,
    load_enterprise=True,  # /etc/claude/CLAUDE.md
    load_user=True,        # ~/.claude/CLAUDE.md
    load_project=True,     # ./.claude/CLAUDE.md
)

# Initialize with memory
llm = EmpathyLLM(
    provider="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    claude_memory_config=memory_config,
)

# Memory is automatically loaded and included in context
response = llm.interact(
    user_id="user_123",
    user_input="Help with deployment",
    context={},
)

# Memory instructions from CLAUDE.md are followed
```

## Usage Patterns

### Complete Security Setup

```python
import os
from attune.llm import EmpathyLLM
from attune.memory import PIIScrubber, SecretsDetector
from attune.memory.security import AuditLogger

# Initialize security components
pii_scrubber = PIIScrubber()
secrets_detector = SecretsDetector()
audit_logger = AuditLogger(log_dir="logs")

# Configure the LLM with the built-in security pipeline
llm = EmpathyLLM(
    provider="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    enable_security=True,
)

# Interactions run through the security pipeline
response = llm.interact(
    user_id="user_123",
    user_input="Help debug this error",
    context={},
)
```

## Best Practices

### Production Security Checklist

- [ ] Enable the security pipeline (`enable_security=True`)
- [ ] Run prompts through `PIIScrubber` before sending
- [ ] Run prompts through `SecretsDetector` before sending
- [ ] Keep an `AuditLogger` trail of interactions
- [ ] Use encrypted storage (SQLite encryption or
      PostgreSQL + encryption at rest)
- [ ] Rotate API keys regularly
- [ ] Monitor audit logs
- [ ] Review access patterns periodically

## See Also

- [Configuration API](config.md)
- [Security Architecture](../how-to/security-architecture.md)
