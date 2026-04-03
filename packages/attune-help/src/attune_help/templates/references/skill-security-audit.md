---
type: reference
subtype: procedural
name: skill-security-audit
category: skill
tags: [security, skill, plugin, reference]
source: plugin/skills/security-audit/SKILL.md
---

# Security Audit Reference

Complete reference for the security audit skill —
every check it runs, how to configure it, and how to
interpret and act on results.

## Invocation

```
/security-audit <path>
```

Or natural language:

```
scan src/ for vulnerabilities
check my code for security issues
run a security audit on the auth module
```

## Depth levels

The skill runs on your Claude subscription — no API key
or additional cost. You control how thorough the scan is:

| Depth | What you get |
|-------|-------------|
| **Quick** | Surface scan — eval/exec, obvious secrets, fast |
| **Standard** | Full pattern matching with severity ratings (default) |
| **Deep** | Multi-pass review with OWASP mapping and fix suggestions |

Set depth with natural language:

```
deep security audit on src/
quick scan of config.py
```

## All checks

### Code injection (CWE-95)

Detects `eval()`, `exec()`, and `compile()` on data
that could be influenced by external input. Ignores
`ast.literal_eval()` (safe) and scanner test fixtures
(false positives).

### Path traversal (CWE-22)

Flags `open()`, `Path.write_text()`, `Path.read_text()`,
and similar file operations where the path comes from
user input without validation via `_validate_file_path()`
or equivalent.

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
from user input without IP blocklist validation or
DNS resolution checks.

### Weak cryptography

Flags MD5 and SHA1 used for security purposes (hashing
passwords, generating tokens). Ignores non-security uses
(checksums, cache keys).

### Broad exception handling

Identifies bare `except:` and `except Exception:` blocks
that could mask security-relevant errors. Distinguishes
intentional broad catches (marked with `# INTENTIONAL:`
or `# noqa: BLE001`) from accidental ones.

## Output format

Results are presented as a severity-grouped table:

```markdown
## Security Audit Results

**Score:** 82/100 | **Files Scanned:** 47 | **Issues:** 5

### Critical

| File | Line | Issue | CWE |
|------|------|-------|-----|
| [executor.py:89](src/hooks/executor.py#L89) | 89 | eval() on user input | CWE-95 |

### High

| File | Line | Issue | CWE |
|------|------|-------|-----|
| [config.py:203](src/config.py#L203) | 203 | Path not validated | CWE-22 |

### Medium

| File | Line | Issue | CWE |
|------|------|-------|-----|
| [session.py:112](src/auth/session.py#L112) | 112 | Broad exception | BLE001 |
```

**Scoring:**

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
result = eval(trusted_input)  # noqa: S307 — input is validated upstream
```

Or exclude paths in your project configuration:

```yaml
# attune.config.yml
security_audit:
  exclude:
    - "tests/fixtures/**"
    - "benchmarks/**"
```

## After the audit

| Goal | What to say |
|------|-------------|
| Fix critical issues | "fix the critical findings" |
| Generate regression tests | "write security tests for the flagged files" |
| Deeper scan of one area | "deep scan src/auth/" |
| Track findings over time | "compare with last audit" |
| Export for CI | "export results as JSON" |

## Want to learn more?

- Say **"what is security audit?"** to go back to the overview
- Say **"how do I run a security audit?"** for the step-by-step guide
- Say **"review my code"** for a broader code quality review
- Say **"tell me about bug prediction"** to predict where failures happen
