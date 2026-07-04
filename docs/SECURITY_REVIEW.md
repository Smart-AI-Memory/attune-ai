---
description: Security Review - Bandit Findings: **Date:** 2026-01-26 **Reviewer:** Automated code quality review **Tool:** Bandit v1.8.6 --- ## Summary **2 medium-severity f
---

# Security Review - Bandit Findings

**Date:** 2026-01-26
**Reviewer:** Automated code quality review
**Tool:** Bandit v1.8.6

---

## Summary

**2 medium-severity findings identified - BOTH ARE FALSE POSITIVES**

The Bandit static analysis tool flagged 2 security issues, but upon manual review, both are false positives. The code implements proper security controls.

---

## Finding 1: B104 - Hardcoded Bind to All Interfaces

**Status:** ✅ FALSE POSITIVE
**Severity:** Medium
**Confidence:** Medium
**Location:** `src/attune/monitoring/alerts.py:88`

### Bandit Report
```
Issue: [B104:hardcoded_bind_all_interfaces] Possible binding to all interfaces.
CWE: CWE-605 (https://cwe.mitre.org/data/definitions/605.html)
```

### Code Context
```python
# Line 85-94
blocked_hosts = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",  # ← Flagged by Bandit
    "::1",
    "[::1]",
    "169.254.169.254",  # AWS metadata
    "metadata.google.internal",  # GCP metadata
    "instance-data",  # Azure metadata pattern
}
```

### Analysis

**This is a blocklist, not a bind address.**

The code defines a set of **prohibited webhook destinations** to prevent SSRF (Server-Side Request Forgery) attacks. The string `"0.0.0.0"` appears in a list of addresses that are **explicitly blocked**, not as a server bind configuration.

**Security impact:** POSITIVE - This code **prevents** SSRF by blocking requests to `0.0.0.0`.

### Recommendation

✅ **No action required**

To suppress this false positive in future scans, add a Bandit comment:
```python
blocked_hosts = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",  # nosec B104 - blocklist for SSRF prevention, not bind address
    "::1",
    ...
}
```

---

## Finding 2: B310 - URL Open Without Scheme Validation

**Status:** ✅ FALSE POSITIVE (with proper validation)
**Severity:** Medium
**Confidence:** High
**Location:** `src/attune/monitoring/alerts.py:777`

### Bandit Report
```
Issue: [B310:blacklist] Audit url open for permitted schemes.
       Allowing use of file:/ or custom schemes is often unexpected.
CWE: CWE-22 (https://cwe.mitre.org/data/definitions/22.html)
```

### Code Context
```python
# Line 726
validated_url = _validate_webhook_url(alert.webhook_url)

# Line 770-777
req = urllib.request.Request(
    validated_url,
    data=data,
    headers={"Content-Type": "application/json"},
)

try:
    with urllib.request.urlopen(req, timeout=10) as response:  # ← Flagged by Bandit
        ...
```

### Analysis

**The URL is validated before use through `_validate_webhook_url()`.**

The validation function (lines 56-120) implements comprehensive security checks:

1. **Scheme validation (line 74-77):**
   ```python
   if parsed.scheme not in ("http", "https"):
       raise ValueError(
           f"Invalid scheme '{parsed.scheme}'. Only http and https allowed for webhooks."
       )
   ```

2. **Hostname validation (line 80-82):**
   ```python
   hostname = parsed.hostname
   if not hostname:
       raise ValueError("Webhook URL must contain a valid hostname")
   ```

3. **SSRF prevention (line 85-98):**
   - Blocks localhost addresses (127.0.0.1, ::1, 0.0.0.0)
   - Blocks cloud metadata services (AWS, GCP, Azure)
   - Blocks private IP ranges (10.x, 172.16-31.x, 192.168.x)

4. **Port restrictions (line 106-115):**
   - Blocks common internal service ports (Redis 6379, PostgreSQL 5432, etc.)

**Security impact:** POSITIVE - The code properly prevents:
- File scheme access (file://)
- SSRF attacks via localhost/private IPs
- Access to cloud metadata services
- Access to internal service ports

### Recommendation

✅ **Code is secure - validation is comprehensive**

To suppress this warning, add a Bandit comment explaining the validation:
```python
# nosec B310 - URL validated by _validate_webhook_url() - only http/https allowed, SSRF protected
with urllib.request.urlopen(req, timeout=10) as response:
    ...
```

---

## Overall Security Posture

**Assessment:** ✅ EXCELLENT

The `alerts.py` module demonstrates strong security practices:
- Comprehensive input validation
- SSRF attack prevention
- Allowlist approach (only http/https schemes)
- Protection against cloud metadata access
- Private IP range blocking
- Internal port blocking

**No security vulnerabilities identified in this review.**

---

## Recommendations for Future

1. **Add `# nosec` comments** to suppress false positives in CI/CD
2. **Document validation functions** in security documentation
3. **Add unit tests** for SSRF prevention edge cases (if not already present)
4. **Consider adding rate limiting** for webhook deliveries

---

## Related Files

- Security implementation: `src/attune/monitoring/alerts.py`
- Security standards: `.claude/rules-tail/attune/coding-standards-index.md`
- Security policy: `SECURITY.md`

---

**Review Status:** COMPLETE
**Action Required:** None (false positives)
**Next Review:** After significant webhook/alert changes
