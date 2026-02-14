"""Tests for LongTermMemory simple storage (simple_storage.py)

Covers:
- CRUD operations (store, retrieve, update, delete)
- File persistence across instances
- Classification support (PUBLIC/INTERNAL/SENSITIVE)
- Edge cases (missing keys, empty storage, invalid inputs)
- Security (path traversal prevention, null bytes)
- list_keys with and without classification filter
- clear operation

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from pathlib import Path

import pytest

from attune.memory.long_term_types import Classification
from attune.memory.simple_storage import LongTermMemory


@pytest.mark.unit
class TestStore:
    """Tests for LongTermMemory.store()."""

    def test_store_simple_value(self, tmp_path: "Path") -> None:
        """Test storing a simple dict value returns True."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        result = memory.store("my_key", {"hello": "world"})
        assert result is True

    def test_store_creates_json_file(self, tmp_path: "Path") -> None:
        """Test that store creates a JSON file named after the key."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("config", {"setting": 1})

        json_file = storage_dir / "config.json"
        assert json_file.exists()

        with json_file.open(encoding="utf-8") as f:
            record = json.load(f)

        assert record["key"] == "config"
        assert record["data"] == {"setting": 1}
        assert "created_at" in record
        assert "updated_at" in record

    def test_store_default_classification_is_internal(self, tmp_path: "Path") -> None:
        """Test that the default classification is INTERNAL when none given."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("item", {"value": 42})

        with (storage_dir / "item.json").open(encoding="utf-8") as f:
            record = json.load(f)

        assert record["classification"] == "INTERNAL"

    def test_store_with_string_classification(self, tmp_path: "Path") -> None:
        """Test storing with a string classification value."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("pub", {"data": 1}, classification="PUBLIC")

        with (storage_dir / "pub.json").open(encoding="utf-8") as f:
            record = json.load(f)

        assert record["classification"] == "PUBLIC"

    def test_store_with_enum_classification(self, tmp_path: "Path") -> None:
        """Test storing with a Classification enum value."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("secret", {"data": 1}, classification=Classification.SENSITIVE)

        with (storage_dir / "secret.json").open(encoding="utf-8") as f:
            record = json.load(f)

        assert record["classification"] == "SENSITIVE"

    def test_store_with_invalid_classification_falls_back_to_internal(
        self, tmp_path: "Path"
    ) -> None:
        """Test that an invalid classification string falls back to INTERNAL."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("item", {"val": 1}, classification="BOGUS")

        with (storage_dir / "item.json").open(encoding="utf-8") as f:
            record = json.load(f)

        assert record["classification"] == "INTERNAL"

    def test_store_various_json_serializable_types(self, tmp_path: "Path") -> None:
        """Test storing different JSON-serializable data types."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))

        assert memory.store("string_val", "hello") is True
        assert memory.store("int_val", 42) is True
        assert memory.store("float_val", 3.14) is True
        assert memory.store("list_val", [1, 2, 3]) is True
        assert memory.store("bool_val", True) is True
        assert memory.store("null_val", None) is True

    def test_store_non_serializable_raises_type_error(self, tmp_path: "Path") -> None:
        """Test that non-JSON-serializable data raises TypeError."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))

        with pytest.raises(TypeError):
            memory.store("bad", {1, 2, 3})  # sets are not JSON serializable

    def test_store_empty_key_raises_value_error(self, tmp_path: "Path") -> None:
        """Test that an empty key raises ValueError."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))

        with pytest.raises(ValueError, match="key cannot be empty"):
            memory.store("", {"data": 1})

    def test_store_whitespace_only_key_raises_value_error(self, tmp_path: "Path") -> None:
        """Test that a whitespace-only key raises ValueError."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))

        with pytest.raises(ValueError, match="key cannot be empty"):
            memory.store("   ", {"data": 1})

    def test_store_overwrites_existing_key(self, tmp_path: "Path") -> None:
        """Test that storing with the same key overwrites the previous value."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("key1", {"version": 1})
        memory.store("key1", {"version": 2})

        result = memory.retrieve("key1")
        assert result == {"version": 2}

    def test_store_classification_case_insensitive(self, tmp_path: "Path") -> None:
        """Test that lowercase classification strings are normalized to uppercase."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("item", {"v": 1}, classification="public")

        with (storage_dir / "item.json").open(encoding="utf-8") as f:
            record = json.load(f)

        assert record["classification"] == "PUBLIC"


@pytest.mark.unit
class TestRetrieve:
    """Tests for LongTermMemory.retrieve()."""

    def test_retrieve_stored_value(self, tmp_path: "Path") -> None:
        """Test retrieving a previously stored value."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("key1", {"value": 42})

        result = memory.retrieve("key1")
        assert result == {"value": 42}

    def test_retrieve_missing_key_returns_none(self, tmp_path: "Path") -> None:
        """Test that retrieving a non-existent key returns None."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        result = memory.retrieve("nonexistent")
        assert result is None

    def test_retrieve_empty_key_raises_value_error(self, tmp_path: "Path") -> None:
        """Test that retrieving with an empty key raises ValueError."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))

        with pytest.raises(ValueError, match="key cannot be empty"):
            memory.retrieve("")

    def test_retrieve_whitespace_key_raises_value_error(self, tmp_path: "Path") -> None:
        """Test that retrieving with a whitespace-only key raises ValueError."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))

        with pytest.raises(ValueError, match="key cannot be empty"):
            memory.retrieve("   ")

    def test_retrieve_corrupted_json_returns_none(self, tmp_path: "Path") -> None:
        """Test that a corrupted JSON file causes retrieve to return None."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))

        # Write invalid JSON directly to the file
        bad_file = storage_dir / "broken.json"
        bad_file.write_text("NOT VALID JSON {{{", encoding="utf-8")

        result = memory.retrieve("broken")
        assert result is None

    def test_retrieve_returns_data_field_only(self, tmp_path: "Path") -> None:
        """Test that retrieve returns only the 'data' field, not the full record."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("key1", "just_a_string")

        result = memory.retrieve("key1")
        assert result == "just_a_string"


@pytest.mark.unit
class TestDelete:
    """Tests for LongTermMemory.delete()."""

    def test_delete_existing_key(self, tmp_path: "Path") -> None:
        """Test deleting an existing key returns True and removes the file."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("to_delete", {"temp": True})

        assert (storage_dir / "to_delete.json").exists()

        result = memory.delete("to_delete")
        assert result is True
        assert not (storage_dir / "to_delete.json").exists()

    def test_delete_nonexistent_key_returns_false(self, tmp_path: "Path") -> None:
        """Test deleting a non-existent key returns False."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        result = memory.delete("ghost")
        assert result is False

    def test_delete_empty_key_raises_value_error(self, tmp_path: "Path") -> None:
        """Test that deleting with an empty key raises ValueError."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))

        with pytest.raises(ValueError, match="key cannot be empty"):
            memory.delete("")

    def test_delete_then_retrieve_returns_none(self, tmp_path: "Path") -> None:
        """Test that retrieving a deleted key returns None."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("ephemeral", {"data": 1})
        memory.delete("ephemeral")

        result = memory.retrieve("ephemeral")
        assert result is None


@pytest.mark.unit
class TestListKeys:
    """Tests for LongTermMemory.list_keys()."""

    def test_list_keys_empty_storage(self, tmp_path: "Path") -> None:
        """Test listing keys when storage is empty returns empty list."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        result = memory.list_keys()
        assert result == []

    def test_list_keys_returns_all_keys(self, tmp_path: "Path") -> None:
        """Test that list_keys returns all stored keys without a filter."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("alpha", 1)
        memory.store("beta", 2)
        memory.store("gamma", 3)

        keys = memory.list_keys()
        assert sorted(keys) == ["alpha", "beta", "gamma"]

    def test_list_keys_filtered_by_string_classification(self, tmp_path: "Path") -> None:
        """Test filtering keys by classification string."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("pub1", 1, classification="PUBLIC")
        memory.store("pub2", 2, classification="PUBLIC")
        memory.store("int1", 3, classification="INTERNAL")

        public_keys = memory.list_keys(classification="PUBLIC")
        assert sorted(public_keys) == ["pub1", "pub2"]

    def test_list_keys_filtered_by_enum_classification(self, tmp_path: "Path") -> None:
        """Test filtering keys by Classification enum."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("s1", 1, classification=Classification.SENSITIVE)
        memory.store("s2", 2, classification=Classification.SENSITIVE)
        memory.store("i1", 3, classification=Classification.INTERNAL)

        sensitive_keys = memory.list_keys(classification=Classification.SENSITIVE)
        assert sorted(sensitive_keys) == ["s1", "s2"]

    def test_list_keys_invalid_classification_returns_empty(self, tmp_path: "Path") -> None:
        """Test that an invalid classification filter returns empty list."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("item", 1)

        result = memory.list_keys(classification="INVALID_LEVEL")
        assert result == []

    def test_list_keys_no_matches_returns_empty(self, tmp_path: "Path") -> None:
        """Test filtering returns empty when no keys match classification."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("item", 1, classification="PUBLIC")

        result = memory.list_keys(classification="SENSITIVE")
        assert result == []

    def test_list_keys_skips_corrupted_files(self, tmp_path: "Path") -> None:
        """Test that corrupted JSON files are silently skipped."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("valid", {"ok": True})

        # Inject a corrupted file
        bad_file = storage_dir / "corrupted.json"
        bad_file.write_text("!!! not json !!!", encoding="utf-8")

        keys = memory.list_keys()
        assert "valid" in keys
        # corrupted should be skipped, not raise an exception


@pytest.mark.unit
class TestClear:
    """Tests for LongTermMemory.clear()."""

    def test_clear_empty_storage_returns_zero(self, tmp_path: "Path") -> None:
        """Test clearing empty storage returns 0."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        result = memory.clear()
        assert result == 0

    def test_clear_removes_all_entries(self, tmp_path: "Path") -> None:
        """Test that clear removes all stored entries and returns count."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("a", 1)
        memory.store("b", 2)
        memory.store("c", 3)

        count = memory.clear()
        assert count == 3

        # Verify storage is empty
        assert memory.list_keys() == []

    def test_clear_only_removes_json_files(self, tmp_path: "Path") -> None:
        """Test that clear only removes .json files, not other files."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("item", 1)

        # Add a non-JSON file
        (storage_dir / "readme.txt").write_text("keep me", encoding="utf-8")

        memory.clear()

        # Non-JSON file should survive
        assert (storage_dir / "readme.txt").exists()


@pytest.mark.unit
class TestPersistence:
    """Tests for data persistence across LongTermMemory instances."""

    def test_data_survives_new_instance(self, tmp_path: "Path") -> None:
        """Test that data stored by one instance can be retrieved by another."""
        storage_dir = str(tmp_path / "persistent")

        # Store with first instance
        memory1 = LongTermMemory(storage_path=storage_dir)
        memory1.store("persistent_key", {"important": True})

        # Retrieve with a new instance
        memory2 = LongTermMemory(storage_path=storage_dir)
        result = memory2.retrieve("persistent_key")

        assert result == {"important": True}

    def test_list_keys_persists_across_instances(self, tmp_path: "Path") -> None:
        """Test that list_keys works correctly across different instances."""
        storage_dir = str(tmp_path / "persistent")

        memory1 = LongTermMemory(storage_path=storage_dir)
        memory1.store("key_a", 1, classification="PUBLIC")
        memory1.store("key_b", 2, classification="INTERNAL")

        memory2 = LongTermMemory(storage_path=storage_dir)
        all_keys = memory2.list_keys()
        assert sorted(all_keys) == ["key_a", "key_b"]

        public_keys = memory2.list_keys(classification="PUBLIC")
        assert public_keys == ["key_a"]

    def test_delete_persists_across_instances(self, tmp_path: "Path") -> None:
        """Test that a delete in one instance is reflected in another."""
        storage_dir = str(tmp_path / "persistent")

        memory1 = LongTermMemory(storage_path=storage_dir)
        memory1.store("vanishing", {"data": 1})

        memory2 = LongTermMemory(storage_path=storage_dir)
        memory2.delete("vanishing")

        memory3 = LongTermMemory(storage_path=storage_dir)
        assert memory3.retrieve("vanishing") is None


@pytest.mark.unit
class TestPathSecurity:
    """Tests for path traversal and injection prevention."""

    def test_store_rejects_path_traversal_dotdot(self, tmp_path: "Path") -> None:
        """Test that keys containing '..' are rejected."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        result = memory.store("../etc/passwd", {"evil": True})
        assert result is False

    def test_store_rejects_absolute_path_key(self, tmp_path: "Path") -> None:
        """Test that keys starting with '/' are rejected."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        result = memory.store("/etc/passwd", {"evil": True})
        assert result is False

    def test_store_rejects_null_byte_in_key(self, tmp_path: "Path") -> None:
        """Test that keys containing null bytes are rejected."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        result = memory.store("key\x00evil", {"evil": True})
        assert result is False


@pytest.mark.unit
class TestInitialization:
    """Tests for LongTermMemory initialization."""

    def test_creates_storage_directory(self, tmp_path: "Path") -> None:
        """Test that the storage directory is created on init."""
        storage_dir = tmp_path / "new_dir" / "nested"
        assert not storage_dir.exists()

        LongTermMemory(storage_path=str(storage_dir))
        assert storage_dir.exists()
        assert storage_dir.is_dir()

    def test_existing_directory_no_error(self, tmp_path: "Path") -> None:
        """Test that initializing with an existing directory does not raise."""
        storage_dir = tmp_path / "existing"
        storage_dir.mkdir()

        memory = LongTermMemory(storage_path=str(storage_dir))
        assert memory.storage_path == storage_dir


@pytest.mark.unit
class TestUpdateOperation:
    """Tests for update (store with existing key) semantics."""

    def test_update_changes_data(self, tmp_path: "Path") -> None:
        """Test that re-storing under the same key updates the data."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))
        memory.store("evolving", {"version": 1})

        assert memory.retrieve("evolving") == {"version": 1}

        memory.store("evolving", {"version": 2, "extra": "field"})

        assert memory.retrieve("evolving") == {"version": 2, "extra": "field"}

    def test_update_changes_classification(self, tmp_path: "Path") -> None:
        """Test that re-storing can change the classification."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))
        memory.store("item", {"data": 1}, classification="PUBLIC")
        memory.store("item", {"data": 1}, classification="SENSITIVE")

        with (storage_dir / "item.json").open(encoding="utf-8") as f:
            record = json.load(f)

        assert record["classification"] == "SENSITIVE"

    def test_update_refreshes_updated_at(self, tmp_path: "Path") -> None:
        """Test that re-storing updates the updated_at timestamp."""
        storage_dir = tmp_path / "storage"
        memory = LongTermMemory(storage_path=str(storage_dir))

        memory.store("timed", {"v": 1})
        with (storage_dir / "timed.json").open(encoding="utf-8") as f:
            first_record = json.load(f)

        memory.store("timed", {"v": 2})
        with (storage_dir / "timed.json").open(encoding="utf-8") as f:
            second_record = json.load(f)

        # updated_at should change (or at least not be before the original)
        assert second_record["updated_at"] >= first_record["updated_at"]


@pytest.mark.unit
class TestCRUDWorkflow:
    """End-to-end CRUD workflow tests."""

    def test_full_crud_lifecycle(self, tmp_path: "Path") -> None:
        """Test create, read, update, delete lifecycle in sequence."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))

        # Create
        assert memory.store("lifecycle", {"step": "create"}) is True

        # Read
        assert memory.retrieve("lifecycle") == {"step": "create"}

        # Update
        assert memory.store("lifecycle", {"step": "update"}) is True
        assert memory.retrieve("lifecycle") == {"step": "update"}

        # Delete
        assert memory.delete("lifecycle") is True
        assert memory.retrieve("lifecycle") is None

        # Verify key is gone from listing
        assert "lifecycle" not in memory.list_keys()

    def test_store_multiple_then_clear(self, tmp_path: "Path") -> None:
        """Test storing multiple items then clearing all."""
        memory = LongTermMemory(storage_path=str(tmp_path / "storage"))

        for i in range(5):
            memory.store(f"item_{i}", {"index": i})

        assert len(memory.list_keys()) == 5

        cleared = memory.clear()
        assert cleared == 5
        assert memory.list_keys() == []
