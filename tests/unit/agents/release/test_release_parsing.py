"""Tests for release_parsing._parse_response.

Covers all four parse strategies (XML, markdown-fenced, raw JSON, regex
extraction) plus their failure fallthroughs. Pure function, no external
deps — previously omitted from coverage as "Requires LLM API calls"
(mislabeled; un-omitted alongside this file per the omit-audit).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.agents.release.release_parsing import _parse_response


class TestEmpty:
    def test_empty_string(self):
        assert _parse_response("") == {"parse_error": "empty response"}

    def test_whitespace_only(self):
        assert _parse_response("   \n\t ") == {"parse_error": "empty response"}


class TestXmlStrategy:
    def test_valid_xml_json(self):
        out = _parse_response('<analysis>{"score": 9.0}</analysis>')
        assert out == {"score": 9.0}

    def test_invalid_xml_json_falls_through(self):
        # XML block present but bad JSON → falls through to later strategies,
        # ultimately the no-content error (no score/coverage tokens).
        out = _parse_response("<analysis>not json</analysis>")
        assert out["parse_error"] == "no parseable content"


class TestMarkdownStrategy:
    def test_valid_fenced_json(self):
        out = _parse_response('```json\n{"coverage_percent": 85}\n```')
        assert out == {"coverage_percent": 85}

    def test_fenced_without_lang(self):
        out = _parse_response('```\n{"score": 7}\n```')
        assert out == {"score": 7}

    def test_invalid_fenced_falls_through(self):
        out = _parse_response("```\nnope\n```")
        assert out["parse_error"] == "no parseable content"


class TestRawJsonStrategy:
    def test_valid_raw_json(self):
        out = _parse_response('{"approved": true, "score": 8.5}')
        assert out["approved"] is True
        assert out["score"] == 8.5

    def test_invalid_raw_json_falls_through(self):
        # Starts with { but isn't valid JSON → regex last resort, then error.
        out = _parse_response("{ broken")
        assert out["parse_error"] == "no parseable content"


class TestRegexStrategy:
    def test_extracts_score(self):
        out = _parse_response("Overall score: 7.5 looks good")
        assert out["score"] == 7.5
        assert out["parse_method"] == "regex"

    def test_extracts_coverage(self):
        out = _parse_response("Coverage: 92% of lines")
        assert out["coverage_percent"] == 92.0
        assert out["parse_method"] == "regex"

    def test_extracts_critical_issues(self):
        out = _parse_response("Found 3 critical issues in the scan")
        assert out["critical_issues"] == 3
        assert out["parse_method"] == "regex"

    def test_extracts_multiple_metrics(self):
        out = _parse_response("score: 6, coverage: 80%, 2 high findings")
        assert out["score"] == 6.0
        assert out["coverage_percent"] == 80.0
        assert out["critical_issues"] == 2

    def test_no_parseable_content_truncates_raw(self):
        long_text = "x" * 1000
        out = _parse_response(long_text)
        assert out["parse_error"] == "no parseable content"
        assert len(out["raw_text"]) == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
