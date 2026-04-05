---
feature: security-audit
depth: reference
generated_at: "2026-04-05T00:00:00+00:00"
source_hash: demo
status: demo
---

# Security Audit Reference

Complete reference for security audit checks — every
pattern detected, how to configure scans, and how to
interpret results.

## All checks

### Code injection (CWE-95)

Detects `eval()`, `exec()`, and `compile()` on data
that could be influenced by external input. Ignores
`ast.literal_eval()` (safe) and scanner test fixtures
(false positives).

### Path traversal (CWE-22)

Flags `open()`, `Path.write_text()`, `Path.read_text()`,
and similar file operations where the path comes from
user input without validation.

### Hardcoded secrets

Scans for patterns matching API keys, tokens, passwords,
and private keys in source code. Distinguishes real
secrets from test fixtures using naming heuristics
(FAKE_, EXAMPLE_, test_).

### SQL injection (CWE-89)

Detects string concatenation and f-strings in SQL
queries. Recommends parameterized queries.

### Command injection (CWE-78)

Flags `subprocess.run()` with `shell=True`, string
interpolation in shell commands, and `os.system()` calls.

### SSRF (CWE-918)

Checks HTTP request functions (`requests.get()`,
`urllib.request.urlopen()`, `aiohttp`) for URLs built
from user input without IP blocklist validation or DNS
resolution checks.

### Weak cryptography

Flags MD5 and SHA1 used for security purposes (hashing
passwords, generating tokens). Ignores non-security uses
like checksums and cache keys.

### Broad exception handling

Identifies bare `except:` and `except Exception:` blocks
that could mask security-relevant errors. Distinguishes
intentional broad catches (marked with `# INTENTIONAL:`
or `# noqa: BLE001`) from accidental ones.

## Output format

Results are grouped by severity:

```markdown
## Security Audit Results

**Score:** 82/100 | **Files:** 47 | **Issues:** 5

### Critical

| File | Line | Issue | CWE |
|------|------|-------|-----|
| executor.py | 89 | eval() on user input | CWE-95 |

### High

| File | Line | Issue | CWE |
|------|------|-------|-----|
| config.py | 203 | Path not validated | CWE-22 |
```

## Scoring

| Range | Rating | Meaning |
|-------|--------|---------|
| 90-100 | Excellent | No critical or high findings |
| 75-89 | Good | Minor issues, no blockers |
| 50-74 | Needs work | High-severity findings present |
| 0-49 | Critical | Critical findings, do not release |

## Configuration

### Ignoring findings

Add inline comments to suppress specific findings:

```python
result = eval(trusted_input)  # noqa: S307
```

Or exclude paths in your project configuration:

```yaml
security_audit:
  exclude:
    - "tests/fixtures/**"
    - "benchmarks/**"
```

## After the audit

| Goal | Next step |
|------|-----------|
| Fix critical issues | Generate patches for critical findings |
| Prevent regressions | Write security tests for flagged files |
| Deeper scan | Run a focused deep scan on one directory |
| Track over time | Compare with previous audit results |
| CI integration | Export results as JSON for your pipeline |
