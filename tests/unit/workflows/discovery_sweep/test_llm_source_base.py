"""Tests for :mod:`attune.workflows.discovery_sweep.llm_source_base`.

Covers ``parse_findings_json`` (well-formed, malformed, missing,
multi-block, prose-wrapped, optional fields, invalid severity, bad
shapes) plus the :class:`LLMSource` marker defaults and the
:data:`STRUCTURED_EMIT_FOOTER` constant per spec P2A.2.
"""

from __future__ import annotations

import json

from attune.workflows.discovery_sweep import Finding
from attune.workflows.discovery_sweep.llm_source_base import (
    STRUCTURED_EMIT_FOOTER,
    LLMSource,
    parse_findings_json,
)

SOURCE = "fake-source"


def _wrap(payload: dict) -> str:
    """Helper: wrap a dict in a ```json fenced block."""
    return f"some prose\n\n```json\n{json.dumps(payload)}\n```\n"


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_wellformed_block_returns_findings() -> None:
    """Single well-formed block round-trips into Finding objects."""
    text = _wrap(
        {
            "findings": [
                {
                    "severity": "high",
                    "title": "eval() in handler",
                    "description": "Direct eval of untrusted input.",
                    "file": "src/handler.py",
                    "line": 42,
                    "evidence": "result = some_call(payload)",
                    "confidence": 0.9,
                    "tags": ["security", "cwe-95"],
                }
            ]
        }
    )

    findings = parse_findings_json(text, SOURCE)

    assert findings == [
        Finding(
            source=SOURCE,
            severity="high",
            title="eval() in handler",
            description="Direct eval of untrusted input.",
            file="src/handler.py",
            line=42,
            evidence="result = some_call(payload)",
            confidence=0.9,
            tags=("security", "cwe-95"),
        )
    ]


def test_block_with_extra_prose_parses() -> None:
    """Markdown prose before and after the fence doesn't confuse the regex."""
    text = (
        "# Audit summary\n\nWe found one issue.\n\n"
        + _wrap(
            {
                "findings": [
                    {
                        "severity": "medium",
                        "title": "broad except",
                        "description": "Catches Exception unnecessarily.",
                        "file": "src/util.py",
                        "line": 10,
                        "evidence": "except Exception:",
                        "confidence": 0.6,
                        "tags": [],
                    }
                ]
            }
        )
        + "\n\nEnd of report."
    )

    findings = parse_findings_json(text, SOURCE)

    assert len(findings) == 1
    assert findings[0].title == "broad except"
    assert findings[0].tags == ()


def test_multiple_blocks_uses_last() -> None:
    """Per P2A.2, when multiple ```json blocks appear the last wins."""
    first = _wrap({"findings": [{"severity": "low", "title": "first"}]})
    second = _wrap(
        {
            "findings": [
                {
                    "severity": "high",
                    "title": "second",
                    "description": "the winner",
                    "confidence": 0.8,
                }
            ]
        }
    )

    findings = parse_findings_json(first + "\n\n" + second, SOURCE)

    assert len(findings) == 1
    assert findings[0].title == "second"
    assert findings[0].severity == "high"


def test_missing_optional_fields_uses_defaults() -> None:
    """Entries without file/line/evidence/tags get None / empty defaults."""
    text = _wrap(
        {
            "findings": [
                {
                    "severity": "info",
                    "title": "doc only",
                    "description": "no location, no evidence, no tags",
                    "confidence": 0.5,
                }
            ]
        }
    )

    findings = parse_findings_json(text, SOURCE)

    assert findings == [
        Finding(
            source=SOURCE,
            severity="info",
            title="doc only",
            description="no location, no evidence, no tags",
            file=None,
            line=None,
            evidence=None,
            confidence=0.5,
            tags=(),
        )
    ]


def test_empty_findings_list_returns_empty_list() -> None:
    """A well-formed block with an empty list is NOT a parse failure."""
    text = _wrap({"findings": []})
    assert parse_findings_json(text, SOURCE) == []


# ---------------------------------------------------------------------------
# Fallback paths
# ---------------------------------------------------------------------------


def _assert_is_fallback(findings: list[Finding], expected_text: str) -> None:
    """Shared assertion for the text-only-fallback shape."""
    assert len(findings) == 1
    only = findings[0]
    assert only.source == SOURCE
    assert only.severity == "info"
    assert only.confidence == 0.1
    assert only.tags == ("text-only-fallback",)
    assert only.title == f"{SOURCE} returned no structured findings"
    assert only.file is None
    assert only.line is None
    if len(expected_text) > 200:
        assert only.evidence == expected_text[:200] + "..."
    else:
        assert only.evidence == expected_text


def test_missing_block_returns_fallback() -> None:
    """No ```json fence anywhere → single fallback finding."""
    text = "Plain prose, no fenced block at all."
    _assert_is_fallback(parse_findings_json(text, SOURCE), text)


def test_malformed_json_returns_fallback() -> None:
    """JSON syntax errors inside the fence → fallback."""
    text = "```json\n{not valid json,,,}\n```"
    _assert_is_fallback(parse_findings_json(text, SOURCE), text)


def test_findings_key_missing_returns_fallback() -> None:
    """Top-level dict without ``findings`` → fallback."""
    text = _wrap({"results": []})
    _assert_is_fallback(parse_findings_json(text, SOURCE), text)


def test_findings_not_a_list_returns_fallback() -> None:
    """``findings`` value of the wrong type → fallback."""
    text = _wrap({"findings": "not-a-list"})
    _assert_is_fallback(parse_findings_json(text, SOURCE), text)


def test_invalid_severity_returns_fallback() -> None:
    """Entry with severity outside the Literal set → fallback (no coercion)."""
    text = _wrap(
        {
            "findings": [
                {
                    "severity": "catastrophic",
                    "title": "bad sev",
                    "description": "made-up severity",
                    "confidence": 0.7,
                }
            ]
        }
    )
    _assert_is_fallback(parse_findings_json(text, SOURCE), text)


def test_entry_not_dict_returns_fallback() -> None:
    """A non-dict entry inside ``findings`` → fallback for the whole response."""
    text = _wrap({"findings": ["just a string, not an object"]})
    _assert_is_fallback(parse_findings_json(text, SOURCE), text)


def test_fallback_evidence_truncated_when_long() -> None:
    """Evidence is the raw text capped at 200 chars + ``...`` when long."""
    text = "x" * 500  # no json block → fallback
    out = parse_findings_json(text, SOURCE)
    assert len(out) == 1
    assert out[0].evidence == ("x" * 200) + "..."


# ---------------------------------------------------------------------------
# Marker + constants
# ---------------------------------------------------------------------------


def test_llmsource_default_attributes() -> None:
    """Bare subclass of LLMSource picks up is_llm=True, multiplier=1.0."""

    class MyAdapter(LLMSource):
        name = "my-adapter"

    instance = MyAdapter()
    assert instance.is_llm is True
    assert instance.budget_multiplier == 1.0


def test_structured_emit_footer_documents_findings_schema() -> None:
    """Footer must include a valid JSON example matching the parser contract."""
    assert "```json" in STRUCTURED_EMIT_FOOTER

    _, fenced_and_rest = STRUCTURED_EMIT_FOOTER.split("```json", 1)
    json_block, _ = fenced_and_rest.split("```", 1)
    payload = json.loads(json_block.strip())

    assert isinstance(payload, dict)
    assert "findings" in payload
    assert isinstance(payload["findings"], list)

    if payload["findings"]:
        first_finding = payload["findings"][0]
        assert isinstance(first_finding, dict)
        assert "severity" in first_finding
        assert "confidence" in first_finding
