"""Tests for TeamStore persistence.

Tests CRUD operations, path security, and spec validation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from pathlib import Path

import pytest

from attune.orchestration.team_store import (
    TeamSpecification,
    TeamStore,
    _sanitize_team_name,
)


class TestSanitizeTeamName:
    """Tests for _sanitize_team_name helper."""

    def test_simple_name_unchanged(self) -> None:
        assert _sanitize_team_name("release-team") == "release-team"

    def test_special_chars_replaced(self) -> None:
        assert _sanitize_team_name("team/with:special!chars") == "team_with_special_chars"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _sanitize_team_name("")

    def test_null_bytes_raises(self) -> None:
        with pytest.raises(ValueError, match="null bytes"):
            _sanitize_team_name("team\x00evil")

    def test_long_name_truncated(self) -> None:
        long_name = "a" * 300
        assert len(_sanitize_team_name(long_name)) == 200


class TestTeamSpecification:
    """Tests for TeamSpecification dataclass."""

    def test_valid_spec(self) -> None:
        spec = TeamSpecification(
            name="Test Team",
            agents=[{"role": "Auditor"}],
            strategy="parallel",
        )
        assert spec.name == "Test Team"
        assert spec.strategy == "parallel"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            TeamSpecification(name="", agents=[{"role": "A"}])

    def test_empty_agents_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            TeamSpecification(name="Team", agents=[])

    def test_invalid_strategy_raises(self) -> None:
        with pytest.raises(ValueError, match="strategy must be"):
            TeamSpecification(
                name="Team",
                agents=[{"role": "A"}],
                strategy="invalid",
            )

    def test_to_dict_round_trip(self) -> None:
        original = TeamSpecification(
            name="Round Trip Team",
            agents=[{"role": "Auditor", "tier": "CAPABLE"}],
            strategy="sequential",
            quality_gates={"min_score": 80.0},
            description="Test team",
            tags=["test", "demo"],
        )
        data = original.to_dict()
        restored = TeamSpecification.from_dict(data)

        assert restored.name == original.name
        assert restored.agents == original.agents
        assert restored.strategy == original.strategy
        assert restored.quality_gates == original.quality_gates
        assert restored.tags == original.tags


class TestTeamStore:
    """Tests for TeamStore CRUD operations."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test round-trip save and load."""
        store = TeamStore(storage_dir=str(tmp_path))
        spec = TeamSpecification(
            name="my-team",
            agents=[{"role": "Auditor"}],
            strategy="parallel",
        )
        store.save(spec)
        loaded = store.load("my-team")

        assert loaded is not None
        assert loaded.name == "my-team"
        assert loaded.agents == [{"role": "Auditor"}]

    def test_load_nonexistent_returns_none(self, tmp_path: Path) -> None:
        """Test that loading unknown name returns None."""
        store = TeamStore(storage_dir=str(tmp_path))
        assert store.load("nonexistent") is None

    def test_list_all(self, tmp_path: Path) -> None:
        """Test listing all specs."""
        store = TeamStore(storage_dir=str(tmp_path))
        store.save(TeamSpecification(name="team-a", agents=[{"role": "A"}]))
        store.save(TeamSpecification(name="team-b", agents=[{"role": "B"}]))

        all_specs = store.list_all()
        assert len(all_specs) == 2
        names = {s.name for s in all_specs}
        assert names == {"team-a", "team-b"}

    def test_delete(self, tmp_path: Path) -> None:
        """Test deleting a spec."""
        store = TeamStore(storage_dir=str(tmp_path))
        store.save(TeamSpecification(name="delete-me", agents=[{"role": "A"}]))

        assert store.delete("delete-me") is True
        assert store.load("delete-me") is None
        assert store.delete("delete-me") is False  # Already deleted

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        """Test that data persists across store instances."""
        store1 = TeamStore(storage_dir=str(tmp_path))
        store1.save(
            TeamSpecification(
                name="persistent",
                agents=[{"role": "A"}],
                strategy="sequential",
            ),
        )

        store2 = TeamStore(storage_dir=str(tmp_path))
        loaded = store2.load("persistent")
        assert loaded is not None
        assert loaded.strategy == "sequential"


class TestTeamStorePathSecurity:
    """Security tests for TeamStore file operations."""

    def test_blocks_null_bytes(self, tmp_path: Path) -> None:
        """Test that null bytes in name are rejected."""
        store = TeamStore(storage_dir=str(tmp_path))
        with pytest.raises(ValueError, match="null bytes"):
            store.save(
                TeamSpecification(
                    name="team\x00evil",
                    agents=[{"role": "A"}],
                ),
            )

    def test_sanitizes_path_traversal(self, tmp_path: Path) -> None:
        """Test that path traversal in name is sanitized."""
        store = TeamStore(storage_dir=str(tmp_path))
        spec = TeamSpecification(
            name="../../etc/passwd",
            agents=[{"role": "A"}],
        )
        path = store.save(spec)
        # File should be within the storage directory
        assert path.parent == tmp_path

    def test_all_files_stay_within_storage_dir(self, tmp_path: Path) -> None:
        """Test no files escape the storage directory."""
        store = TeamStore(storage_dir=str(tmp_path))
        store.save(TeamSpecification(name="safe-1", agents=[{"role": "A"}]))
        store.save(TeamSpecification(name="safe-2", agents=[{"role": "B"}]))

        for f in tmp_path.glob("*.json"):
            assert f.parent == tmp_path

    def test_corrupted_file_handled(self, tmp_path: Path) -> None:
        """Test that corrupt files don't crash list_all."""
        (tmp_path / "corrupt.json").write_text("{broken json")
        store = TeamStore(storage_dir=str(tmp_path))
        specs = store.list_all()
        assert all(s.name != "corrupt" for s in specs)
