"""Tests for prompts/parser module.

Tests Finding, ParsedResponse dataclasses, and XmlResponseParser.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.prompts.parser import Finding, ParsedResponse, XmlResponseParser

# ---------------------------------------------------------------------------
# Tests for Finding dataclass
# ---------------------------------------------------------------------------


class TestFinding:
    """Tests for the Finding dataclass."""

    def test_to_dict(self):
        """to_dict returns all fields."""
        f = Finding(
            severity="high",
            title="SQL Injection",
            location="app.py:42",
            details="User input not sanitized",
            fix="Use parameterized queries",
        )

        d = f.to_dict()

        assert d["severity"] == "high"
        assert d["title"] == "SQL Injection"
        assert d["location"] == "app.py:42"
        assert d["details"] == "User input not sanitized"
        assert d["fix"] == "Use parameterized queries"

    def test_from_dict(self):
        """from_dict creates Finding with defaults for missing keys."""
        d = {"severity": "low", "title": "Minor issue"}
        f = Finding.from_dict(d)

        assert f.severity == "low"
        assert f.title == "Minor issue"
        assert f.location is None
        assert f.details == ""
        assert f.fix == ""

    def test_from_dict_defaults(self):
        """from_dict with empty dict uses safe defaults."""
        f = Finding.from_dict({})

        assert f.severity == "medium"
        assert f.title == ""

    def test_roundtrip(self):
        """to_dict -> from_dict preserves all data."""
        original = Finding("critical", "XSS", "view.py:10", "Unescaped output", "Escape HTML")
        restored = Finding.from_dict(original.to_dict())

        assert restored.severity == original.severity
        assert restored.title == original.title
        assert restored.location == original.location
        assert restored.details == original.details
        assert restored.fix == original.fix


# ---------------------------------------------------------------------------
# Tests for ParsedResponse dataclass
# ---------------------------------------------------------------------------


class TestParsedResponse:
    """Tests for the ParsedResponse dataclass."""

    def test_to_dict(self):
        """to_dict includes findings as dicts."""
        resp = ParsedResponse(
            success=True,
            raw="<response>test</response>",
            summary="All good",
            findings=[Finding("low", "minor")],
            checklist=["Fix A"],
        )

        d = resp.to_dict()

        assert d["success"] is True
        assert len(d["findings"]) == 1
        assert d["findings"][0]["title"] == "minor"
        assert d["checklist"] == ["Fix A"]

    def test_from_dict(self):
        """from_dict restores findings as Finding objects."""
        d = {
            "success": True,
            "raw": "test",
            "summary": "ok",
            "findings": [{"severity": "high", "title": "issue"}],
            "checklist": ["item1"],
        }

        resp = ParsedResponse.from_dict(d)

        assert resp.success is True
        assert len(resp.findings) == 1
        assert isinstance(resp.findings[0], Finding)
        assert resp.findings[0].severity == "high"

    def test_from_raw(self):
        """from_raw creates a failed response with errors."""
        resp = ParsedResponse.from_raw("raw text", ["Parse failed"])

        assert resp.success is False
        assert resp.raw == "raw text"
        assert resp.summary == "raw text"
        assert resp.errors == ["Parse failed"]

    def test_from_raw_default_error(self):
        """from_raw with no errors provides default."""
        resp = ParsedResponse.from_raw("text")

        assert resp.errors == ["No XML content found"]

    def test_from_raw_truncates_summary(self):
        """from_raw truncates summary to 500 chars."""
        long_text = "x" * 1000
        resp = ParsedResponse.from_raw(long_text)

        assert len(resp.summary) == 500


# ---------------------------------------------------------------------------
# Tests for XmlResponseParser
# ---------------------------------------------------------------------------


class TestXmlResponseParser:
    """Tests for XmlResponseParser.parse."""

    def test_empty_response(self):
        """Empty string returns failed ParsedResponse."""
        parser = XmlResponseParser()
        result = parser.parse("")

        assert result.success is False
        assert "Empty response" in result.errors

    def test_no_xml_content_fallback(self):
        """Non-XML text returns fallback when fallback_on_error=True."""
        parser = XmlResponseParser(fallback_on_error=True)
        result = parser.parse("Just plain text without XML")

        assert result.success is False
        assert result.raw == "Just plain text without XML"

    def test_no_xml_content_raises(self):
        """Non-XML text raises ValueError when fallback_on_error=False."""
        parser = XmlResponseParser(fallback_on_error=False)

        with pytest.raises(ValueError, match="No XML content"):
            parser.parse("Just plain text")

    def test_parse_simple_xml(self):
        """Parses simple XML with summary."""
        parser = XmlResponseParser()
        xml = "<response><summary>All clear</summary></response>"
        result = parser.parse(xml)

        assert result.success is True
        assert result.summary == "All clear"

    def test_parse_xml_in_markdown_block(self):
        """Extracts XML from markdown code blocks."""
        parser = XmlResponseParser()
        text = "Here's the analysis:\n```xml\n<response><summary>Found issues</summary></response>\n```"
        result = parser.parse(text)

        assert result.success is True
        assert result.summary == "Found issues"

    def test_parse_findings(self):
        """Extracts findings from XML."""
        parser = XmlResponseParser()
        xml = """<response>
            <finding severity="high">
                <title>SQL Injection</title>
                <location>db.py:10</location>
                <details>Unparameterized query</details>
                <fix>Use bind parameters</fix>
            </finding>
        </response>"""
        result = parser.parse(xml)

        assert result.success is True
        assert len(result.findings) == 1
        assert result.findings[0].severity == "high"
        assert result.findings[0].title == "SQL Injection"
        assert result.findings[0].location == "db.py:10"

    def test_parse_findings_in_container(self):
        """Extracts findings from <findings><item> structure."""
        parser = XmlResponseParser()
        xml = """<response>
            <findings>
                <item severity="medium">
                    <title>Unused import</title>
                </item>
            </findings>
        </response>"""
        result = parser.parse(xml)

        assert result.success is True
        assert len(result.findings) == 1
        assert result.findings[0].title == "Unused import"

    def test_parse_checklist(self):
        """Extracts remediation checklist items."""
        parser = XmlResponseParser()
        xml = """<response>
            <remediation-checklist>
                <item>Fix SQL injection</item>
                <item>Add input validation</item>
            </remediation-checklist>
        </response>"""
        result = parser.parse(xml)

        assert result.success is True
        assert len(result.checklist) == 2
        assert "Fix SQL injection" in result.checklist

    def test_parse_extra_verdict(self):
        """Extracts verdict into extra dict."""
        parser = XmlResponseParser()
        xml = "<response><verdict>APPROVE</verdict></response>"
        result = parser.parse(xml)

        assert result.success is True
        assert result.extra.get("verdict") == "APPROVE"

    def test_parse_extra_suggestions(self):
        """Extracts suggestions into extra dict."""
        parser = XmlResponseParser()
        xml = """<response>
            <suggestions>
                <suggestion>Use type hints</suggestion>
                <suggestion>Add docstrings</suggestion>
            </suggestions>
        </response>"""
        result = parser.parse(xml)

        assert result.success is True
        assert len(result.extra.get("suggestions", [])) == 2

    def test_malformed_xml_fallback(self):
        """Malformed XML returns fallback with error."""
        parser = XmlResponseParser(fallback_on_error=True)
        result = parser.parse("<response><unclosed>")

        assert result.success is False
        assert any("parse error" in e.lower() for e in result.errors)

    def test_generic_code_block_with_xml(self):
        """Extracts XML from generic code block (no xml language tag)."""
        parser = XmlResponseParser()
        text = "```\n<response><summary>test</summary></response>\n```"
        result = parser.parse(text)

        assert result.success is True
        assert result.summary == "test"

    def test_response_tags_extraction(self):
        """Extracts XML from <response> tags in mixed text."""
        parser = XmlResponseParser()
        text = "Some preamble text.\n<response><summary>found it</summary></response>\nMore text."
        result = parser.parse(text)

        assert result.success is True
        assert result.summary == "found it"
