"""Mock LLM backend for benchmark development.

Returns canned responses that exercise the XmlResponseParser without
requiring API calls. Provides both XML and plain-text response variants.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import random
from typing import Any


class MockLLMBackend:
    """Mock LLM backend returning canned responses.

    XML-enabled responses return proper XML structure; plain responses
    return unstructured text. Simulates realistic token counts and latency.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    async def call(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Return a mock response based on prompt content.

        Detects whether the prompt is XML-structured (contains <request>)
        and returns an appropriately formatted response.
        """
        is_xml_prompt = "<request>" in prompt or "<role>" in prompt
        is_security = "security" in prompt.lower() or "vulnerabilit" in prompt.lower()
        is_review = "review" in prompt.lower() or "code quality" in prompt.lower()
        is_perf = "performance" in prompt.lower() or "bottleneck" in prompt.lower()

        if is_xml_prompt:
            if is_security:
                text = _MOCK_SECURITY_XML
            elif is_perf:
                text = _MOCK_PERF_XML
            else:
                text = _MOCK_REVIEW_XML
        else:
            if is_security:
                text = _MOCK_SECURITY_PLAIN
            elif is_perf:
                text = _MOCK_PERF_PLAIN
            else:
                text = _MOCK_REVIEW_PLAIN

        # Simulate realistic token counts
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(text) // 4
        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }


# ---------------------------------------------------------------------------
# Mock XML responses (parseable by XmlResponseParser)
# ---------------------------------------------------------------------------

_MOCK_SECURITY_XML = """\
<response>
<summary>Found 2 security vulnerabilities requiring immediate attention.</summary>
<findings>
  <finding>
    <severity>critical</severity>
    <title>Unsafe eval() on user input</title>
    <location>line 3, function calculate</location>
    <details>The eval() function executes arbitrary Python code from user input, enabling remote code execution.</details>
    <fix>Use ast.literal_eval() for safe evaluation of literal expressions, or implement a whitelist-based expression parser.</fix>
  </finding>
  <finding>
    <severity>critical</severity>
    <title>Shell injection via subprocess</title>
    <location>line 8, function run_command</location>
    <details>Using shell=True with user-controlled input allows arbitrary command execution.</details>
    <fix>Use subprocess.run() with a list of arguments and shell=False. Validate command against an allowlist.</fix>
  </finding>
</findings>
<remediation-checklist>
  <item>Replace eval() with ast.literal_eval()</item>
  <item>Remove shell=True from subprocess calls</item>
  <item>Add input validation for all user-controlled parameters</item>
</remediation-checklist>
</response>"""

_MOCK_REVIEW_XML = """\
<response>
<summary>Code review identified 2 issues: missing error handling and bare except clause.</summary>
<verdict>request_changes</verdict>
<findings>
  <finding>
    <severity>high</severity>
    <title>Missing error handling in file operations</title>
    <location>line 2, function process_data</location>
    <details>open() call has no error handling for FileNotFoundError or PermissionError.</details>
    <fix>Wrap in try/except with specific exception types and proper logging.</fix>
  </finding>
  <finding>
    <severity>high</severity>
    <title>Bare except clause masks all errors</title>
    <location>line 11, function risky_operation</location>
    <details>Bare except: catches KeyboardInterrupt and SystemExit, making debugging impossible.</details>
    <fix>Catch specific exceptions (e.g., ValueError, IOError) and log the error.</fix>
  </finding>
</findings>
<suggestions>
  <item>Add type hints to all function parameters</item>
  <item>Use context manager for file operations</item>
</suggestions>
<remediation-checklist>
  <item>Add try/except with specific exceptions to process_data</item>
  <item>Replace bare except with specific exception handling</item>
  <item>Add type hints to function signatures</item>
</remediation-checklist>
</response>"""

_MOCK_PERF_XML = """\
<response>
<summary>Found 2 performance issues: N+1 query pattern and unbounded file read.</summary>
<performance-score>45</performance-score>
<findings>
  <finding>
    <severity>high</severity>
    <title>N+1 query pattern</title>
    <location>line 4-7, function get_users_with_orders</location>
    <details>Executing a separate query per user creates O(n) database round-trips. For 1000 users, this means 1001 queries instead of 2.</details>
    <fix>Use a JOIN query: SELECT users.*, orders.* FROM users LEFT JOIN orders ON users.id = orders.user_id</fix>
  </finding>
  <finding>
    <severity>medium</severity>
    <title>Unbounded file read into memory</title>
    <location>line 12, function process_large_file</location>
    <details>readlines() loads entire file into memory. For large files this causes OOM errors.</details>
    <fix>Use line-by-line iteration: for line in f: instead of f.readlines()</fix>
  </finding>
</findings>
<remediation-checklist>
  <item>Replace per-user queries with JOIN</item>
  <item>Use streaming file processing</item>
</remediation-checklist>
</response>"""


# ---------------------------------------------------------------------------
# Mock plain text responses (may or may not parse as XML)
# ---------------------------------------------------------------------------

_MOCK_SECURITY_PLAIN = """\
## Security Audit Results

I found 2 critical security vulnerabilities:

### 1. Unsafe eval() on user input (Critical)
**Location:** line 3, function calculate
The eval() function executes arbitrary Python code from user input. An attacker could run `eval("__import__('os').system('rm -rf /')")`.

**Fix:** Use ast.literal_eval() for safe literal evaluation.

### 2. Shell injection via subprocess (Critical)
**Location:** line 8, function run_command
Using shell=True with user input allows arbitrary command execution.

**Fix:** Use subprocess.run() with a list and shell=False.

### Remediation Checklist
- [ ] Replace eval() with ast.literal_eval()
- [ ] Remove shell=True from subprocess calls
- [ ] Add input validation
"""

_MOCK_REVIEW_PLAIN = """\
## Code Review

**Verdict:** Request Changes

### Issues Found

1. **Missing error handling** (High) - line 2, process_data
   The open() call has no error handling. Add try/except for FileNotFoundError.

2. **Bare except clause** (High) - line 11, risky_operation
   Bare except: catches everything including KeyboardInterrupt. Use specific exceptions.

### Suggestions
- Add type hints to all functions
- Use context managers for file operations

### Checklist
- [ ] Add error handling to process_data
- [ ] Replace bare except with specific exceptions
- [ ] Add type hints
"""

_MOCK_PERF_PLAIN = """\
## Performance Audit

**Score:** 45/100

### Issues Found

1. **N+1 Query Pattern** (High) - lines 4-7, get_users_with_orders
   Each user triggers a separate query. For 1000 users = 1001 queries.
   Fix: Use a JOIN query instead.

2. **Unbounded File Read** (Medium) - line 12, process_large_file
   readlines() loads entire file into memory.
   Fix: Iterate line by line.

### Checklist
- [ ] Replace per-user queries with JOIN
- [ ] Use streaming file processing
"""
