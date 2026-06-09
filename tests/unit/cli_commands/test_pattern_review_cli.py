"""Tests for the ``attune patterns`` CLI (review / promote / reject).

The CLI handlers build ``PatternReviewQueue()`` / ``PersistentPatternLibrary()``
with the default backend; the fixture redirects that to a temp file backend
so queue + library share one isolated store (no ~/.attune writes).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from attune.cli_commands import pattern_review as cli
from attune.memory.file_stash import FileStashBackend
from attune.memory.types import StagedPattern
from attune.pattern_review import PatternReviewQueue, PersistentPatternLibrary


@pytest.fixture
def backend(tmp_path, monkeypatch):
    be = FileStashBackend(base_dir=str(tmp_path))
    monkeypatch.setattr("attune.pattern_review._default_backend", lambda: be)
    return be


def _stage(backend, pattern_id="p1", **kw):
    base = {
        "agent_id": "a1",
        "pattern_type": "behavioral",
        "name": "n",
        "description": "d",
        "confidence": 0.8,
    }
    base.update(kw)
    PatternReviewQueue(backend=backend).stage(StagedPattern(pattern_id=pattern_id, **base))


def _args(**kw):
    return SimpleNamespace(**kw)


class TestReview:
    def test_empty_queue(self, backend, capsys):
        rc = cli.cmd_patterns_review(_args(type=None, agent=None, min_confidence=None, json=False))
        assert rc == 0
        assert "No patterns staged" in capsys.readouterr().out

    def test_lists_staged(self, backend, capsys):
        _stage(backend, "p1", name="cool pattern")
        rc = cli.cmd_patterns_review(_args(type=None, agent=None, min_confidence=None, json=False))
        out = capsys.readouterr().out
        assert rc == 0
        assert "p1" in out and "cool pattern" in out

    def test_json_output(self, backend, capsys):
        _stage(backend, "p1")
        rc = cli.cmd_patterns_review(_args(type=None, agent=None, min_confidence=None, json=True))
        import json as _json

        data = _json.loads(capsys.readouterr().out)
        assert rc == 0
        assert data[0]["pattern_id"] == "p1"


class TestPromote:
    def test_promote_durable(self, backend, capsys):
        _stage(backend, "p1")
        rc = cli.cmd_patterns_promote(_args(pattern_id="p1"))
        assert rc == 0
        assert "Promoted" in capsys.readouterr().out
        # Durable: a fresh persistent library over the same store has it.
        assert "p1" in PersistentPatternLibrary(backend=backend).patterns
        # And it's gone from the queue.
        assert PatternReviewQueue(backend=backend).get("p1") is None

    def test_promote_absent_returns_1(self, backend, capsys):
        rc = cli.cmd_patterns_promote(_args(pattern_id="nope"))
        assert rc == 1
        assert "No staged pattern" in capsys.readouterr().out

    def test_promote_no_id_returns_2(self, backend):
        assert cli.cmd_patterns_promote(_args(pattern_id=None)) == 2


class TestReject:
    def test_reject_drops(self, backend, capsys):
        _stage(backend, "p1")
        rc = cli.cmd_patterns_reject(_args(pattern_id="p1", reason="noisy"))
        assert rc == 0
        assert "Rejected" in capsys.readouterr().out
        assert PatternReviewQueue(backend=backend).get("p1") is None

    def test_reject_absent_returns_1(self, backend):
        assert cli.cmd_patterns_reject(_args(pattern_id="nope", reason=None)) == 1


class TestEdgeBranches:
    def test_review_truncates_long_code(self, backend, capsys):
        _stage(backend, "p1", code="x = " + "a" * 200)
        cli.cmd_patterns_review(_args(type=None, agent=None, min_confidence=None, json=False))
        assert "..." in capsys.readouterr().out

    def test_promote_duplicate_returns_1(self, backend, capsys):
        from attune.pattern_library import Pattern

        PersistentPatternLibrary(backend=backend).contribute_pattern(
            "a1",
            Pattern(id="p1", agent_id="a1", pattern_type="behavioral", name="x", description="d"),
        )
        _stage(backend, "p1")
        rc = cli.cmd_patterns_promote(_args(pattern_id="p1"))
        assert rc == 1
        assert "Cannot promote" in capsys.readouterr().out

    def test_reject_no_id_returns_2(self, backend):
        assert cli.cmd_patterns_reject(_args(pattern_id=None, reason=None)) == 2

    def test_review_shows_short_code_untruncated(self, backend, capsys):
        _stage(backend, "p1", code="y = 2")
        cli.cmd_patterns_review(_args(type=None, agent=None, min_confidence=None, json=False))
        out = capsys.readouterr().out
        assert "y = 2" in out and "..." not in out
