# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Curating sweep (R3): dedupe, lint, digest, apply."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from attune.docs_outbox.store import DIGEST_NAME, list_artifacts, outbox_dir, write_artifact
from attune.docs_outbox.sweep import apply_sweep, run_sweep

NOW = datetime(2026, 8, 6, 14, 32)


def _repo(tmp_path):
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / ".claude" / "lessons.md").write_text("# Lessons\n", encoding="utf-8")
    return root


def _raw(attune_home, name, kind, target, body):
    """Drop an artifact straight on disk, bypassing write_artifact's gate.

    This is the real threat model for lint: the sweep parses `kind` and
    `target` off disk, so hand-authored or post-edited files never pass
    through routing validation.
    """
    from attune.docs_outbox.store import outbox_dir

    path = outbox_dir(attune_home) / name
    path.write_text(
        f"---\nkind: {kind}\nslug: raw\ntarget: {target}\n---\n\n{body}", encoding="utf-8"
    )
    return path


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


def test_lint_rejects_unbulleted_lesson_body(tmp_path):
    """The lessons index anchors on '- **'; a bare entry appends
    cleanly but is invisible to recall (2026-08-11 retro, two swept
    artifacts drifted in exactly this way)."""
    repo = _repo(tmp_path)
    write_artifact("lesson", "bare", "**Title**: no bullet.", attune_home=tmp_path, now=NOW)
    write_artifact(
        "lesson", "prose", "Plain prose.", attune_home=tmp_path, now=NOW + timedelta(minutes=1)
    )
    write_artifact(
        "lesson",
        "good",
        "- **Title**: bulleted.",
        attune_home=tmp_path,
        now=NOW + timedelta(minutes=2),
    )
    result = run_sweep(repo, attune_home=tmp_path)
    for name in ("20260806-1432-lesson-bare.md", "20260806-1433-lesson-prose.md"):
        assert any("must start with '- **'" in i for i in result.lint_issues[name])
    assert "20260806-1434-lesson-good.md" not in result.lint_issues
    changed = apply_sweep(repo, attune_home=tmp_path)
    text = (repo / ".claude" / "lessons.md").read_text(encoding="utf-8")
    assert "bulleted." in text and "no bullet." not in text
    assert changed == [repo / ".claude" / "lessons.md"]
    # The linty pair stays pending rather than being archived as applied.
    assert sorted(a.slug for a in list_artifacts(tmp_path)) == ["bare", "prose"]


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
        "lesson",
        "second",
        "- **B**: Lesson B.",
        attune_home=tmp_path,
        now=NOW + timedelta(minutes=1),
    )
    write_artifact("lesson", "first", "- **A**: Lesson A.", attune_home=tmp_path, now=NOW)
    changed = apply_sweep(repo, attune_home=tmp_path)
    text = (repo / ".claude" / "lessons.md").read_text(encoding="utf-8")
    assert text.index("Lesson A.") < text.index("Lesson B.")
    assert changed == [repo / ".claude" / "lessons.md"]  # deduped paths
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


class TestReviewRegressions:
    """One test per defect found in the 2026-08-06 adversarial review.

    Each reproduces the exact sequence that used to lose or corrupt
    data; see docs/specs/docs-outbox/decisions.md D4.
    """

    def test_unknown_kind_cannot_replace_the_corpus(self, tmp_path):
        """A kind typo ('lessons') used to take the file-REPLACING
        branch and wipe .claude/lessons.md."""
        repo = _repo(tmp_path)
        _raw(tmp_path, "20260806-1432-lesson-typo.md", "lessons", ".claude/lessons.md", "- Body.\n")
        result = run_sweep(repo, attune_home=tmp_path)
        assert any(
            "not an outbox kind" in issue
            for issue in result.lint_issues["20260806-1432-lesson-typo.md"]
        )
        changed = apply_sweep(repo, attune_home=tmp_path)
        assert changed == []
        assert (repo / ".claude" / "lessons.md").read_text(encoding="utf-8") == "# Lessons\n"

    def test_lesson_cannot_target_a_source_file(self, tmp_path):
        """A lesson pointed at src/app.py used to append prose into it.

        Caught by the .md gate, which fires before the default-target
        check — both are asserted, here and in the sibling test.
        """
        repo = _repo(tmp_path)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
        _raw(tmp_path, "20260806-1432-lesson-oops.md", "lesson", "src/app.py", "Prose.\n")
        result = run_sweep(repo, attune_home=tmp_path)
        assert "target must be a .md file" in result.lint_issues["20260806-1432-lesson-oops.md"]
        apply_sweep(repo, attune_home=tmp_path)
        assert (repo / "src" / "app.py").read_text(encoding="utf-8") == "print('hi')\n"

    def test_lesson_cannot_target_another_markdown_file(self, tmp_path):
        """The .md gate is not enough: an appending kind aimed at any
        OTHER tracked .md would still append prose into it."""
        repo = _repo(tmp_path)
        (repo / "docs").mkdir()
        (repo / "docs" / "notes.md").write_text("# Notes\n", encoding="utf-8")
        _raw(tmp_path, "20260806-1432-lesson-astray.md", "lesson", "docs/notes.md", "Prose.\n")
        result = run_sweep(repo, attune_home=tmp_path)
        issues = result.lint_issues["20260806-1432-lesson-astray.md"]
        assert any("must target .claude/lessons.md" in i for i in issues)
        apply_sweep(repo, attune_home=tmp_path)
        assert (repo / "docs" / "notes.md").read_text(encoding="utf-8") == "# Notes\n"

    def test_two_artifacts_claiming_one_new_file_collide_at_lint(self, tmp_path):
        """Both used to lint clean; the second silently overwrote the
        first, and both were archived as applied."""
        repo = _repo(tmp_path)
        write_artifact(
            "report", "first", "FIRST.", target="docs/r.md", attune_home=tmp_path, now=NOW
        )
        write_artifact(
            "report",
            "second",
            "SECOND.",
            target="docs/r.md",
            attune_home=tmp_path,
            now=NOW + timedelta(minutes=1),
        )
        result = run_sweep(repo, attune_home=tmp_path)
        assert "20260806-1432-report-first.md" not in result.lint_issues
        assert any(
            "already claims this target" in i
            for i in result.lint_issues["20260806-1433-report-second.md"]
        )
        apply_sweep(repo, attune_home=tmp_path)
        assert (repo / "docs" / "r.md").read_text(encoding="utf-8") == "FIRST.\n"
        # The loser stays pending rather than being archived as applied.
        assert [a.slug for a in list_artifacts(tmp_path)] == ["second"]

    def test_identical_bodies_to_different_targets_are_not_deduped(self, tmp_path):
        """Dedupe keyed on body alone dropped real work."""
        repo = _repo(tmp_path)
        write_artifact("report", "a", "SHARED.", target="docs/a.md", attune_home=tmp_path, now=NOW)
        write_artifact("report", "b", "SHARED.", target="docs/b.md", attune_home=tmp_path, now=NOW)
        result = run_sweep(repo, attune_home=tmp_path)
        assert result.dropped_duplicates == []
        apply_sweep(repo, attune_home=tmp_path)
        assert (repo / "docs" / "a.md").exists()
        assert (repo / "docs" / "b.md").exists()

    def test_failure_midway_leaves_the_failed_artifact_pending(self, tmp_path):
        """A mid-loop raise used to skip archiving for ALL artifacts,
        so the successful ones re-applied (and duplicated) next run."""
        repo = _repo(tmp_path)
        (repo / "blocker").write_text("i am a file\n", encoding="utf-8")
        write_artifact("lesson", "good", "- **Good lesson.**", attune_home=tmp_path, now=NOW)
        write_artifact(
            "report",
            "bad",
            "Body.",
            target="blocker/sub/x.md",
            attune_home=tmp_path,
            now=NOW + timedelta(minutes=1),
        )
        apply_sweep(repo, attune_home=tmp_path)
        first = (repo / ".claude" / "lessons.md").read_text(encoding="utf-8")
        assert first.count("Good lesson.") == 1
        # The good artifact was archived; only the failing one remains.
        assert [a.slug for a in list_artifacts(tmp_path)] == ["bad"]
        # Re-running must not double-append the already-applied lesson.
        apply_sweep(repo, attune_home=tmp_path)
        assert (repo / ".claude" / "lessons.md").read_text(encoding="utf-8").count(
            "Good lesson."
        ) == 1

    def test_apply_failure_is_reported_not_swallowed(self, tmp_path):
        repo = _repo(tmp_path)
        (repo / "blocker").write_text("i am a file\n", encoding="utf-8")
        write_artifact(
            "report", "bad", "Body.", target="blocker/sub/x.md", attune_home=tmp_path, now=NOW
        )
        result = run_sweep(repo, attune_home=tmp_path)
        apply_sweep(repo, attune_home=tmp_path, result=result)
        assert "20260806-1432-report-bad.md" in result.apply_failures

    def test_digest_is_removed_once_the_outbox_drains(self, tmp_path):
        """A stale digest.md used to linger, so the chip could render an
        already-applied batch."""
        repo = _repo(tmp_path)
        write_artifact("lesson", "one", "- **One**: body.", attune_home=tmp_path, now=NOW)
        run_sweep(repo, attune_home=tmp_path)
        assert (outbox_dir(tmp_path) / DIGEST_NAME).exists()
        apply_sweep(repo, attune_home=tmp_path)
        assert not (outbox_dir(tmp_path) / DIGEST_NAME).exists()

    def test_pipe_in_target_does_not_break_the_digest_table(self, tmp_path):
        repo = _repo(tmp_path)
        _raw(tmp_path, "20260806-1432-report-pipe.md", "report", "docs/a|b.md", "Body.\n")
        result = run_sweep(repo, attune_home=tmp_path)
        row = [ln for ln in result.digest.splitlines() if "report-pipe" in ln][0]
        assert r"a\|b" in row  # escaped, so it cannot open a phantom cell
        # 5 cell borders for 4 columns; the escaped pipe is the 6th.
        assert row.count("|") == 6
        assert len(re.split(r"(?<!\\)\|", row)) == 6  # '' + 4 cells + ''
