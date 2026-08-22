"""Baseline resolution for the release-audit stage (R3 step 0).

The property under test is FAIL-CLOSED. An audit whose range is wrong
reports an empty sweep, which reads exactly like a clean diff — so
every unresolvable input must raise rather than fall back to a default
range.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from attune.classes.baseline import (
    Baseline,
    BaselineError,
    changed_files,
    last_release_tag,
    resolve_baseline,
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return result.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=30)
    for key, value in (
        ("user.email", "t@t"),
        ("user.name", "t"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
    ):
        _git(tmp_path, "config", key, value)
    return tmp_path


def _commit(repo: Path, name: str, body: str = "x = 1\n") -> str:
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"add {name}")
    return _git(repo, "rev-parse", "HEAD")


class TestResolvesTheRange:
    def test_uses_the_last_release_tag(self, tmp_path):
        repo = _repo(tmp_path)
        _commit(repo, "a.py")
        _git(repo, "tag", "v1.0.0")
        head = _commit(repo, "b.py")

        baseline = resolve_baseline(repo)

        assert baseline.tag == "v1.0.0"
        assert baseline.source == "last-release-tag"
        assert baseline.head_sha == head
        assert len(baseline.baseline_sha) == 40, "SHAs are recorded full-length for the manifest"
        assert baseline.changed == ("b.py",)

    def test_override_skips_tag_lookup_entirely(self, tmp_path):
        """--baseline names the range; an untagged repo must still work."""
        repo = _repo(tmp_path)
        first = _commit(repo, "a.py")
        _commit(repo, "b.py")

        baseline = resolve_baseline(repo, override=first)

        assert baseline.source == "override"
        assert baseline.tag is None
        assert baseline.baseline_sha == first
        assert baseline.changed == ("b.py",)

    def test_tag_is_picked_by_VERSION_not_commit_date(self, tmp_path):
        """A tag pushed late for an older release must not win."""
        repo = _repo(tmp_path)
        _commit(repo, "a.py")
        _git(repo, "tag", "v2.0.0")
        _commit(repo, "b.py")
        # v1.9.0 is created LAST, so a date-ordered lookup would pick it.
        _git(repo, "tag", "v1.9.0")

        assert last_release_tag(repo) == "v2.0.0"

    def test_non_release_tags_are_ignored(self, tmp_path):
        repo = _repo(tmp_path)
        _commit(repo, "a.py")
        _git(repo, "tag", "nightly-2026-08-22")
        _git(repo, "tag", "v0.1.0")
        _git(repo, "tag", "v1.0.0-rc1")

        assert last_release_tag(repo) == "v0.1.0"

    def test_tag_range_is_readable(self, tmp_path):
        repo = _repo(tmp_path)
        _commit(repo, "a.py")
        _git(repo, "tag", "v1.0.0")
        _commit(repo, "b.py")

        assert resolve_baseline(repo).tag_range.startswith("v1.0.0..")


class TestFailsClosed:
    """Never guess a range — an empty sweep must mean a clean diff."""

    def test_no_release_tag_raises(self, tmp_path):
        repo = _repo(tmp_path)
        _commit(repo, "a.py")

        with pytest.raises(BaselineError) as exc:
            resolve_baseline(repo)

        assert exc.value.reason == "no-release-tag"
        assert "--baseline" in str(exc.value), "the error must name the way forward"

    def test_unresolvable_override_raises(self, tmp_path):
        repo = _repo(tmp_path)
        _commit(repo, "a.py")

        with pytest.raises(BaselineError) as exc:
            resolve_baseline(repo, override="no-such-ref")

        assert exc.value.reason == "bad-baseline-ref"

    def test_shallow_clone_raises(self, tmp_path):
        origin = _repo(tmp_path / "origin")
        _commit(origin, "a.py")
        _git(origin, "tag", "v1.0.0")
        _commit(origin, "b.py")

        shallow = tmp_path / "shallow"
        subprocess.run(
            ["git", "clone", "-q", "--depth", "1", f"file://{origin}", str(shallow)],
            check=True,
            timeout=60,
        )

        with pytest.raises(BaselineError) as exc:
            resolve_baseline(shallow)

        assert exc.value.reason == "shallow-clone"

    def test_not_a_repo_raises_rather_than_returning_empty(self, tmp_path):
        with pytest.raises(BaselineError):
            resolve_baseline(tmp_path)


class TestChangedFileSemantics:
    """R1: deleted skipped, rename scans the NEW path, unscannable filtered."""

    def test_deleted_file_is_skipped(self, tmp_path):
        repo = _repo(tmp_path)
        _commit(repo, "gone.py")
        base = _git(repo, "rev-parse", "HEAD")
        (repo / "gone.py").unlink()
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "delete")

        assert changed_files(repo, base) == ()

    def test_rename_scans_the_new_path(self, tmp_path):
        repo = _repo(tmp_path)
        _commit(repo, "old.py", "x = 1\n" * 20)
        base = _git(repo, "rev-parse", "HEAD")
        _git(repo, "mv", "old.py", "new.py")
        _git(repo, "commit", "-q", "-m", "rename")

        assert changed_files(repo, base) == ("new.py",)

    def test_unscannable_files_are_filtered(self, tmp_path):
        repo = _repo(tmp_path)
        _commit(repo, "a.py")
        base = _git(repo, "rev-parse", "HEAD")
        _commit(repo, "notes.md", "# notes\n")
        (repo / "data.json").write_text("{}", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "non-python")

        assert changed_files(repo, base) == ()

    def test_order_is_deterministic_and_deduped(self, tmp_path):
        """A packet hash must be stable across runs of the same range."""
        repo = _repo(tmp_path)
        _commit(repo, "a.py")
        base = _git(repo, "rev-parse", "HEAD")
        _commit(repo, "z.py")
        _commit(repo, "m.py")
        _commit(repo, "z.py", "x = 2\n")  # touched twice

        result = changed_files(repo, base)

        assert result == ("m.py", "z.py")
        assert result == changed_files(repo, base), "repeated calls must agree"


class TestBaselineShape:
    def test_is_frozen_so_a_recorded_range_cannot_drift(self):
        baseline = Baseline(tag="v1.0.0", baseline_sha="a" * 40, head_sha="b" * 40, source="t")

        with pytest.raises(AttributeError):
            baseline.baseline_sha = "c" * 40  # type: ignore[misc]
