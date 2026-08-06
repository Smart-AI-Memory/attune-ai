# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Curating sweep (R3): dedupe, lint, digest, apply."""

from __future__ import annotations

from datetime import datetime, timedelta

from attune.docs_outbox.store import DIGEST_NAME, list_artifacts, outbox_dir, write_artifact
from attune.docs_outbox.sweep import apply_sweep, run_sweep

NOW = datetime(2026, 8, 6, 14, 32)


def _repo(tmp_path):
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "lessons.md").write_text("# Lessons\n", encoding="utf-8")
    return root


def test_empty_outbox_sweep(tmp_path):
    result = run_sweep(_repo(tmp_path), attune_home=tmp_path)
    assert result.kept == []
    assert "empty" in result.digest
    assert not (outbox_dir(tmp_path) / DIGEST_NAME).exists()


def test_exact_duplicates_dropped_keep_earliest(tmp_path):
    write_artifact("lesson", "dup", "Same body.", attune_home=tmp_path, now=NOW)
    write_artifact(
        "lesson", "dup-again", "Same body.", attune_home=tmp_path, now=NOW + timedelta(minutes=1)
    )
    result = run_sweep(_repo(tmp_path), attune_home=tmp_path)
    assert [a.slug for a in result.kept] == ["dup"]
    assert [a.slug for a in result.dropped_duplicates] == ["dup-again"]
    assert "exact duplicate" in result.digest


def test_related_slugs_flagged(tmp_path):
    write_artifact("lesson", "same", "Body one.", attune_home=tmp_path, now=NOW)
    write_artifact(
        "lesson", "same", "Body two.", attune_home=tmp_path, now=NOW + timedelta(minutes=1)
    )
    result = run_sweep(_repo(tmp_path), attune_home=tmp_path)
    assert result.related_slugs == ["lesson/same"]
    assert "related-slug" in result.digest


def test_core_worthy_flagging(tmp_path):
    write_artifact("lesson", "leaky", "A secret key leaked.", attune_home=tmp_path, now=NOW)
    write_artifact("lesson", "benign", "Plain formatting note.", attune_home=tmp_path, now=NOW)
    result = run_sweep(_repo(tmp_path), attune_home=tmp_path)
    assert result.core_worthy == ["20260806-1432-lesson-leaky.md"]
    assert "core-worthy?" in result.digest


def test_lint_rejects_escaping_target(tmp_path):
    write_artifact(
        "report", "escape", "Body.", target="../outside.md", attune_home=tmp_path, now=NOW
    )
    result = run_sweep(_repo(tmp_path), attune_home=tmp_path)
    issues = result.lint_issues["20260806-1432-report-escape.md"]
    assert any("target rejected" in issue for issue in issues)
    assert not result.clean


def test_lint_rejects_absolute_target_and_overwrite(tmp_path):
    repo = _repo(tmp_path)
    (repo / "docs").mkdir()
    (repo / "docs" / "existing.md").write_text("x\n", encoding="utf-8")
    write_artifact("report", "abs", "Body.", target="/etc/passwd", attune_home=tmp_path, now=NOW)
    write_artifact(
        "report", "clobber", "Body two.", target="docs/existing.md", attune_home=tmp_path, now=NOW
    )
    result = run_sweep(repo, attune_home=tmp_path)
    assert "target must be repo-relative" in result.lint_issues["20260806-1432-report-abs.md"]
    assert any(
        "refusing overwrite" in issue
        for issue in result.lint_issues["20260806-1432-report-clobber.md"]
    )


def test_sweep_writes_digest_file(tmp_path):
    write_artifact("lesson", "one", "Body.", attune_home=tmp_path, now=NOW)
    result = run_sweep(_repo(tmp_path), attune_home=tmp_path)
    digest_path = outbox_dir(tmp_path) / DIGEST_NAME
    assert digest_path.read_text(encoding="utf-8") == result.digest
    assert "1 pending" in result.digest


def test_stale_warning_in_digest(tmp_path):
    write_artifact(
        "lesson", "old", "Body.", attune_home=tmp_path, now=datetime.now() - timedelta(days=3)
    )
    result = run_sweep(_repo(tmp_path), attune_home=tmp_path)
    assert "STALE" in result.digest


def test_apply_appends_lessons_in_timestamp_order_and_archives(tmp_path):
    repo = _repo(tmp_path)
    write_artifact(
        "lesson", "second", "- Lesson B.", attune_home=tmp_path, now=NOW + timedelta(minutes=1)
    )
    write_artifact("lesson", "first", "- Lesson A.", attune_home=tmp_path, now=NOW)
    changed = apply_sweep(repo, attune_home=tmp_path)
    text = (repo / ".claude" / "lessons.md").read_text(encoding="utf-8")
    assert text.index("Lesson A.") < text.index("Lesson B.")
    assert changed == [repo / ".claude" / "lessons.md"] * 2
    assert list_artifacts(tmp_path) == []  # everything swept


def test_apply_creates_report_file(tmp_path):
    repo = _repo(tmp_path)
    write_artifact(
        "report", "round", "Report body.", target="docs/reports/r.md", attune_home=tmp_path, now=NOW
    )
    changed = apply_sweep(repo, attune_home=tmp_path)
    assert changed == [repo / "docs" / "reports" / "r.md"]
    assert (repo / "docs" / "reports" / "r.md").read_text(encoding="utf-8") == "Report body.\n"


def test_apply_skips_linty_artifacts_and_leaves_them_pending(tmp_path):
    repo = _repo(tmp_path)
    write_artifact("report", "bad", "Body.", target="../escape.md", attune_home=tmp_path, now=NOW)
    changed = apply_sweep(repo, attune_home=tmp_path)
    assert changed == []
    assert len(list_artifacts(tmp_path)) == 1  # still pending, untouched
