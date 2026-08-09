"""Tests for the append-only verdict history (memory-status-integrity P2 task 4).

All fixtures live under ``tmp_path`` — nothing reads the real home
directory. The properties pinned here are the D6 design rules: digest
binding ignores formatting but breaks on wording, the log is append-only
with last-record-wins resolution, and every reader fails open.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from attune.memory.verdict_log import (
    VERDICTS_FILENAME,
    VerdictRecord,
    append_verdict,
    canonical_digest,
    latest_verdicts,
    load_verdicts,
    propagate_verdict,
    set_verified,
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


def _write_mem(tmp_path: Path, extra: str = "") -> Path:
    path = tmp_path / "project_x.md"
    path.write_text(
        "---\n"
        "name: project_x\n"
        "description: a claim\n"
        "metadata:\n"
        "  type: project\n"
        f"{extra}"
        "---\n\nThe body.\n",
        encoding="utf-8",
    )
    return path


class TestSetVerified:
    def test_inserts_when_absent_and_preserves_everything_else(self, tmp_path: Path) -> None:
        path = _write_mem(tmp_path)
        before = path.read_text(encoding="utf-8")
        set_verified(path, date(2026, 8, 9))
        after = path.read_text(encoding="utf-8")
        assert "verified: 2026-08-09\n---" in after
        assert after.replace("\nverified: 2026-08-09", "") == before
        assert after.endswith("---\n\nThe body.\n")

    def test_replaces_when_present(self, tmp_path: Path) -> None:
        path = _write_mem(tmp_path, extra="verified: 2026-01-01\n")
        set_verified(path, date(2026, 8, 9))
        text = path.read_text(encoding="utf-8")
        assert text.count("verified:") == 1
        assert "verified: 2026-08-09" in text

    def test_setting_verified_does_not_change_the_digest(self, tmp_path: Path) -> None:
        """``verified:`` is outside the canonical digest by design — recording
        a verification must never invalidate the verification it records."""
        from attune.memory.curated_audit import load_memory

        path = _write_mem(tmp_path)
        before = load_memory(path).digest
        set_verified(path, date(2026, 8, 9))
        assert load_memory(path).digest == before

    def test_file_without_frontmatter_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "plain.md"
        path.write_text("# just a heading\n", encoding="utf-8")
        with pytest.raises(ValueError, match="no frontmatter"):
            set_verified(path, date(2026, 8, 9))


class TestPropagateVerdict:
    def test_deletes_the_derived_node_key(self) -> None:
        deleted = []

        class _Client:
            def delete(self, key):
                deleted.append(key)
                return 1

        assert propagate_verdict("project_x", client=_Client()) is True
        assert deleted == ["attune:memory:node:project_x"]

    def test_missing_key_reports_false(self) -> None:
        class _Client:
            def delete(self, key):
                return 0

        assert propagate_verdict("project_x", client=_Client()) is False

    def test_client_error_degrades_to_false(self) -> None:
        """The loop must never block on the memory layer."""

        class _Client:
            def delete(self, key):
                raise ConnectionError("redis down")

        assert propagate_verdict("project_x", client=_Client()) is False
