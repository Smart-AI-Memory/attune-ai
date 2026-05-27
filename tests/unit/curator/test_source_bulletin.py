"""Tests for the bulletin source reader."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.bulletin.file_backend import FileBulletinBackend
from attune.bulletin.protocol import BulletinEntry
from attune.curator.sources import bulletin as bulletin_source


def _seed_active(root: Path, entries: list[BulletinEntry]) -> None:
    backend = FileBulletinBackend(root)
    for entry in entries:
        backend.append(entry)


def _seed_archive(root: Path, date_iso: str, entries: list[BulletinEntry]) -> None:
    archive = root / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    path = archive / f"{date_iso}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry.to_dict()) + "\n")


@pytest.fixture
def bulletin_home(tmp_path, monkeypatch):
    """Point attune_home() at a temp dir so tests don't touch ~/.attune."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    return tmp_path / "bulletin"


def _make_entry(
    *,
    run_id: str = "r1",
    workflow: str = "code-review",
    actor_kind: str = "cli",
    heartbeat: datetime | None = None,
    status: str = "running",
    scope: str | None = None,
) -> BulletinEntry:
    now = datetime.now(timezone.utc)
    hb = heartbeat or now
    return BulletinEntry(
        actor_id="actor-1",
        actor_kind=actor_kind,  # type: ignore[arg-type]
        workflow=workflow,
        run_id=run_id,
        started_at=(hb - timedelta(seconds=10)).isoformat(),
        last_heartbeat=hb.isoformat(),
        current_status=status,  # type: ignore[arg-type]
        scope=scope,
    )


def test_empty_bulletin_returns_empty_summary(tmp_path, bulletin_home):
    summary = bulletin_source.read(project_root=tmp_path)
    assert summary.source_id == "bulletin"
    assert summary.items == []
    # Stable hash on empty input.
    assert isinstance(summary.state_hash, str) and len(summary.state_hash) == 16


def test_active_entries_become_source_items(tmp_path, bulletin_home):
    _seed_active(
        bulletin_home,
        [
            _make_entry(run_id="r1", workflow="code-review"),
            _make_entry(run_id="r2", workflow="security-audit", actor_kind="dashboard"),
        ],
    )
    summary = bulletin_source.read(project_root=tmp_path)
    assert len(summary.items) == 2
    ids = {item.item_id for item in summary.items}
    assert ids == {"bulletin:active:r1", "bulletin:active:r2"}
    for item in summary.items:
        assert item.metadata["kind"] == "active"
        assert item.metadata["heartbeat_age_s"].isdigit()
        assert (
            item.link
            == f"/runs/{item.metadata.get('workflow') and item.item_id.split(':')[-1]}/view"
        )


def test_state_hash_stable_across_calls(tmp_path, bulletin_home):
    _seed_active(bulletin_home, [_make_entry(run_id="r1")])
    a = bulletin_source.read(project_root=tmp_path).state_hash
    b = bulletin_source.read(project_root=tmp_path).state_hash
    assert a == b


def test_state_hash_changes_on_new_heartbeat(tmp_path, bulletin_home):
    _seed_active(bulletin_home, [_make_entry(run_id="r1")])
    first = bulletin_source.read(project_root=tmp_path).state_hash
    # Append another heartbeat for the same run with a later timestamp.
    later = datetime.now(timezone.utc) + timedelta(seconds=5)
    _seed_active(
        bulletin_home,
        [_make_entry(run_id="r1", heartbeat=later)],
    )
    second = bulletin_source.read(project_root=tmp_path).state_hash
    assert first != second


def test_archive_filter_respects_since(tmp_path, bulletin_home):
    today = datetime.now(timezone.utc).date()
    older = (today - timedelta(days=5)).isoformat()
    recent = (today - timedelta(days=1)).isoformat()
    _seed_archive(
        bulletin_home,
        older,
        [_make_entry(run_id="old", status="completed")],
    )
    _seed_archive(
        bulletin_home,
        recent,
        [_make_entry(run_id="new", status="completed")],
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    summary = bulletin_source.read(project_root=tmp_path, since=cutoff)
    ids = {item.item_id for item in summary.items}
    assert "bulletin:archived:new" in ids
    assert "bulletin:archived:old" not in ids


def test_missing_archive_dir_does_not_raise(tmp_path, bulletin_home):
    # No archive/ created — only an active log.
    _seed_active(bulletin_home, [_make_entry(run_id="r1")])
    summary = bulletin_source.read(project_root=tmp_path)
    # Should include only the active entry, no errors from missing archive.
    assert any(item.item_id == "bulletin:active:r1" for item in summary.items)


def test_archived_items_carry_terminal_status(tmp_path, bulletin_home):
    today_iso = datetime.now(timezone.utc).date().isoformat()
    _seed_archive(
        bulletin_home,
        today_iso,
        [_make_entry(run_id="r1", status="failed")],
    )
    summary = bulletin_source.read(project_root=tmp_path)
    archived = [i for i in summary.items if i.metadata["kind"] == "archived"]
    assert len(archived) == 1
    assert archived[0].metadata["terminal_status"] == "failed"


def test_reader_never_raises_on_unreadable_dir(tmp_path, bulletin_home, monkeypatch):
    # Force read_active to raise; reader must swallow and return empty active items.
    def boom(*args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(FileBulletinBackend, "read_active", boom)
    summary = bulletin_source.read(project_root=tmp_path)
    assert summary.source_id == "bulletin"
    assert summary.items == []  # Nothing to show; no crash.
