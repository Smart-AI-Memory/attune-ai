"""Tests for the append-only verdict history (memory-status-integrity P2 task 4).

All fixtures live under ``tmp_path`` — nothing reads the real home
directory. The properties pinned here are the D6 design rules: digest
binding ignores formatting but breaks on wording, the log is append-only
with last-record-wins resolution, and every reader fails open.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.memory.verdict_log import (
    VERDICTS_FILENAME,
    VerdictRecord,
    append_verdict,
    canonical_digest,
    latest_verdicts,
    load_verdicts,
)


def _record(stem: str = "project_x", verdict: str = "keep", digest: str = "d1") -> VerdictRecord:
    return VerdictRecord.create(stem=stem, verdict=verdict, digest=digest, who="patrick")


class TestVerdictRecord:
    def test_create_stamps_utc_timestamp(self) -> None:
        rec = _record()
        assert rec.at.endswith("+00:00")
        assert rec.who == "patrick"

    def test_invalid_verdict_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid verdict"):
            VerdictRecord.create(stem="s", verdict="approve", digest="d", who="w")


class TestCanonicalDigest:
    def test_formatting_only_changes_preserve_the_digest(self) -> None:
        """D6 #2: a reformat that changes no words must not invalidate."""
        base = canonical_digest("a claim", "line one\nline two\n")
        assert canonical_digest("a claim", "line one   \nline two") == base
        assert canonical_digest("a claim", "line one\r\nline two\r\n") == base
        assert canonical_digest("a claim", "\n\nline one\n\n\n\nline two\n\n") == base

    def test_wording_change_breaks_the_digest(self) -> None:
        base = canonical_digest("a claim", "line one\nline two\n")
        assert canonical_digest("a claim", "line one\nline three\n") != base
        assert canonical_digest("a different claim", "line one\nline two\n") != base

    def test_missing_description_is_stable(self) -> None:
        assert canonical_digest(None, "body") == canonical_digest(None, "body")
        assert canonical_digest(None, "body") != canonical_digest("desc", "body")

    def test_moving_words_between_description_and_body_breaks_digest(self) -> None:
        """Codex D11 finding: without a field boundary, `("a b", "c")` and
        `("a", "b c")` shared a token stream and wrongly preserved
        verification across a served-metadata change."""
        assert canonical_digest("a b", "c") != canonical_digest("a", "b c")


class TestAppendAndLoad:
    def test_round_trip_preserves_order(self, tmp_path: Path) -> None:
        first = _record(digest="d1")
        second = _record(verdict="sharper", digest="d2")
        append_verdict(tmp_path, first)
        append_verdict(tmp_path, second)

        loaded = load_verdicts(tmp_path)
        assert [(r.verdict, r.digest) for r in loaded] == [("keep", "d1"), ("sharper", "d2")]
        assert (tmp_path / VERDICTS_FILENAME).exists()

    def test_append_requires_an_existing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="not a directory"):
            append_verdict(tmp_path / "nope", _record())

    def test_load_missing_log_is_empty(self, tmp_path: Path) -> None:
        assert load_verdicts(tmp_path) == []

    def test_malformed_line_is_skipped_not_fatal(self, tmp_path: Path) -> None:
        """Fail-open: one corrupt append must not disable the binding check."""
        append_verdict(tmp_path, _record(digest="d1"))
        log = tmp_path / VERDICTS_FILENAME
        with log.open("a", encoding="utf-8") as handle:
            handle.write("not json at all\n")
            handle.write(json.dumps({"stem": "s", "verdict": "bogus-value"}) + "\n")
        append_verdict(tmp_path, _record(digest="d2"))

        loaded = load_verdicts(tmp_path)
        assert [r.digest for r in loaded] == ["d1", "d2"]

    def test_latest_verdicts_last_record_wins(self, tmp_path: Path) -> None:
        append_verdict(tmp_path, _record(stem="a", verdict="keep", digest="d1"))
        append_verdict(tmp_path, _record(stem="b", verdict="wrong", digest="d2"))
        append_verdict(tmp_path, _record(stem="a", verdict="sharper", digest="d3"))

        latest = latest_verdicts(tmp_path)
        assert latest["a"].verdict == "sharper" and latest["a"].digest == "d3"
        assert latest["b"].verdict == "wrong"

    def test_latest_verdicts_empty_without_log(self, tmp_path: Path) -> None:
        assert latest_verdicts(tmp_path) == {}
