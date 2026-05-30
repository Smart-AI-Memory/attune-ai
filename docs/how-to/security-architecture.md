---
description: Security architecture in attune — PII scrubbing, secrets detection, audit logging, path validation, and the SecurityAuditWorkflow.
---

# Security Architecture

Attune's security surface is a set of composable primitives in
`attune.security` (re-exported from `attune.memory.security`) plus an
Agent-SDK-backed `SecurityAuditWorkflow` that scans a codebase. This
page describes what actually ships in the source tree.

---

## Overview

The security module exposes four primitive families and one workflow:

1. **PII scrubbing** — `PIIScrubber`, `PIIPattern`, `PIIDetection`.
2. **Secrets detection** — `SecretsDetector`, `detect_secrets()`,
   `SecretType`, `SecretDetection`.
3. **Audit logging** — `AuditLogger`, `AuditEvent`,
   `SecurityViolation`, `Severity`.
4. **Path validation** — `_validate_file_path()` (private helper used
   by the CLI to block path traversal).
5. **Workflow** — `SecurityAuditWorkflow` runs a multi-subagent audit
   against a directory or file.

All public symbols are importable from either
`attune.security` or `attune.memory.security` — the former re-exports
the latter for convenience.

```python
from attune.security import (
    PIIScrubber,
    SecretsDetector,
    AuditLogger,
    AuditEvent,
    SecurityViolation,
    Severity,
    detect_secrets,
)
```

---

## PII Protection

`PIIScrubber` detects PII in text and returns a tuple of
`(sanitized_text, detections)`. Each detection is a `PIIDetection`
dataclass with the matched text, position, replacement token, and
confidence.

### Built-in patterns

`PIIScrubber._init_default_patterns()` ships nine patterns:

| Pattern name  | Replacement     | Notes                                       |
|---------------|-----------------|---------------------------------------------|
| `email`       | `[EMAIL]`       | RFC 5322 simplified                         |
| `ssn`         | `[SSN]`         | Excludes invalid area numbers (000/666/9xx) |
| `phone`       | `[PHONE]`       | US + international formats                  |
| `credit_card` | `[CC]`          | Visa / MC / Amex / Discover                 |
| `ipv4`        | `[IP]`          | Octet-validated                             |
| `ipv6`        | `[IP]`          | Simplified IPv6                             |
| `address`     | `[ADDRESS]`     | US street address heuristic                 |
| `name`        | `[NAME]`        | Title-prefixed names; **disabled by default** (high false-positive rate) |
| `mrn`         | `[MRN]`         | Medical Record Number                       |
| `patient_id`  | `[PATIENT_ID]`  | Patient identifier (`Patient ID:` / `PID-`) |

### Usage

```python
from attune.security import PIIScrubber

scrubber = PIIScrubber()  # name detection disabled by default

text = "Email user@example.com or call 555-123-4567 (MRN: 1234567)."
sanitized, detections = scrubber.scrub(text)

print(sanitized)
# "Email [EMAIL] or call [PHONE] (MRN: [MRN])."

for d in detections:
    print(d.pii_type, d.replacement, d.confidence)
```

`PIIDetection.to_audit_safe_dict()` returns a dict that omits the
matched value — safe to forward to an audit log.

### Custom patterns

```python
scrubber.add_custom_pattern(
    name="employee_id",
    pattern=r"EMP-\d{6}",
    replacement="[EMPLOYEE_ID]",
    confidence=1.0,
    description="Company employee identifier",
)
```

Default patterns can be disabled with `disable_pattern(name)` and
re-enabled with `enable_pattern(name)`. Custom patterns are removed
with `remove_custom_pattern(name)`.

---

## Secrets Detection

`SecretsDetector` scans content for hardcoded credentials using
compiled regex patterns plus optional Shannon-entropy fallback. The
detector **never stores the matched secret value** — only metadata
(type, severity, line/column, redacted context snippet).

### Supported secret types

From `SecretType` (see `secrets_types.py`):

- API keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `AWS_ACCESS_KEY`,
  `AWS_SECRET_KEY`, `GITHUB_TOKEN`, `SLACK_TOKEN`, `STRIPE_KEY`,
  `GENERIC_API_KEY`
- Passwords: `PASSWORD`, `BASIC_AUTH`
- Private keys: `RSA_PRIVATE_KEY`, `SSH_PRIVATE_KEY`,
  `EC_PRIVATE_KEY`, `PGP_PRIVATE_KEY`, `TLS_CERTIFICATE_KEY`
- Tokens: `JWT_TOKEN`, `OAUTH_TOKEN`, `BEARER_TOKEN`
- Databases: `DATABASE_URL`, `CONNECTION_STRING`
- Heuristic: `HIGH_ENTROPY_STRING`

### Severity model

`Severity` is an enum with four levels:

| Level    | Typical members                                        |
|----------|--------------------------------------------------------|
| CRITICAL | Private keys, AWS access/secret keys                   |
| HIGH     | API keys (Anthropic, OpenAI, GitHub, Slack, Stripe), passwords, database URLs |
| MEDIUM   | OAuth tokens, JWT tokens, bearer tokens                |
| LOW      | High-entropy strings (heuristic catch)                 |

### Usage

```python
from attune.security import SecretsDetector, detect_secrets

# One-shot:
detections = detect_secrets(source_code)

# Reusable instance with custom thresholds:
detector = SecretsDetector(
    enable_entropy_analysis=True,
    entropy_threshold=4.5,
    min_entropy_length=20,
)
detections = detector.detect(source_code)

for d in detections:
    print(
        d.secret_type.value,
        d.severity.value,
        f"line {d.line_number} col {d.column_start}",
        d.context_snippet,  # secret value replaced with [REDACTED]
    )
```

`SecretDetection.to_dict()` is JSON-safe. Custom patterns are added
via `detector.add_custom_pattern(name, pattern, severity)` where
`severity` is `"critical" | "high" | "medium" | "low"`.

---

## Audit Logging

`AuditLogger` writes append-only JSON-Lines (`.jsonl`) events to a
log directory, with optional size-based rotation and age-based
cleanup. The constructor accepts:

```python
AuditLogger(
    log_dir=None,                  # defaults to platform_utils.get_default_log_dir()
    log_filename="audit.jsonl",
    max_file_size_mb=100,
    retention_days=365,
    enable_rotation=True,
    enable_console_logging=False,
)
```

The log directory is created with `0o700` permissions; on init
failure it falls back to `./logs`.

### Event types

Logging methods on `AuditLogger` (mixed in from
`AuditLogMethodsMixin`):

- `log_llm_request(user_id, empathy_level, provider, model, memory_sources, pii_count=0, secrets_count=0, ...)`
  — records an LLM API call with per-request size, duration, and
  PII/secret counts.
- `log_pattern_store(user_id, pattern_id, pattern_type, classification, pii_scrubbed=0, secrets_detected=0, ...)`
  — records storage of a MemDocs pattern.
- `log_pattern_retrieve(user_id, pattern_id, classification, access_granted=True, ...)`
  — records pattern retrieval and unauthorized-access attempts.
- `log_security_violation(user_id, violation_type, severity, details, ...)`
  — records a security policy violation.

`log_llm_request` and `log_pattern_store` automatically escalate to
`log_security_violation` when `secrets_count > 0` or when sensitive
classifications are stored unencrypted.

### Event shape

Every event is an `AuditEvent` dataclass:

```python
AuditEvent(
    event_id="evt_<12-hex>",        # auto-generated
    timestamp="<UTC ISO-8601>",     # auto-generated
    version="1.0",
    event_type="llm_request",       # or store_pattern / retrieve_pattern / security_violation
    user_id="...",
    session_id="...",
    status="success",               # or failed / blocked
    error="",
    data={...},                     # event-specific fields
)
```

`to_dict()` flattens `data` into the top level for easier querying.

### Querying logs

`AuditLogger.query()` (from `AuditQueryMixin`) supports filtering by
`event_type`, `user_id`, `status`, date range, and arbitrary
field/value filters:

```python
events = logger.query(
    event_type="llm_request",
    user_id="user@example.com",
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 1, 31),
    limit=1000,
)
```

---

## Path Validation

> **Internal API.** The `_validate_file_path` helper has a leading
> underscore — treat it as internal. The signature and behavior may
> change between releases. It is documented here because it is the
> single source of truth for path-traversal defense across the
> codebase; prefer calling it via the higher-level workflows rather
> than depending on its signature directly.

`attune.security.path_validation._validate_file_path(path, allowed_dir=None)`
is the internal guard the CLI uses to block path-traversal attacks
(CWE-22) before running workflows against user-supplied paths.

- Rejects empty paths, non-string paths, and paths containing null
  bytes.
- Resolves the path with `Path.resolve()` and (optionally) asserts
  it lies under `allowed_dir`.
- Refuses to operate on platform system directories
  (e.g. `/etc`, `/private/etc`, `/usr/bin`, `/bin` on Unix;
  `C:\Windows\System32`, `Program Files` on Windows).

The leading underscore is intentional: this is a private primitive
used internally by `attune.cli_commands.workflow_commands.cmd_workflow_run`,
not a public API. Callers outside the CLI should not import it.

---

## SecurityAuditWorkflow

`SecurityAuditWorkflow` (slug: `security-audit`) is the public,
SDK-native security audit. It delegates to four Claude Agent SDK
subagents and synthesizes their findings into a `WorkflowResult`:

- **vuln-scanner** — injection flaws, `eval`/`exec`, XSS, path
  traversal, command injection, insecure deserialization.
- **secret-detector** — hardcoded credentials, API keys, tokens,
  private keys, database credentials.
- **auth-reviewer** — missing auth checks, broken access control,
  insecure session management, privilege-escalation risks.
- **remediation-planner** — prioritized fix plan grouped by effort.

### Run from the CLI

```bash
attune workflow run security-audit --path src/
attune workflow run security-audit --path src/ --depth deep
```

Supported `--depth` values are `quick`, `standard` (default), and
`deep`. Depth maps to a `max_turns` budget for the orchestrator
(10 / 20 / 40 respectively) and engages extended thinking on `deep`.

### Run from Python

```python
import asyncio
from attune.workflows.security_audit import SecurityAuditWorkflow

async def run_audit():
    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(path="src/", depth="standard")
    print(result.final_output)
    print(result.summary)

asyncio.run(run_audit())
```

### Output

The orchestrator's synthesis covers three sections —
**Summary** (a security score 0–100 + 2-3 sentence executive
summary), **Security** (consolidated findings by severity), and
**Suggestions** (prioritized remediation). Per-subagent transcripts
are recovered separately and appended under
`## Subagent findings` so the orchestrator's summary cannot silently
drop their detail.

The returned `WorkflowResult` carries `final_output`, `summary`,
`success`, `stages`, `cost_report`, `metadata` (with the resolved
path, depth, and subagent transcripts), plus optional `error` /
`error_type` / `transient` fields when the SDK call fails.

---

## See also

- [Wizards](../reference/wizards.md) — the wizard runtime; the `security` builtin delegates to `SecurityAuditWorkflow`.
- [CLI Reference](../reference/cli-reference.md) — `attune workflow run security-audit` invocation and flags.
