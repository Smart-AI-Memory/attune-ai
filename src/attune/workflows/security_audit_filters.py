"""Security Audit Filter Methods.

Mixin providing false-positive filtering for security scan results.
Extracted from security_audit.py for maintainability.

Contains:
- SecurityFilterMixin: Filter methods for detection code, fake credentials,
  documentation, SQL parameterization, and safe random usage

Expected attributes on the host class: (none - uses constants from patterns module)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re

from .security_audit_patterns import (
    DETECTION_PATTERNS,
    FAKE_CREDENTIAL_PATTERNS,
)


class SecurityFilterMixin:
    """Mixin providing false-positive filtering for security scan results."""

    def _analyze_finding(self, finding: dict) -> str:
        """Generate analysis context for a finding."""
        vuln_type = finding.get("type", "")
        analyses = {
            "sql_injection": "Potential SQL injection. Verify parameterized input.",
            "xss": "Potential XSS vulnerability. Check output escaping.",
            "hardcoded_secret": "Hardcoded credential. Use env vars or secrets manager.",
            "insecure_random": "Insecure random. Use secrets module instead.",
            "path_traversal": "Potential path traversal. Validate file paths.",
            "command_injection": "Potential command injection. Avoid shell=True.",
        }
        return analyses.get(vuln_type, "Review for security implications.")

    def _get_remediation_action(self, finding: dict) -> str:
        """Generate specific remediation action for a finding."""
        actions = {
            "sql_injection": "Use parameterized queries or ORM. Never interpolate user input.",
            "xss": "Use framework's auto-escaping. Sanitize user input.",
            "hardcoded_secret": "Move to env vars or use a secrets manager.",
            "insecure_random": "Use secrets.token_hex() or secrets.randbelow().",
            "path_traversal": "Use os.path.realpath() and validate paths.",
            "command_injection": "Use subprocess with shell=False and argument lists.",
        }
        return actions.get(finding.get("type", ""), "Apply security best practices.")

    def _is_detection_code(self, line_content: str, match_text: str) -> bool:
        """Check if a match is actually detection/scanning code, not a vulnerability.

        This prevents false positives when scanning security tools that contain
        patterns like 'if "eval(" in content:' which are detecting vulnerabilities,
        not introducing them.
        """
        # Check if the line contains detection patterns
        for pattern in DETECTION_PATTERNS:
            if re.search(pattern, line_content, re.IGNORECASE):
                return True

        # Check if the match is inside a string literal used for comparison
        # e.g., 'if "eval(" in content:' or 'pattern = r"eval\("'
        if f'"{match_text.strip()}"' in line_content or f"'{match_text.strip()}'" in line_content:
            return True

        return False

    def _is_fake_credential(self, match_text: str) -> bool:
        """Check if a matched credential is obviously fake/for testing.

        This prevents false positives for test fixtures using patterns like
        'AKIAIOSFODNN7EXAMPLE' (AWS official example) or 'test-key-not-real'.
        """
        for pattern in FAKE_CREDENTIAL_PATTERNS:
            if re.search(pattern, match_text, re.IGNORECASE):
                return True
        return False

    def _is_documentation_or_string(self, line_content: str, match_text: str) -> bool:
        """Check if a command injection match is in documentation or string literals.

        This prevents false positives for:
        - Docstrings describing security issues
        - String literals containing example vulnerable code
        - Comments explaining vulnerabilities
        """
        line = line_content.strip()

        # Check if line is a comment or documentation
        if (
            line.startswith("#")
            or line.startswith("//")
            or line.startswith("*")
            or line.startswith("-")
        ):
            return True

        # Check if inside a docstring (triple quotes)
        if '"""' in line or "'''" in line:
            return True

        # Check if the match is inside a string literal being defined
        # e.g., 'pattern = r"eval\("' or '"eval(" in content'
        string_patterns = [
            r'["\'].*' + re.escape(match_text.strip()[:10]) + r'.*["\']',  # Inside quotes
            r'r["\'].*' + re.escape(match_text.strip()[:10]),  # Raw string
            r'=\s*["\']',  # String assignment
        ]
        for pattern in string_patterns:
            if re.search(pattern, line):
                return True

        # Check for common documentation patterns
        doc_indicators = [
            "example",
            "vulnerable",
            "insecure",
            "dangerous",
            "pattern",
            "detect",
            "scan",
            "check for",
            "look for",
        ]
        line_lower = line.lower()
        if any(ind in line_lower for ind in doc_indicators):
            return True

        return False

    def _is_safe_sql_parameterization(
        self,
        line_content: str,
        match_text: str,
        file_content: str,
    ) -> bool:
        """Check if SQL query uses safe parameterization despite f-string usage.

        Phase 2 Enhancement: Detects safe patterns like:
        - placeholders = ",".join("?" * len(ids))
        - cursor.execute(f"... IN ({placeholders})", ids)

        This prevents false positives for the SQLite-recommended pattern
        of building dynamic placeholder strings.

        Args:
            line_content: The line containing the match (may be incomplete for multi-line)
            match_text: The matched text
            file_content: Full file content for context analysis

        Returns:
            True if this is safe parameterized SQL, False otherwise

        """
        # Get the position of the match in the full file content
        match_pos = file_content.find(match_text)
        if match_pos == -1:
            # Try to find cursor.execute
            match_pos = file_content.find("cursor.execute")
            if match_pos == -1:
                return False

        # Extract a larger context (next 200 chars after match)
        context = file_content[match_pos : match_pos + 200]

        # Also get lines before the match for placeholder detection
        lines_before = file_content[:match_pos].split("\n")
        recent_lines = lines_before[-10:] if len(lines_before) > 10 else lines_before

        # Pattern 1: Check if this is a placeholder-based parameterized query
        # Look for: cursor.execute(f"... IN ({placeholders})", params)
        if "placeholders" in context or any("placeholders" in line for line in recent_lines[-5:]):
            # Check if context has both f-string and separate parameters
            # Pattern: f"...{placeholders}..." followed by comma and params
            if re.search(r'f["\'][^"\']*\{placeholders\}[^"\']*["\']\s*,\s*\w+', context):
                return True  # Safe - has separate parameters

            # Also check if recent lines built the placeholders
            for prev_line in reversed(recent_lines):
                if "placeholders" in prev_line and '"?"' in prev_line and "join" in prev_line:
                    # Found placeholder construction
                    # Now check if the execute has separate parameters
                    if "," in context and any(
                        param in context for param in ["run_ids", "ids", "params", "values", ")"]
                    ):
                        return True

        # Pattern 2: Check if f-string only builds SQL structure with constants
        # Example: f"SELECT * FROM {TABLE_NAME}" where TABLE_NAME is a constant
        f_string_vars = re.findall(r"\{(\w+)\}", context)
        if f_string_vars:
            # Check if all variables are constants (UPPERCASE or table/column names)
            all_constants = all(
                var.isupper() or "TABLE" in var.upper() or "COLUMN" in var.upper()
                for var in f_string_vars
            )
            if all_constants:
                return True  # Safe - using constants, not user data

        # Pattern 3: Check for security note comments nearby
        # If developers added security notes, it's likely safe
        for prev_line in reversed(recent_lines[-3:]):
            if "security note" in prev_line.lower() and "safe" in prev_line.lower():
                return True

        return False

    def _is_safe_random_usage(self, line_content: str, file_path: str, file_content: str) -> bool:
        """Check if random usage is in a safe context (tests, simulations, non-crypto).

        Phase 2 Enhancement: Reduces false positives for random module usage
        in test fixtures, A/B testing simulations, and demo code.

        Args:
            line_content: The line containing the match
            file_path: Path to the file being scanned
            file_content: Full file content for context analysis

        Returns:
            True if random usage is safe/documented, False if potentially insecure

        """
        # Check if file is a test file
        is_test = any(pattern in file_path.lower() for pattern in ["/test", "test_", "conftest"])

        # Check for explicit security notes nearby
        lines = file_content.split("\n")
        line_index = None
        for i, line in enumerate(lines):
            if line_content.strip() in line:
                line_index = i
                break

        if line_index is not None:
            # Check 5 lines before and after for security notes
            context_start = max(0, line_index - 5)
            context_end = min(len(lines), line_index + 5)
            context = "\n".join(lines[context_start:context_end]).lower()

            # Look for clarifying comments
            safe_indicators = [
                "security note",
                "not cryptographic",
                "not for crypto",
                "test data",
                "demo data",
                "simulation",
                "reproducible",
                "deterministic",
                "fixed seed",
                "not used for security",
                "not used for secrets",
                "not used for tokens",
            ]

            if any(indicator in context for indicator in safe_indicators):
                return True  # Documented as safe

        # Check for common safe random patterns
        line_lower = line_content.lower()

        # Pattern 1: Fixed seed (reproducible tests)
        if "random.seed(" in line_lower:
            return True  # Fixed seed is for reproducibility, not security

        # Pattern 2: A/B testing, simulations, demos
        safe_contexts = [
            "simulation",
            "demo",
            "a/b test",
            "ab_test",
            "fixture",
            "mock",
            "example",
            "sample",
        ]
        if any(context in file_path.lower() for context in safe_contexts):
            return True

        # If it's a test file without crypto indicators, it's probably safe
        if is_test:
            crypto_indicators = ["password", "secret", "token", "key", "crypto", "auth"]
            if not any(indicator in file_path.lower() for indicator in crypto_indicators):
                return True

        return False
