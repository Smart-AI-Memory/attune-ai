"""Security Audit Pattern Constants.

OWASP-inspired vulnerability detection patterns and filter lists.
Extracted from security_audit.py for maintainability.

Contains:
- SKIP_DIRECTORIES: Dirs to skip during scanning
- DETECTION_PATTERNS: Patterns indicating detection code (not vulnerable)
- FAKE_CREDENTIAL_PATTERNS: Known fake/test credential patterns
- SECURITY_EXAMPLE_PATHS: Paths containing security examples/tests
- TEST_FIXTURE_PATTERNS: Test fixture data patterns
- TEST_FILE_PATTERNS: Test file path patterns
- SECURITY_PATTERNS: OWASP Top 10 vulnerability patterns

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

# Directories to skip during scanning (build artifacts, third-party code)
SKIP_DIRECTORIES = {
    ".git",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".next",  # Next.js build output
    "dist",
    "build",
    ".tox",
    "site",  # MkDocs output
    "ebook-site",
    "website",  # Website build artifacts
    "anthropic-cookbook",  # Third-party examples
    ".eggs",
    "*.egg-info",
    "htmlcov",  # Coverage report artifacts
    "htmlcov_logging",  # Coverage report artifacts
    ".coverage",  # Coverage data
    "vscode-extension",  # VSCode extension code (separate security review)
    "vscode-memory-panel",  # VSCode panel code
}

# Patterns that indicate a line is DETECTION code, not vulnerable code
# These help avoid false positives when scanning security tools
DETECTION_PATTERNS = [
    r'["\']eval\s*\(["\']',  # String literal like "eval(" (detection, not execution)
    r'["\']exec\s*\(["\']',  # String literal like "exec(" (detection, not execution)
    r"in\s+content",  # Pattern detection like "eval(" in content
    r"re\.compile",  # Regex compilation for detection
    r"\.finditer\(",  # Regex matching for detection
    r"\.search\(",  # Regex searching for detection
]

# Known fake/test credential patterns to ignore
FAKE_CREDENTIAL_PATTERNS = [
    r"EXAMPLE",  # AWS example keys
    r"FAKE",
    r"TEST",
    r"your-.*-here",
    r'"your-key"',  # Placeholder key
    r"abc123xyz",
    r"\.\.\.",  # Placeholder with ellipsis
    r"test-key",
    r"mock",
    r'"hardcoded_secret"',  # Literal example text
    r'"secret"$',  # Generic "secret" as value
    r'"secret123"',  # Test password
    r'"password"$',  # Generic password as value
    r"_PATTERN",  # Pattern constants
    r"_EXAMPLE",  # Example constants
]

# Files/paths that contain security examples/tests (not vulnerabilities)
SECURITY_EXAMPLE_PATHS = [
    "owasp_patterns.py",
    "vulnerability_scanner.py",
    "test_security",
    "test_secrets",
    "test_owasp",
    "secrets_detector.py",  # Security tool with pattern definitions
    "pii_scrubber.py",  # Privacy tool
    "secure_memdocs",  # Secure storage module
    "/security/",  # Security modules
    "/benchmarks/",  # Benchmark files with test fixtures
    "benchmark_",  # Benchmark files (e.g., benchmark_caching.py)
    "phase_2_setup.py",  # Setup file with educational patterns
]

# Patterns indicating test fixture data (code written to temp files for testing)
TEST_FIXTURE_PATTERNS = [
    r"SECURITY_TEST_FILES\s*=",  # Dict of test fixture code
    r"write_text\s*\(",  # Writing test data to temp files
    r"# UNSAFE - DO NOT USE",  # Educational comments showing bad patterns
    r"# SAFE -",  # Educational comments showing good patterns
    r"# INJECTION RISK",  # Educational markers
    r"pragma:\s*allowlist\s*secret",  # Explicit allowlist marker
]

# Test file patterns - findings here are informational, not critical
TEST_FILE_PATTERNS = [
    r"[/\\]tests[/\\]",
    r"[/\\]test_",
    r"_test\.py$",
    r"_demo\.py$",
    r"_example\.py$",
    r"[/\\]examples[/\\]",
    r"[/\\]demo",
    r"coach[/\\]vscode-extension",  # Example VSCode extension
]

# Common security vulnerability patterns (OWASP Top 10 inspired)
SECURITY_PATTERNS = {
    "sql_injection": {
        "patterns": [
            r'execute\s*\(\s*["\'].*%s',
            r'cursor\.execute\s*\(\s*f["\']',
            r"\.format\s*\(.*\).*execute",
        ],
        "severity": "critical",
        "owasp": "A03:2021 Injection",
    },
    "xss": {
        "patterns": [
            r"innerHTML\s*=",
            r"dangerouslySetInnerHTML",
            r"document\.write\s*\(",
        ],
        "severity": "high",
        "owasp": "A03:2021 Injection",
    },
    "hardcoded_secret": {
        "patterns": [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][A-Za-z0-9]{20,}["\']',
        ],
        "severity": "critical",
        "owasp": "A02:2021 Cryptographic Failures",
    },
    "insecure_random": {
        "patterns": [
            r"random\.\w+\s*\(",
            r"Math\.random\s*\(",
        ],
        "severity": "medium",
        "owasp": "A02:2021 Cryptographic Failures",
    },
    "path_traversal": {
        "patterns": [
            r"open\s*\([^)]*\+[^)]*\)",
            r"readFile\s*\([^)]*\+[^)]*\)",
        ],
        "severity": "high",
        "owasp": "A01:2021 Broken Access Control",
    },
    "command_injection": {
        "patterns": [
            r"subprocess\.\w+\s*\([^)]*shell\s*=\s*True",
            r"os\.system\s*\(",
            r"eval\s*\(",
            r"exec\s*\(",
        ],
        "severity": "critical",
        "owasp": "A03:2021 Injection",
    },
}
