"""Tests for attune_author.manifest."""

from __future__ import annotations

from pathlib import Path

import pytest

from attune_author.manifest import (
    Feature,
    FeatureManifest,
    load_manifest,
    match_files_to_features,
    resolve_topic,
    save_manifest,
)


class TestLoadManifest:
    """Tests for load_manifest()."""

    def test_loads_valid_manifest(self, help_dir: Path) -> None:
        """Test loading a valid features.yaml."""
        manifest = load_manifest(help_dir)

        assert manifest.version == 1
        assert len(manifest.features) == 2
        assert "auth" in manifest.features
        assert "cli" in manifest.features

    def test_parses_feature_fields(self, help_dir: Path) -> None:
        """Test that feature fields are parsed correctly."""
        manifest = load_manifest(help_dir)
        auth = manifest.features["auth"]

        assert auth.name == "auth"
        assert auth.description == "Authentication and authorization"
        assert auth.files == ["src/auth/**"]
        assert auth.tags == ["security", "users"]

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        """Test FileNotFoundError for missing manifest."""
        with pytest.raises(FileNotFoundError, match="No features.yaml"):
            load_manifest(tmp_path / "nonexistent")

    def test_raises_on_invalid_yaml(self, tmp_path: Path) -> None:
        """Test ValueError for malformed manifest."""
        help = tmp_path / ".help"
        help.mkdir()
        (help / "features.yaml").write_text("- just a list\n")

        with pytest.raises(ValueError, match="expected mapping"):
            load_manifest(help)

    def test_raises_on_invalid_features_section(self, tmp_path: Path) -> None:
        """Test ValueError when features is not a mapping."""
        help = tmp_path / ".help"
        help.mkdir()
        (help / "features.yaml").write_text("version: 1\nfeatures:\n  - not a mapping\n")

        with pytest.raises(ValueError, match="must be a mapping"):
            load_manifest(help)


class TestSaveManifest:
    """Tests for save_manifest()."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Test that save -> load produces the same data."""
        original = FeatureManifest(
            version=1,
            features={
                "auth": Feature(
                    name="auth",
                    description="Authentication",
                    files=["src/auth/**"],
                    tags=["security"],
                ),
            },
        )

        help_dir = tmp_path / ".help"
        save_manifest(original, help_dir)

        loaded = load_manifest(help_dir)
        assert loaded.version == 1
        assert "auth" in loaded.features
        assert loaded.features["auth"].description == "Authentication"

    def test_creates_directory(self, tmp_path: Path) -> None:
        """Test that save_manifest creates the help directory."""
        manifest = FeatureManifest(version=1, features={})
        help_dir = tmp_path / "new" / ".help"

        save_manifest(manifest, help_dir)
        assert (help_dir / "features.yaml").exists()


class TestMatchFilesToFeatures:
    """Tests for match_files_to_features()."""

    def test_matches_glob_patterns(self, help_dir: Path) -> None:
        """Test that changed files match feature globs."""
        manifest = load_manifest(help_dir)
        changed = ["src/auth/login.py", "src/cli.py", "README.md"]

        matches = match_files_to_features(changed, manifest)

        assert "auth" in matches
        assert "src/auth/login.py" in matches["auth"]
        assert "cli" in matches
        assert "src/cli.py" in matches["cli"]

    def test_no_match_returns_empty(self, help_dir: Path) -> None:
        """Test that unmatched files produce empty dict."""
        manifest = load_manifest(help_dir)
        matches = match_files_to_features(["unrelated.txt"], manifest)

        assert matches == {}


class TestResolveTopic:
    """Tests for resolve_topic()."""

    def test_exact_match(self, help_dir: Path) -> None:
        """Test exact feature name match."""
        manifest = load_manifest(help_dir)
        assert resolve_topic("auth", manifest) == "auth"

    def test_substring_match(self, help_dir: Path) -> None:
        """Test substring match on feature name."""
        manifest = load_manifest(help_dir)
        assert resolve_topic("cl", manifest) == "cli"

    def test_tag_match(self, help_dir: Path) -> None:
        """Test match by tag."""
        manifest = load_manifest(help_dir)
        assert resolve_topic("security", manifest) == "auth"

    def test_no_match_returns_none(self, help_dir: Path) -> None:
        """Test None for unresolvable query."""
        manifest = load_manifest(help_dir)
        assert resolve_topic("nonexistent", manifest) is None
