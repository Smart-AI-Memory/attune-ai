"""Tests for the specs source reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.curator.sources import specs as specs_source


def _make_spec(specs_root: Path, slug: str, *, status: str = "approved") -> None:
    spec_dir = specs_root / slug
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "requirements.md").write_text(
        f"# {slug}\n\n**Status:** {status}\n\nBody.\n",
        encoding="utf-8",
    )
    (spec_dir / "tasks.md").write_text(
        f"# Tasks\n\n**Status:** {status}\n\n- [ ] something\n",
        encoding="utf-8",
    )


@pytest.fixture
def project_with_specs(tmp_path):
    """Create a tmp project with docs/specs/<3 specs>."""
    specs_root = tmp_path / "docs" / "specs"
    _make_spec(specs_root, "alpha", status="approved")
    _make_spec(specs_root, "beta", status="draft")
    _make_spec(specs_root, "gamma", status="complete")
    return tmp_path


def test_lists_specs_with_status(project_with_specs, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(project_with_specs / ".attune"))
    summary = specs_source.read(project_root=project_with_specs)
    assert summary.source_id == "specs"
    ids = {item.item_id for item in summary.items}
    assert ids == {"spec:alpha", "spec:beta", "spec:gamma"}
    statuses = {item.item_id: item.metadata["status"] for item in summary.items}
    assert statuses == {
        "spec:alpha": "approved",
        "spec:beta": "draft",
        "spec:gamma": "complete",
    }


def test_links_use_spec_slug(project_with_specs, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(project_with_specs / ".attune"))
    summary = specs_source.read(project_root=project_with_specs)
    for item in summary.items:
        slug = item.item_id.split(":", 1)[1]
        assert item.link == f"/specs/{slug}"


def test_age_days_present_for_existing_specs(project_with_specs, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(project_with_specs / ".attune"))
    summary = specs_source.read(project_root=project_with_specs)
    for item in summary.items:
        # Newly-created files: age_days should be 0.
        assert item.metadata["age_days"] in ("0", "1")  # tolerate tz edge


def test_completion_candidate_flag_defaults_false(project_with_specs, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(project_with_specs / ".attune"))
    summary = specs_source.read(project_root=project_with_specs)
    flags = {item.metadata["is_completion_candidate"] for item in summary.items}
    # Without GitHub access / PR refs, every spec is "false" — that's
    # the safe default the reader guarantees when detection skips.
    assert flags == {"false"}


def test_state_hash_stable_across_calls(project_with_specs, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(project_with_specs / ".attune"))
    a = specs_source.read(project_root=project_with_specs).state_hash
    b = specs_source.read(project_root=project_with_specs).state_hash
    assert a == b


def test_missing_specs_dir_returns_empty_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    summary = specs_source.read(project_root=tmp_path)
    assert summary.source_id == "specs"
    assert summary.items == []


def test_reader_does_not_raise_when_detect_candidates_blows_up(project_with_specs, monkeypatch):
    """If completion-candidate detection raises, the reader still
    returns spec status + age — just with is_completion_candidate=false."""
    monkeypatch.setenv("ATTUNE_HOME", str(project_with_specs / ".attune"))

    def boom(*args, **kwargs):
        raise RuntimeError("simulated detector failure")

    monkeypatch.setattr(
        "attune.ops.completion_candidates.detect_candidates",
        boom,
    )
    summary = specs_source.read(project_root=project_with_specs)
    assert len(summary.items) == 3
    for item in summary.items:
        assert item.metadata["is_completion_candidate"] == "false"


def test_list_specs_raise_returns_empty(project_with_specs, monkeypatch):
    """If _list_specs_in_root raises, reader returns empty summary."""
    monkeypatch.setenv("ATTUNE_HOME", str(project_with_specs / ".attune"))

    def boom(*args, **kwargs):
        raise RuntimeError("simulated listing failure")

    monkeypatch.setattr(
        "attune.curator.sources.specs._list_specs_in_root",
        boom,
    )
    summary = specs_source.read(project_root=project_with_specs)
    assert summary.source_id == "specs"
    assert summary.items == []
    assert len(summary.state_hash) == 16


def test_spec_without_any_status_falls_through(project_with_specs, monkeypatch):
    """A spec dir whose phase files all lack '**Status:**' lines yields
    metadata.status='unknown'."""
    monkeypatch.setenv("ATTUNE_HOME", str(project_with_specs / ".attune"))
    silent = project_with_specs / "docs" / "specs" / "silent"
    silent.mkdir(parents=True, exist_ok=True)
    (silent / "tasks.md").write_text(
        "# Tasks\n\nNo status line here.\n\n- [ ] todo\n",
        encoding="utf-8",
    )
    summary = specs_source.read(project_root=project_with_specs)
    silent_items = [i for i in summary.items if i.item_id == "spec:silent"]
    assert silent_items
    assert silent_items[0].metadata["status"] == "unknown"


def test_age_days_none_when_no_last_modified():
    """Direct unit test of the _age_days helper: empty input -> None."""
    import attune.curator.sources.specs as spec_mod

    assert spec_mod._age_days(None) is None
    assert spec_mod._age_days("") is None


def test_age_days_returns_none_on_bad_iso():
    """_age_days swallows fromisoformat ValueError and returns None."""
    import attune.curator.sources.specs as spec_mod

    assert spec_mod._age_days("not-an-iso-string") is None


def test_age_days_handles_naive_datetime():
    """A naive datetime (no tz) gets UTC-coerced before delta math."""
    from datetime import datetime, timedelta, timezone

    import attune.curator.sources.specs as spec_mod

    naive_yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).replace(tzinfo=None)
    days = spec_mod._age_days(naive_yesterday.isoformat())
    assert days is not None and days >= 1


def test_empty_summary_helper():
    """_empty_summary returns the canonical empty SourceSummary."""
    import attune.curator.sources.specs as spec_mod

    summary = spec_mod._empty_summary(started=0.0)
    assert summary.source_id == "specs"
    assert summary.items == []
    assert len(summary.state_hash) == 16
