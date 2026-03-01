"""Response parsing mixin for workflow classes.

This module provides methods for parsing and extracting structured data
from LLM responses, including XML parsing, regex-based extraction, and
finding inference.

Extracted from base.py for improved maintainability and import performance.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
import uuid
from typing import Any


class ResponseParsingMixin:
    """Mixin providing response parsing capabilities for workflows.

    This mixin adds methods for extracting structured findings from
    LLM responses, including XML parsing and regex-based extraction.

    Methods:
        _parse_xml_response: Parse XML-formatted LLM responses
        _extract_findings_from_response: Extract findings using multiple strategies
        _enrich_finding_with_location: Add location details to findings
        _parse_location_string: Parse location strings to file/line/column
        _infer_severity: Infer severity level from text
        _infer_category: Infer category from text

    Note:
        This mixin expects the class to have a _get_xml_config() method
        that returns XML configuration settings.

    """

    def _parse_xml_response(self, response: str) -> dict[str, Any]:
        """Parse an XML response if XML enforcement is enabled.

        Args:
            response: The LLM response text.

        Returns:
            Dictionary with parsed fields or raw response data.

        """
        from attune.prompts import XmlResponseParser

        config = self._get_xml_config()

        if not config.get("enforce_response_xml", False):
            # No parsing needed, return as-is
            return {
                "_parsed_response": None,
                "_raw": response,
            }

        fallback = config.get("fallback_on_parse_error", True)
        parser = XmlResponseParser(fallback_on_error=fallback)
        parsed = parser.parse(response)

        return {
            "_parsed_response": parsed,
            "_raw": response,
            "summary": parsed.summary,
            "findings": [f.to_dict() for f in parsed.findings],
            "checklist": parsed.checklist,
            "xml_parsed": parsed.success,
            "parse_errors": parsed.errors,
        }

    def _extract_findings_from_response(
        self,
        response: str,
        files_changed: list[str],
        code_context: str = "",
    ) -> list[dict[str, Any]]:
        """Extract structured findings from LLM response.

        Tries multiple strategies in order:
        1. XML parsing (if XML tags present)
        2. Regex-based extraction for file:line patterns
        3. Returns empty list if no findings extractable

        Args:
            response: Raw LLM response text
            files_changed: List of files being analyzed (for context)
            code_context: Original code being reviewed (optional)

        Returns:
            List of findings matching WorkflowFinding schema:
            [
                {
                    "id": "unique-id",
                    "file": "relative/path.py",
                    "line": 42,
                    "column": 10,
                    "severity": "high",
                    "category": "security",
                    "message": "Brief message",
                    "details": "Extended explanation",
                    "recommendation": "Fix suggestion"
                }
            ]

        """
        findings: list[dict[str, Any]] = []

        # Strategy 1: Try XML parsing first
        response_lower = response.lower()
        if (
            "<finding>" in response_lower
            or "<issue>" in response_lower
            or "<findings>" in response_lower
        ):
            # Parse XML directly (bypass config checks)
            from attune.prompts import XmlResponseParser

            parser = XmlResponseParser(fallback_on_error=True)
            parsed = parser.parse(response)

            if parsed.success and parsed.findings:
                for raw_finding in parsed.findings:
                    enriched = self._enrich_finding_with_location(
                        raw_finding.to_dict(),
                        files_changed,
                    )
                    findings.append(enriched)
                return findings

        # Strategy 2: Regex-based extraction for common patterns
        # Match patterns like:
        # - "src/auth.py:42: SQL injection found"
        # - "In file src/auth.py line 42"
        # - "auth.py (line 42, column 10)"
        patterns = [
            # Pattern 1: file.py:line:column: message
            r"([^\s:]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php)):(\d+):(\d+):\s*(.+)",
            # Pattern 2: file.py:line: message
            r"([^\s:]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php)):(\d+):\s*(.+)",
            # Pattern 3: in file X line Y
            r"(?:in file|file)\s+([^\s]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php))\s+line\s+(\d+)",
            # Pattern 4: file.py (line X)
            r"([^\s]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php))\s*\(line\s+(\d+)(?:,\s*col(?:umn)?\s+(\d+))?\)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    file_path = match[0]
                    line = int(match[1])

                    # Handle different pattern formats
                    if len(match) == 4 and match[2].isdigit():
                        # Pattern 1: file:line:col:message
                        column = int(match[2])
                        message = match[3]
                    elif len(match) == 3 and match[2] and not match[2].isdigit():
                        # Pattern 2: file:line:message
                        column = 1
                        message = match[2]
                    elif len(match) == 3 and match[2].isdigit():
                        # Pattern 4: file (line col)
                        column = int(match[2])
                        message = ""
                    else:
                        # Pattern 3: in file X line Y (no message)
                        column = 1
                        message = ""

                    # Determine severity from keywords in message
                    severity = self._infer_severity(message)
                    category = self._infer_category(message)

                    findings.append(
                        {
                            "id": str(uuid.uuid4())[:8],
                            "file": file_path,
                            "line": line,
                            "column": column,
                            "severity": severity,
                            "category": category,
                            "message": message.strip() if message else "",
                            "details": "",
                            "recommendation": "",
                        },
                    )

        # Deduplicate by file:line
        seen: set[tuple[str, int]] = set()
        unique_findings = []
        for finding in findings:
            key = (finding["file"], finding["line"])
            if key not in seen:
                seen.add(key)
                unique_findings.append(finding)

        return unique_findings

    def _enrich_finding_with_location(
        self,
        raw_finding: dict[str, Any],
        files_changed: list[str],
    ) -> dict[str, Any]:
        """Enrich a finding from XML parser with file/line/column fields.

        Args:
            raw_finding: Finding dict from XML parser (has 'location' string field)
            files_changed: List of files being analyzed

        Returns:
            Enriched finding dict with file, line, column fields

        """
        location_str = raw_finding.get("location", "")
        file_path, line, column = self._parse_location_string(location_str, files_changed)

        # Map category from severity or title keywords
        category = self._infer_category(
            raw_finding.get("title", "") + " " + raw_finding.get("details", ""),
        )

        return {
            "id": str(uuid.uuid4())[:8],
            "file": file_path,
            "line": line,
            "column": column,
            "severity": raw_finding.get("severity", "medium"),
            "category": category,
            "message": raw_finding.get("title", ""),
            "details": raw_finding.get("details", ""),
            "recommendation": raw_finding.get("fix", ""),
        }

    def _parse_location_string(
        self,
        location: str,
        files_changed: list[str],
    ) -> tuple[str, int, int]:
        """Parse a location string to extract file, line, column.

        Handles formats like:
        - "src/auth.py:42:10"
        - "src/auth.py:42"
        - "auth.py line 42"
        - "line 42 in auth.py"

        Args:
            location: Location string from finding
            files_changed: List of files being analyzed (for fallback)

        Returns:
            Tuple of (file_path, line_number, column_number)
            Defaults: ("", 1, 1) if parsing fails

        """
        if not location:
            # Fallback: use first file if available
            return (files_changed[0] if files_changed else "", 1, 1)

        # Try colon-separated format: file.py:line:col
        match = re.search(
            r"([^\s:]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php)):(\d+)(?::(\d+))?",
            location,
        )
        if match:
            file_path = match.group(1)
            line = int(match.group(2))
            column = int(match.group(3)) if match.group(3) else 1
            return (file_path, line, column)

        # Try "line X in file.py" format
        match = re.search(
            r"line\s+(\d+)\s+(?:in|of)\s+([^\s]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php))",
            location,
            re.IGNORECASE,
        )
        if match:
            line = int(match.group(1))
            file_path = match.group(2)
            return (file_path, line, 1)

        # Try "file.py line X" format
        match = re.search(
            r"([^\s]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php))\s+line\s+(\d+)",
            location,
            re.IGNORECASE,
        )
        if match:
            file_path = match.group(1)
            line = int(match.group(2))
            return (file_path, line, 1)

        # Extract just line number if present
        match = re.search(r"line\s+(\d+)", location, re.IGNORECASE)
        if match:
            line = int(match.group(1))
            # Use first file from files_changed as fallback
            file_path = files_changed[0] if files_changed else ""
            return (file_path, line, 1)

        # Couldn't parse - return defaults
        return (files_changed[0] if files_changed else "", 1, 1)

    def _infer_severity(self, text: str) -> str:
        """Infer severity from keywords in text.

        Args:
            text: Message or title text

        Returns:
            Severity level: critical, high, medium, low, or info

        """
        text_lower = text.lower()

        if any(
            word in text_lower
            for word in [
                "critical",
                "severe",
                "exploit",
                "vulnerability",
                "injection",
                "remote code execution",
                "rce",
            ]
        ):
            return "critical"

        if any(
            word in text_lower
            for word in [
                "high",
                "security",
                "unsafe",
                "dangerous",
                "xss",
                "csrf",
                "auth",
                "password",
                "secret",
            ]
        ):
            return "high"

        if any(
            word in text_lower
            for word in [
                "warning",
                "issue",
                "problem",
                "bug",
                "error",
                "deprecated",
                "leak",
            ]
        ):
            return "medium"

        if any(word in text_lower for word in ["low", "minor", "style", "format", "typo"]):
            return "low"

        return "info"

    def _infer_category(self, text: str) -> str:
        """Infer finding category from keywords.

        Args:
            text: Message or title text

        Returns:
            Category: security, performance, maintainability, style, or correctness

        """
        text_lower = text.lower()

        if any(
            word in text_lower
            for word in [
                "security",
                "vulnerability",
                "injection",
                "xss",
                "csrf",
                "auth",
                "encrypt",
                "password",
                "secret",
                "unsafe",
            ]
        ):
            return "security"

        if any(
            word in text_lower
            for word in [
                "performance",
                "slow",
                "memory",
                "leak",
                "inefficient",
                "optimization",
                "cache",
            ]
        ):
            return "performance"

        if any(
            word in text_lower
            for word in [
                "complex",
                "refactor",
                "duplicate",
                "maintainability",
                "readability",
                "documentation",
            ]
        ):
            return "maintainability"

        if any(
            word in text_lower for word in ["style", "format", "lint", "convention", "whitespace"]
        ):
            return "style"

        return "correctness"
