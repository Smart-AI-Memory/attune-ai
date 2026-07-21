"""Unit tests for attune.ops.specs_data — the framework-free spec data layer.

Exercises the defensive branches (unreadable files, stat/glob OSErrors,
missing roots) that the route/curator integration tests don't hit, plus
the happy paths, root resolution, and the SpecRecord lifecycle
computation. Lives here (not in test_specs_routes) precisely because this
module must be importable and testable without FastAPI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.ops.specs_data import (
    SpecPhase,
    SpecRecord,
    _extract_status,
    _list_specs_in_root,
    _newest_md_mtime,
    _resolved_roots,
    _scan_spec_dir,
)


def _make_spec(root: Path, slug: str, *, status: str | None = "draft") -> Path:
    d = root / slug
    d.mkdir(parents=True)
    body = f"**Status:** {status}\n" if status else "no status here\n"
    (d / "decisions.md").write_text(body, encoding="utf-8")
    return d


# --- _extract_status -------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("**Status:** approved", "approved"),  # colon inside the bolding
        ("**Status**: in-review", "in-review"),  # colon outside the bolding
        ("  **Status:**   complete  ", "complete"),  # surrounding whitespace
        ("no status line here", None),
        ("", None),
    ],
)
def test_extract_status(text: str, expected: str | None) -> None:
    assert _extract_status(text) == expected


# --- _scan_spec_dir --------------------------------------------------------


def test_scan_spec_dir_reports_existing_and_missing(tmp_path: Path) -> None:
    (tmp_path / "decisions.md").write_text("**Status:** draft\n", encoding="utf-8")
    phases = {p.name: p for p in _scan_spec_dir(tmp_path)}
    assert phases["decisions"].exists and phases["decisions"].status == "draft"
    assert phases["requirements"].exists is False
    assert phases["requirements"].status is None


def test_scan_spec_dir_unreadable_file_is_statusless(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing-but-unreadable phase file is reported exists=True, status=None."""
    (tmp_path / "decisions.md").write_text("**Status:** draft\n", encoding="utf-8")

    def boom(self: Path, *a: object, **k: object) -> str:
        raise OSError("simulated unreadable file")

    monkeypatch.setattr(Path, "read_text", boom)
    decisions = next(p for p in _scan_spec_dir(tmp_path) if p.name == "decisions")
    assert decisions.exists is True
    assert decisions.status is None


# --- _newest_md_mtime ------------------------------------------------------


def test_newest_md_mtime_returns_iso(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("x", encoding="utf-8")
    out = _newest_md_mtime(tmp_path)
    assert out is not None and "T" in out  # ISO-8601


def test_newest_md_mtime_no_md_files_returns_none(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    assert _newest_md_mtime(tmp_path) is None


def test_newest_md_mtime_per_file_stat_oserror_is_skipped(tmp_path: Path) -> None:
    """A single .md whose stat() raises (broken symlink) is skipped, not fatal.

    glob yields the entry by name, then `md.stat()` follows the dangling
    link and raises FileNotFoundError (an OSError) — the loop must `continue`
    past it and still return the good file's mtime.
    """
    (tmp_path / "good.md").write_text("x", encoding="utf-8")
    broken = tmp_path / "broken.md"
    try:
        broken.symlink_to(tmp_path / "nonexistent-target")
    except (OSError, NotImplementedError):  # pragma: no cover - platform-dependent
        pytest.skip("symlinks not supported on this platform")
    # broken.md is skipped; good.md still yields a timestamp (no crash).
    assert _newest_md_mtime(tmp_path) is not None


def test_newest_md_mtime_glob_oserror_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: Path, *a: object, **k: object) -> object:
        raise OSError("simulated glob failure")

    monkeypatch.setattr(Path, "glob", boom)
    assert _newest_md_mtime(tmp_path) is None


# --- _list_specs_in_root ---------------------------------------------------


def test_list_specs_in_root_missing_root_returns_empty(tmp_path: Path) -> None:
    assert _list_specs_in_root(tmp_path / "does-not-exist") == []


def test_list_specs_in_root_skips_nonspec_dirs_and_files(tmp_path: Path) -> None:
    _make_spec(tmp_path, "real-spec")
    (tmp_path / "loose-file.md").write_text("x", encoding="utf-8")  # a file, not a dir
    nonspec = tmp_path / "not-a-spec"  # a dir with no recognized phase file
    nonspec.mkdir()
    (nonspec / "readme.txt").write_text("x", encoding="utf-8")
    records = _list_specs_in_root(tmp_path)
    assert [r.slug for r in records] == ["real-spec"]


def test_list_specs_in_root_populates_record(tmp_path: Path) -> None:
    _make_spec(tmp_path, "alpha", status="complete")
    (rec,) = _list_specs_in_root(tmp_path)
    assert rec.slug == "alpha"
    assert rec.root == str(tmp_path)
    assert rec.last_modified is not None
    assert rec.lifecycle  # computed in __post_init__


# --- _resolved_roots -------------------------------------------------------


def test_resolved_roots_defaults_to_docs_specs(tmp_path: Path) -> None:
    cfg = type("C", (), {"project_root": tmp_path, "specs_roots": ()})()
    assert _resolved_roots(cfg) == [(tmp_path / "docs" / "specs").resolve()]


def test_resolved_roots_uses_configured(tmp_path: Path) -> None:
    cfg = type(
        "C", (), {"project_root": tmp_path, "specs_roots": (tmp_path / "a", tmp_path / "b")}
    )()
    assert _resolved_roots(cfg) == [(tmp_path / "a").resolve(), (tmp_path / "b").resolve()]


# --- SpecRecord lifecycle --------------------------------------------------


def test_spec_record_computes_lifecycle() -> None:
    rec = SpecRecord(
        slug="x",
        root="/r",
        path="/r/x",
        phases=[SpecPhase(name="tasks", file="tasks.md", exists=True, status="complete")],
        last_modified=None,
    )
    assert isinstance(rec.lifecycle, str) and rec.lifecycle


def test_spec_record_executing_stage_has_no_next_phase_status() -> None:
    """`next_phase` may name a file with no SpecPhase entry (decisions.md).

    The executing stage targets decisions.md, which is not a tracked
    phase — the prefill lookup must exhaust gracefully to None.
    """
    rec = SpecRecord(
        slug="x",
        root="/r",
        path="/r/x",
        phases=[
            SpecPhase(name="requirements", file="requirements.md", exists=True, status="approved"),
            SpecPhase(name="design", file="design.md", exists=True, status="approved"),
            SpecPhase(name="tasks", file="tasks.md", exists=True, status="approved"),
        ],
        last_modified=None,
    )
    assert rec.stage == "executing"
    assert rec.next_phase == "decisions"
    assert rec.next_phase_status is None
