"""Behavioral + mutation-resistant tests for MemDocsStorage.

Covers the file-based long-term storage backend in
memory/storage_backend.py (no prior dedicated test file; 57% line
coverage from incidental hits).

Design notes:

- Real filesystem via tmp_path — no mock-the-filesystem theatre; the
  JSON round-trips through actual ``open``/``json``.
- Exact-content assertions on the written/read pattern dict kill
  return-value and key-name mutants.
- Error branches (store re-raise, retrieve-on-corrupt -> None,
  delete-failure -> False, list skips corrupt files) are each
  triggered deterministically.
- list_patterns filters are tested from both sides (matching kept,
  non-matching dropped, ``None`` filter keeps all) so the ``!=`` and
  ``and`` short-circuit mutants die.
"""

import json

import pytest

from attune.memory.storage_backend import MemDocsStorage


@pytest.fixture
def storage(tmp_path):
    """MemDocsStorage rooted in an isolated temp directory."""
    return MemDocsStorage(storage_dir=str(tmp_path / "memdocs"))


# ===========================================================================
# __init__
# ===========================================================================


def test_init_creates_storage_dir(tmp_path):
    """Initialization creates the storage directory if absent."""
    target = tmp_path / "fresh" / "nested"
    assert not target.exists()
    store = MemDocsStorage(storage_dir=str(target))
    assert store.storage_dir.is_dir()


def test_init_is_idempotent_on_existing_dir(tmp_path):
    """Re-initializing on an existing directory does not raise."""
    path = str(tmp_path / "reuse")
    MemDocsStorage(storage_dir=path)
    # Second init must not fail (exist_ok=True).
    MemDocsStorage(storage_dir=path)


# ===========================================================================
# store
# ===========================================================================


def test_store_returns_true_on_success(storage):
    """store returns True when the pattern is written."""
    assert storage.store("p1", "content", {"created_by": "alice"}) is True


def test_store_writes_exact_pattern_structure(storage):
    """The on-disk JSON has exactly the documented shape and values."""
    storage.store("p1", "the content", {"k": "v"})
    written = json.loads((storage.storage_dir / "p1.json").read_text(encoding="utf-8"))
    assert written == {
        "pattern_id": "p1",
        "content": "the content",
        "metadata": {"k": "v"},
    }


def test_store_then_retrieve_round_trips(storage):
    """A stored pattern is retrievable with identical data."""
    storage.store("p1", "abc", {"created_by": "bob"})
    assert storage.retrieve("p1") == {
        "pattern_id": "p1",
        "content": "abc",
        "metadata": {"created_by": "bob"},
    }


def test_store_reraises_on_write_failure(storage, monkeypatch):
    """A write error is logged and re-raised, not swallowed."""

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("attune.memory.storage_backend.json.dump", boom)
    with pytest.raises(OSError, match="disk full"):
        storage.store("p1", "content", {})


# ===========================================================================
# retrieve
# ===========================================================================


def test_retrieve_missing_returns_none(storage):
    """Retrieving an unknown pattern returns None."""
    assert storage.retrieve("does-not-exist") is None


def test_retrieve_corrupt_json_returns_none(storage):
    """Corrupt JSON on disk yields None (decode error caught)."""
    (storage.storage_dir / "bad.json").write_text("{not valid json", encoding="utf-8")
    assert storage.retrieve("bad") is None


# ===========================================================================
# delete
# ===========================================================================


def test_delete_existing_returns_true_and_removes_file(storage):
    """Deleting an existing pattern returns True and removes the file."""
    storage.store("p1", "x", {})
    assert storage.delete("p1") is True
    assert not (storage.storage_dir / "p1.json").exists()


def test_delete_missing_returns_false(storage):
    """Deleting an unknown pattern returns False."""
    assert storage.delete("nope") is False


def test_delete_failure_returns_false(storage, monkeypatch):
    """An unlink error is caught and reported as False, not raised."""
    storage.store("p1", "x", {})

    def boom(*_args, **_kwargs):
        raise OSError("locked")

    monkeypatch.setattr("pathlib.Path.unlink", boom)
    assert storage.delete("p1") is False


# ===========================================================================
# list_patterns
# ===========================================================================


def test_list_empty_returns_empty_list(storage):
    """Listing an empty store returns an empty list."""
    assert storage.list_patterns() == []


def test_list_all_when_no_filters(storage):
    """With no filters, every stored pattern id is returned."""
    storage.store("p1", "a", {})
    storage.store("p2", "b", {})
    assert sorted(storage.list_patterns()) == ["p1", "p2"]


def test_list_filters_by_classification(storage):
    """classification filter keeps matches, drops non-matches."""
    storage.store("pub", "a", {"classification": "PUBLIC"})
    storage.store("sec", "b", {"classification": "SENSITIVE"})
    assert storage.list_patterns(classification="SENSITIVE") == ["sec"]


def test_list_filters_by_created_by(storage):
    """created_by filter keeps matches, drops non-matches."""
    storage.store("p1", "a", {"created_by": "alice"})
    storage.store("p2", "b", {"created_by": "bob"})
    assert storage.list_patterns(created_by="alice") == ["p1"]


def test_list_combines_both_filters(storage):
    """Both filters apply conjunctively."""
    storage.store("hit", "a", {"classification": "PUBLIC", "created_by": "alice"})
    storage.store("miss1", "b", {"classification": "PUBLIC", "created_by": "bob"})
    storage.store("miss2", "c", {"classification": "SENSITIVE", "created_by": "alice"})
    assert storage.list_patterns(classification="PUBLIC", created_by="alice") == ["hit"]


def test_list_none_filter_keeps_patterns_without_that_field(storage):
    """A None filter must not exclude patterns lacking the field."""
    storage.store("p1", "a", {})  # no classification / created_by keys
    assert storage.list_patterns() == ["p1"]


def test_list_skips_corrupt_files(storage):
    """A corrupt file is skipped; valid patterns are still returned."""
    storage.store("good", "a", {})
    (storage.storage_dir / "bad.json").write_text("{broken", encoding="utf-8")
    assert storage.list_patterns() == ["good"]
