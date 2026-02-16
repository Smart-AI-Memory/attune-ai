# Secure Memory + MemDocs Integration Guide
**Attune AI v1.8.0-alpha**

Enterprise-ready integration of Claude Memory (CLAUDE.md) and MemDocs with comprehensive security controls.

## 🎯 Quick Start

### 1. Install with Security Features

```bash
# Install Attune AI
pip install -e ".[full]"

# Or minimal with LLM support
pip install -e ".[anthropic,memdocs]"
```

### 2. Set Up Memory Hierarchy

```bash
# Enterprise (requires admin/security team)
sudo mkdir -p /etc/claude
sudo cp examples/claude_memory/enterprise-CLAUDE-secure.md /etc/claude/CLAUDE.md
sudo chmod 644 /etc/claude/CLAUDE.md

# User level (personal preferences)
mkdir -p ~/.claude
cp examples/claude_memory/user-CLAUDE.md ~/.claude/CLAUDE.md

# Project level (team guidelines)
mkdir -p .claude
cp examples/claude_memory/project-CLAUDE.md ./.claude/CLAUDE.md
```

### 3. Initialize with Security

```python
import os
from attune.models import LLMExecutor
from attune.claude_memory import ClaudeMemoryConfig

# Load security policies from all levels
config = ClaudeMemoryConfig(
    enabled=True,
    load_enterprise=True,  # Organization security policies
    load_user=True,        # Personal preferences
    load_project=True      # Project guidelines
)

# Initialize LLM with memory
llm = LLMExecutor(
    provider="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    claude_memory_config=config,
    project_root="."
)

# Security policies are now enforced on every interaction
print(f"Memory loaded: {len(llm._cached_memory)} chars")
print("Security policies active ✓")
```

---

## 📚 Documentation Index

### Core Documents

| Document | Purpose | Audience |
|----------|---------|----------|
| [SECURE_MEMORY_ARCHITECTURE.md](../../SECURE_MEMORY_ARCHITECTURE.md) | Complete security architecture | Everyone |
| [ENTERPRISE_PRIVACY_INTEGRATION.md](../../ENTERPRISE_PRIVACY_INTEGRATION.md) | Privacy roadmap | Security/Compliance |
| [enterprise-CLAUDE-secure.md](enterprise-CLAUDE-secure.md) | Production security policies | Security team |
| [project-CLAUDE.md](project-CLAUDE.md) | Example project config | Developers |
| [user-CLAUDE.md](user-CLAUDE.md) | Example user preferences | End users |

### Implementation Examples

| Example | Shows | Complexity |
|---------|-------|------------|
| [Basic Memory Loading](#basic-memory-loading) | CLAUDE.md → LLM | ⭐ |
| [Hierarchical Policies](#hierarchical-policies) | Enterprise → User → Project | ⭐⭐ |
| [Secure MemDocs Storage](#secure-memdocs-storage) | Classification + encryption | ⭐⭐⭐ |
| [Healthcare Compliance](#healthcare-compliance-example) | HIPAA-compliant patterns | ⭐⭐⭐⭐ |
| [Air-Gapped Mode](#air-gapped-deployment) | Fully local deployment | ⭐⭐⭐⭐ |

---

## 🔐 Security Features

### 1. PII Protection (GDPR, HIPAA)

Automatically scrubs personal identifiable information before LLM calls and MemDocs storage.

```python
from secure_memdocs import SecureMemDocsIntegration

integration = SecureMemDocsIntegration(config)

# Input with PII
content = """
Contact John Doe at john.doe@email.com or 555-123-4567.
His SSN is 123-45-6789.
"""

# Store with auto-scrubbing
result = integration.store_pattern(
    pattern_content=content,
    pattern_type="example",
    user_id="dev@company.com"
)

# Stored content has PII replaced:
# "Contact [NAME] at [EMAIL] or [PHONE]. His SSN is [SSN]."
```

**Supported PII types:**
- Email addresses
- Phone numbers
- Social Security Numbers (SSN)
- Credit card numbers
- IP addresses
- Physical addresses
- Medical Record Numbers (MRN)
- Patient IDs

### 2. Secrets Detection (OWASP)

Blocks API keys, passwords, and other secrets from being stored or sent to LLMs.

```python
# This will raise SecurityError
try:
    content = """
    api_key = "sk_live_abc123xyz789"
    password = "SuperSecret123"
    """

    integration.store_pattern(
        pattern_content=content,
        pattern_type="config",
        user_id="dev@company.com"
    )
except SecurityError as e:
    print(f"Blocked: {e}")
    # "Secrets detected in pattern. Cannot store. Found: ['api_key', 'password']"
```

**Detected secret types:**
- API keys (Anthropic, OpenAI, AWS, etc.)
- Passwords
- Private keys (RSA, SSH, TLS)
- OAuth tokens
- JWT tokens
- Database connection strings

### 3. Classification System

Three-tier classification for MemDocs patterns:

```python
# PUBLIC - General, shareable patterns
integration.store_pattern(
    pattern_content="Standard sorting algorithm in Python",
    pattern_type="algorithm",
    user_id="dev@company.com"
)
# → Classification: PUBLIC
# → Encryption: No
# → Retention: 365 days

# INTERNAL - Company confidential
integration.store_pattern(
    pattern_content="Our proprietary scoring algorithm",
    pattern_type="algorithm",
    user_id="dev@company.com"
)
# → Classification: INTERNAL
# → Encryption: Optional
# → Retention: 180 days

# SENSITIVE - Regulated data (HIPAA, GDPR)
integration.store_pattern(
    pattern_content="Patient handoff protocol with SBAR format",
    pattern_type="clinical",
    user_id="doctor@hospital.com"
)
# → Classification: SENSITIVE
# → Encryption: AES-256-GCM (required)
# → Retention: 90 days
# → Audit: All access logged
```

### 4. Audit Logging (SOC2)

Comprehensive audit trail for compliance.

```python
# Every action is logged
integration.store_pattern(...)  # Logged
integration.retrieve_pattern(...)  # Logged
llm.interact(...)  # Logged

# Audit log format (JSON Lines)
{
  "timestamp": "2025-11-24T03:30:00Z",
  "event_id": "evt_abc123",
  "user_id": "dev@company.com",
  "action": "store_pattern",
  "classification": "INTERNAL",
  "pii_detected": 0,
  "secrets_detected": 0,
  "status": "success"
}
```

**View audit logs:**
```bash
# All pattern storage events
cat /var/log/empathy/audit.jsonl | jq 'select(.action == "store_pattern")'

# PII detections
cat /var/log/empathy/audit.jsonl | jq 'select(.pii_detected > 0)'

# Security violations
cat /var/log/empathy/audit.jsonl | jq 'select(.status == "blocked")'
```

---

## 💡 Usage Examples

### Basic Memory Loading

```python
from attune.models import LLMExecutor
from attune.claude_memory import ClaudeMemoryConfig

# Simple configuration
config = ClaudeMemoryConfig(enabled=True)
llm = LLMExecutor(
    provider="anthropic",
    api_key="your-key",
    claude_memory_config=config,
    project_root="."
)

# Memory from .claude/CLAUDE.md is now active
response = await llm.interact(
    user_id="dev@company.com",
    user_input="Help me implement secure error handling"
)
# Response will follow guidelines from CLAUDE.md
```

### Hierarchical Policies

```python
# Enterprise policy: PII scrubbing + secrets detection
# User policy: Prefers Python 3.10+, concise responses
# Project policy: Attune AI conventions

config = ClaudeMemoryConfig(
    enabled=True,
    load_enterprise=True,  # Security policies (highest priority)
    load_user=True,        # Personal preferences
    load_project=True      # Project conventions
)

llm = LLMExecutor(
    provider="anthropic",
    api_key="your-key",
    claude_memory_config=config,
    project_root="."
)

# All policies are merged with proper precedence:
# Enterprise (CANNOT override) → User → Project
print(llm._cached_memory)
# Shows:
# 1. Enterprise security policies (mandatory)
# 2. User preferences (optional)
# 3. Project guidelines (optional)
```

### Secure MemDocs Storage

```python
from secure_memdocs import SecureMemDocsIntegration

integration = SecureMemDocsIntegration(config)

# Store with automatic classification
pattern = """
# Healthcare Pattern: Vital Signs Monitoring

Normal ranges:
- Heart rate: 60-100 bpm
- Blood pressure: 90/60 to 120/80 mmHg
- Temperature: 97-99°F
"""

result = integration.store_pattern(
    pattern_content=pattern,
    pattern_type="clinical_protocol",
    user_id="nurse@hospital.com",
    auto_classify=True  # Detects healthcare keywords → SENSITIVE
)

print(result)
# {
#   "pattern_id": "pat_xyz123",
#   "classification": "SENSITIVE",
#   "sanitization_report": {
#     "pii_removed": [],
#     "secrets_detected": []
#   }
# }

# Retrieve with access control
retrieved = integration.retrieve_pattern(
    pattern_id="pat_xyz123",
    user_id="nurse@hospital.com",
    check_permissions=True  # Verifies user has access to SENSITIVE
)

print(retrieved["content"])  # Decrypted content
print(retrieved["metadata"]["classification"])  # "SENSITIVE"
```

### Healthcare Compliance Example

Complete HIPAA-compliant workflow:

```python
from attune.models import LLMExecutor
from attune.claude_memory import ClaudeMemoryConfig
from secure_memdocs import SecureMemDocsIntegration
import os

# 1. Load enterprise HIPAA policies
config = ClaudeMemoryConfig(
    enabled=True,
    load_enterprise=True,  # /etc/claude/CLAUDE.md with HIPAA rules
)

llm = LLMExecutor(
    provider="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    claude_memory_config=config,
    project_root="."
)

integration = SecureMemDocsIntegration(config)

# 2. Analyze patient handoff protocol (hypothetical)
response = await llm.interact(
    user_id="doctor@hospital.com",
    user_input="Analyze this handoff protocol for completeness",
    context={
        "wizard": "ClinicalProtocolMonitor",
        "classification": "SENSITIVE"
    }
)

# 3. Store learned pattern (HIPAA-compliant)
pattern_content = response["content"]  # LLM response with insights

result = integration.store_pattern(
    pattern_content=pattern_content,
    pattern_type="clinical_insight",
    user_id="doctor@hospital.com",
    auto_classify=True  # Will classify as SENSITIVE
)

# Automatically:
# ✓ Scrubbed PII (patient names, MRNs)
# ✓ Classified as SENSITIVE
# ✓ Encrypted with AES-256-GCM
# ✓ 90-day retention policy applied
# ✓ Audit log entry created
# ✓ Access restricted to authorized users

print(f"Pattern {result['pattern_id']} stored securely")
print(f"Classification: {result['classification']}")
print(f"Encryption: Active")
print(f"Retention: 90 days (HIPAA compliant)")
```

### Air-Gapped Deployment

Fully local mode for classified/regulated environments:

```bash
# Set environment variable
export EMPATHY_AIR_GAPPED=true
export OLLAMA_HOST=http://localhost:11434
```

```python
import os
from attune.models import LLMExecutor
from attune.claude_memory import ClaudeMemoryConfig

# Verify air-gapped mode
assert os.getenv("EMPATHY_AIR_GAPPED") == "true"

config = ClaudeMemoryConfig(
    enabled=True,
    load_enterprise=True,  # Local file only
    load_user=True,        # Local file only
    load_project=True      # Local file only
)

# Use local model (Ollama)
llm = LLMExecutor(
    provider="local",  # No external API calls
    model="llama2",
    endpoint="http://localhost:11434",
    claude_memory_config=config,
    project_root="."
)

# All operations are local:
# ✓ Memory: Local CLAUDE.md files
# ✓ LLM: Local Ollama model
# ✓ MemDocs: Local SQLite database
# ✓ Audit logs: Local filesystem
# ✗ No external network calls
# ✗ No cloud storage
# ✗ No telemetry

response = await llm.interact(
    user_id="analyst@classified-project",
    user_input="Analyze this classified document",
    context={"classification": "SENSITIVE"}
)

print("✓ Processed entirely locally")
print("✓ No data left the air-gapped environment")
```

---

## 🧪 Testing

### Run Security Tests

```bash
# Test suite for security controls
pytest tests/test_claude_memory.py -v         # Memory integration (14 tests)
pytest tests/test_security_controls.py -v     # PII, secrets, classification
pytest tests/test_memdocs_integration.py -v   # Secure storage

# Specific security tests
pytest -k "pii" -v          # PII scrubbing tests
pytest -k "secrets" -v      # Secrets detection tests
pytest -k "classification" -v  # Classification tests

# Full test suite with coverage
pytest --cov=attune --cov=secure_memdocs --cov-report=html
```

### Manual Security Validation

```python
# Test script: test_manual_security.py
from secure_memdocs import SecureMemDocsIntegration
from attune.claude_memory import ClaudeMemoryConfig

config = ClaudeMemoryConfig(enabled=True)
integration = SecureMemDocsIntegration(config)

# Test 1: PII Scrubbing
print("\n=== Test 1: PII Scrubbing ===")
content_with_pii = "Email john.doe@email.com and call 555-123-4567"
sanitized, pii = integration._scrub_pii(content_with_pii)
print(f"Original: {content_with_pii}")
print(f"Sanitized: {sanitized}")
print(f"PII found: {len(pii)} items")
assert "[EMAIL]" in sanitized
assert "[PHONE]" in sanitized

# Test 2: Secrets Detection
print("\n=== Test 2: Secrets Detection ===")
content_with_secrets = "api_key = 'sk_live_abc123xyz789'"
secrets = integration._detect_secrets(content_with_secrets)
print(f"Secrets found: {len(secrets)}")
assert len(secrets) > 0

# Test 3: Classification
print("\n=== Test 3: Auto-Classification ===")
tests = [
    ("General Python sorting algorithm", "PUBLIC"),
    ("Our proprietary scoring algorithm", "INTERNAL"),
    ("Patient diagnosis: diabetes", "SENSITIVE"),
]
for content, expected in tests:
    classification = integration._classify_pattern(content, "test")
    print(f"{expected}: {content[:40]}...")
    assert classification == expected

print("\n✓ All manual security tests passed")
```

---

## 🎓 Best Practices

### 1. Principle of Least Privilege

```python
# ❌ DON'T: Load all memory by default
config = ClaudeMemoryConfig(
    enabled=True,
    load_enterprise=True,
    load_user=True,
    load_project=True
)

# ✅ DO: Load only what's needed
config = ClaudeMemoryConfig(
    enabled=True,
    load_enterprise=True,  # Always load security policies
    load_user=False,       # Skip if not needed
    load_project=True      # Project context only
)
```

### 2. Explicit Classification

```python
# ❌ DON'T: Rely solely on auto-classification for SENSITIVE
integration.store_pattern(
    content=healthcare_pattern,
    pattern_type="clinical",
    user_id="doctor@hospital.com",
    auto_classify=True  # Might misclassify
)

# ✅ DO: Explicitly classify SENSITIVE data
classification = input("Confirm classification (PUBLIC/INTERNAL/SENSITIVE): ")
assert classification == "SENSITIVE", "Healthcare data must be SENSITIVE"

integration.store_pattern(
    content=healthcare_pattern,
    pattern_type="clinical",
    user_id="doctor@hospital.com",
    auto_classify=False,
    explicit_classification="SENSITIVE"
)
```

### 3. Regular Audits

```python
# Review audit logs monthly
import json
from datetime import datetime, timedelta

def audit_review(days=30):
    cutoff = datetime.utcnow() - timedelta(days=days)

    with open("/var/log/empathy/audit.jsonl") as f:
        logs = [json.loads(line) for line in f]

    recent = [log for log in logs if datetime.fromisoformat(log["timestamp"]) > cutoff]

    print(f"=== Audit Review (last {days} days) ===")
    print(f"Total events: {len(recent)}")
    print(f"PII detections: {sum(log.get('pii_detected', 0) for log in recent)}")
    print(f"Secrets blocked: {sum(1 for log in recent if log.get('secrets_detected', 0) > 0)}")
    print(f"SENSITIVE patterns: {sum(1 for log in recent if log.get('classification') == 'SENSITIVE')}")

audit_review(30)
```

### 4. Defense in Depth

```python
# Multiple layers of security
class SecureEmpathyFramework:
    def __init__(self):
        # Layer 1: Memory policies (CLAUDE.md)
        self.memory_config = ClaudeMemoryConfig(
            enabled=True,
            load_enterprise=True  # Mandatory security policies
        )

        # Layer 2: LLM with memory integration
        self.llm = LLMExecutor(
            provider="anthropic",
            claude_memory_config=self.memory_config
        )

        # Layer 3: Secure MemDocs integration
        self.memdocs = SecureMemDocsIntegration(self.memory_config)

    async def secure_interact(self, user_id, user_input):
        # Pre-flight checks
        if not self._verify_user_permissions(user_id):
            raise PermissionError("User not authorized")

        # Input sanitization
        sanitized_input, pii = self.memdocs._scrub_pii(user_input)

        # LLM interaction (policies enforced via memory)
        response = await self.llm.interact(
            user_id=user_id,
            user_input=sanitized_input
        )

        # Output sanitization
        sanitized_output, _ = self.memdocs._scrub_pii(response["content"])

        # Audit logging
        self._log_interaction(user_id, sanitized_input, sanitized_output, pii)

        return sanitized_output
```

---

## 📞 Support & Resources

### Documentation
- [Complete Security Architecture](../../SECURE_MEMORY_ARCHITECTURE.md)
- [Privacy Roadmap](../../ENTERPRISE_PRIVACY_INTEGRATION.md)
- [API Reference](../../docs/API_REFERENCE.md)
- [Contributing Guide](../../CONTRIBUTING.md)

### Community
- GitHub Issues: https://github.com/Smart-AI-Memory/empathy/issues
- Discussions: https://github.com/Smart-AI-Memory/empathy/discussions
- Email: attune-ai@smartaimemory.com

### Security
- Report vulnerabilities: security@smartaimemory.com
- HIPAA questions: hipaa-officer@smartaimemory.com
- Compliance: compliance@smartaimemory.com

---

## 📝 License

Apache License 2.0
Copyright 2025 Smart AI Memory

---

**Ready to deploy with enterprise-grade security! 🔒**
