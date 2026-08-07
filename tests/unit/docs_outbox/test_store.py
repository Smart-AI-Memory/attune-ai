# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Outbox store (R1): conflict-free per-artifact files."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from attune.docs_outbox.store import (
    archive_swept,
    list_artifacts,
    outbox_dir,
    outbox_status,
    write_artifact,
)

NOW = datetime(2026, 8, 6, 14, 32)


def test_write_lesson_uses_default_target_and_timestamp_name(tmp_path):
    path = write_artifact("lesson", "browser-pane-svg", "Body.", attune_home=tmp_path, now=NOW)
    assert path.name == "20260806-1432-lesson-browser-pane-svg.md"
    text = path.read_text(encoding="utf-8")
    assert "kind: lesson" in text
    assert "target: .claude/lessons.md" in text
    assert text.endswith("Body.\n")


def test_concurrent_writers_never_collide(tmp_path):
    a = write_artifact("lesson", "same-slug", "First.", attune_home=tmp_path, now=NOW)
    b = write_artifact("lesson", "same-slug", "Second.", attune_home=tmp_path, now=NOW)
    assert a != b
    assert len(list_artifacts(tmp_path)) == 2


def test_merge_now_kinds_are_refused(tmp_path):
    with pytest.raises(ValueError, match="merge-now"):
        write_artifact("decision", "some-ruling", "Body.", attune_home=tmp_path)


def test_unknown_kind_is_refused(tmp_path):
    with pytest.raises(ValueError, match="unknown artifact kind"):
        write_artifact("banana", "s", "Body.", attune_home=tmp_path)


def test_bad_slug_is_refused(tmp_path):
    with pytest.raises(ValueError, match="kebab-case"):
        write_artifact("lesson", "../escape", "Body.", attune_home=tmp_path)


def test_report_requires_explicit_target(tmp_path):
    with pytest.raises(ValueError, match="no default target"):
        write_artifact("report", "roundtable-x", "Body.", attune_home=tmp_path)
    path = write_artifact(
        "report", "roundtable-x", "Body.", target="docs/reports/x.md", attune_home=tmp_path
    )
    assert "target: docs/reports/x.md" in path.read_text(encoding="utf-8")


def test_empty_body_is_refused(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        write_artifact("lesson", "s", "   \n", attune_home=tmp_path)


def test_list_artifacts_sorted_and_parsed(tmp_path):
    write_artifact("lesson", "later", "L.", attune_home=tmp_path, now=NOW + timedelta(minutes=5))
    write_artifact("lesson", "earlier", "E.", attune_home=tmp_path, now=NOW)
    artifacts = list_artifacts(tmp_path)
    assert [a.slug for a in artifacts] == ["earlier", "later"]
    assert artifacts[0].created == NOW
    assert artifacts[0].body == "E.\n"
    assert not artifacts[0].issues


def test_list_ignores_digest_and_swept(tmp_path):
    write_artifact("lesson", "one", "Body.", attune_home=tmp_path, now=NOW)
    (outbox_dir(tmp_path) / "digest.md").write_text("# digest\n", encoding="utf-8")
    assert len(list_artifacts(tmp_path)) == 1


def test_missing_frontmatter_becomes_issue(tmp_path):
    (outbox_dir(tmp_path) / "20260806-1400-lesson-raw.md").write_text("raw\n", encoding="utf-8")
    (artifact,) = list_artifacts(tmp_path)
    assert "missing frontmatter" in artifact.issues
    assert artifact.body == "raw\n"


def test_status_empty_then_stale(tmp_path):
    empty = outbox_status(tmp_path)
    assert (empty.count, empty.stale) == (0, False)
    write_artifact(
        "lesson", "old", "Body.", attune_home=tmp_path, now=datetime.now() - timedelta(days=3)
    )
    write_artifact("lesson", "new", "Body.", attune_home=tmp_path, now=datetime.now())
    status = outbox_status(tmp_path)
    assert status.count == 2
    assert status.oldest_days >= 2.9
    assert status.stale is True


def test_status_fresh_is_not_stale(tmp_path):
    write_artifact("lesson", "new", "Body.", attune_home=tmp_path, now=datetime.now())
    assert outbox_status(tmp_path).stale is False


def test_archive_swept_moves_files(tmp_path):
    write_artifact("lesson", "one", "Body.", attune_home=tmp_path, now=NOW)
    artifacts = list_artifacts(tmp_path)
    dest = archive_swept(artifacts, tmp_path)
    assert not list_artifacts(tmp_path)
    assert (dest / "20260806-1432-lesson-one.md").exists()


class TestLineEndings:
    """LF on every platform (#1488 class).

    Text-mode writes translate LF->CRLF on Windows, which would stamp
    CRLF into tracked LF markdown and trip the mixed-line-ending hook.
    Asserted on RAW BYTES — read_text() would hide it via universal
    newlines, which is exactly why the original bug shipped.
    """

    def test_artifact_bytes_use_lf(self, tmp_path):
        path = write_artifact(
            "lesson", "crlf", "line one\nline two\n", attune_home=tmp_path, now=NOW
        )
        raw = path.read_bytes()
        assert b"\r\n" not in raw
        assert b"line one\nline two\n" in raw

    def test_applied_lesson_append_keeps_lf(self, tmp_path):
        from attune.docs_outbox.sweep import apply_sweep

        repo = tmp_path / "repo"
        (repo / ".claude").mkdir(parents=True)
        (repo / ".git").mkdir()
        corpus = repo / ".claude" / "lessons.md"
        corpus.write_bytes(b"# Lessons\n")
        write_artifact("lesson", "appended", "- A\n- B\n", attune_home=tmp_path, now=NOW)
        apply_sweep(repo, attune_home=tmp_path)
        assert b"\r\n" not in corpus.read_bytes()
