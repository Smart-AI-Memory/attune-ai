"""Response parsing service for workflows.

Standalone service extracted from ResponseParsingMixin. Provides structured
data extraction from LLM responses including XML parsing and regex patterns.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
import uuid
from typing import Any


class ParsingService:
    """Service for parsing structured data from LLM responses.

    Extracts findings with file/line/column locations from LLM output
    using XML parsing and regex-based strategies.

    Args:
        xml_config: Optional XML configuration dict for response parsing.

    Example:
        >>> parser = ParsingService()
        >>> findings = parser.extract_findings(response_text, ["src/auth.py"])

    """

    def __init__(self, xml_config: dict[str, Any] | None = None) -> None:
        self._xml_config = xml_config or {}

    def parse_xml_response(self, response: str) -> dict[str, Any]:
        """Parse an XML response if XML enforcement is enabled.

        Args:
            response: The LLM response text.

        Returns:
            Dictionary with parsed fields or raw response data.

        """
        from attune.prompts import XmlResponseParser

        if not self._xml_config.get("enforce_response_xml", False):
            return {"_parsed_response": None, "_raw": response}

        fallback = self._xml_config.get("fallback_on_parse_error", True)
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

    def extract_findings(
        self,
        response: str,
        files_changed: list[str],
        code_context: str = "",
    ) -> list[dict[str, Any]]:
        """Extract structured findings from LLM response.

        Tries multiple strategies:
        1. XML parsing (if XML tags present)
        2. Regex-based extraction for file:line patterns

        Args:
            response: Raw LLM response text
            files_changed: List of files being analyzed
            code_context: Original code being reviewed (optional)

        Returns:
            List of finding dicts with id, file, line, column, severity, etc.

        """
        findings: list[dict[str, Any]] = []

        # Strategy 1: Try XML parsing first
        response_lower = response.lower()
        if any(tag in response_lower for tag in ["<finding>", "<issue>", "<findings>"]):
            from attune.prompts import XmlResponseParser

            parser = XmlResponseParser(fallback_on_error=True)
            parsed = parser.parse(response)

            if parsed.success and parsed.findings:
                for raw_finding in parsed.findings:
                    enriched = self._enrich_finding(raw_finding.to_dict(), files_changed)
                    findings.append(enriched)
                return findings

        # Strategy 2: Regex-based extraction
        patterns = [
            r"([^\s:]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php)):(\d+):(\d+):\s*(.+)",
            r"([^\s:]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php)):(\d+):\s*(.+)",
            r"(?:in file|file)\s+([^\s]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php))\s+line\s+(\d+)",
            r"([^\s]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php))\s*\(line\s+(\d+)"
            r"(?:,\s*col(?:umn)?\s+(\d+))?\)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    file_path = match[0]
                    line = int(match[1])

                    if len(match) == 4 and match[2].isdigit():
                        column = int(match[2])
                        message = match[3]
                    elif len(match) == 3 and match[2] and not match[2].isdigit():
                        column = 1
                        message = match[2]
                    elif len(match) == 3 and match[2].isdigit():
                        column = int(match[2])
                        message = ""
                    else:
                        column = 1
                        message = ""

                    findings.append(
                        {
                            "id": str(uuid.uuid4())[:8],
                            "file": file_path,
                            "line": line,
                            "column": column,
                            "severity": self.infer_severity(message),
                            "category": self.infer_category(message),
                            "message": message.strip() if message else "",
                            "details": "",
                            "recommendation": "",
                        },
                    )

        # Deduplicate by file:line
        seen: set[tuple[str, int]] = set()
        unique: list[dict[str, Any]] = []
        for finding in findings:
            key = (finding["file"], finding["line"])
            if key not in seen:
                seen.add(key)
                unique.append(finding)

        return unique

    def _enrich_finding(
        self,
        raw_finding: dict[str, Any],
        files_changed: list[str],
    ) -> dict[str, Any]:
        """Enrich a finding from XML parser with file/line/column fields."""
        location_str = raw_finding.get("location", "")
        file_path, line, column = self.parse_location(location_str, files_changed)

        category = self.infer_category(
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

    def parse_location(
        self,
        location: str,
        files_changed: list[str],
    ) -> tuple[str, int, int]:
        """Parse a location string to extract file, line, column.

        Args:
            location: Location string from finding
            files_changed: List of files being analyzed (for fallback)

        Returns:
            Tuple of (file_path, line_number, column_number)

        """
        if not location:
            return (files_changed[0] if files_changed else "", 1, 1)

        # file.py:line:col
        match = re.search(
            r"([^\s:]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php)):(\d+)(?::(\d+))?",
            location,
        )
        if match:
            return (match.group(1), int(match.group(2)), int(match.group(3) or 1))

        # "line X in file.py"
        match = re.search(
            r"line\s+(\d+)\s+(?:in|of)\s+([^\s]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php))",
            location,
            re.IGNORECASE,
        )
        if match:
            return (match.group(2), int(match.group(1)), 1)

        # "file.py line X"
        match = re.search(
            r"([^\s]+\.(?:py|ts|tsx|js|jsx|java|go|rb|php))\s+line\s+(\d+)",
            location,
            re.IGNORECASE,
        )
        if match:
            return (match.group(1), int(match.group(2)), 1)

        # Just line number
        match = re.search(r"line\s+(\d+)", location, re.IGNORECASE)
        if match:
            return (files_changed[0] if files_changed else "", int(match.group(1)), 1)

        return (files_changed[0] if files_changed else "", 1, 1)

    @staticmethod
    def infer_severity(text: str) -> str:
        """Infer severity from keywords in text.

        Returns:
            Severity level: critical, high, medium, low, or info

        """
        text_lower = text.lower()

        if any(
            w in text_lower
            for w in [
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
            w in text_lower
            for w in [
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
            w in text_lower
            for w in [
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

        if any(w in text_lower for w in ["low", "minor", "style", "format", "typo"]):
            return "low"

        return "info"

    @staticmethod
    def infer_category(text: str) -> str:
        """Infer finding category from keywords.

        Returns:
            Category: security, performance, maintainability, style, or correctness

        """
        text_lower = text.lower()

        if any(
            w in text_lower
            for w in [
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
            w in text_lower
            for w in [
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
            w in text_lower
            for w in [
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
            w in text_lower
            for w in [
                "style",
                "format",
                "lint",
                "convention",
                "whitespace",
            ]
        ):
            return "style"

        return "correctness"
