"""Tests for attune_author.staleness."""

from __future__ import annotations

from pathlib import Path

from attune_author.manifest import Feature, load_manifest
from attune_author.staleness import (
    FeatureStaleness,
    StalenessReport,
    _read_frontmatter_value,
    check_staleness,
    compute_source_hash,
)


class TestReadFrontmatterValue:
    """Tests for _read_frontmatter_value()."""

    def test_reads_value(self) -> None:
        """Test extracting a value from frontmatter."""
        text = "---\nfoo: bar\nbaz: 123\n---\ncontent"
        assert _read_frontmatter_value(text, "foo") == "bar"
        assert _read_frontmatter_value(text, "baz") == "123"

    def test_returns_none_for_missing_key(self) -> None:
        """Test None for missing key."""
        text = "---\nfoo: bar\n---\ncontent"
        assert _read_frontmatter_value(text, "missing") is None

    def test_returns_none_without_frontmatter(self) -> None:
        """Test None for content without frontmatter."""
        assert _read_frontmatter_value("no frontmatter", "foo") is None

    def test_returns_none_for_unclosed_frontmatter(self) -> None:
        """Test None for unclosed frontmatter block."""
        assert _read_frontmatter_value("---\nfoo: bar\n", "foo") is None


class TestComputeSourceHash:
    """Tests for compute_source_hash()."""

    def test_hashes_matched_files(self, project_root: Path) -> None:
        """Test that hash is computed from matched files."""
        feature = Feature(
            name="auth",
            description="Auth",
            files=["src/auth/**"],
        )

        digest, matched = compute_source_hash(feature, project_root)

        assert len(digest) == 64  # SHA-256 hex
        assert len(matched) > 0
        assert any("login.py" in f for f in matched)

    def test_consistent_hash(self, project_root: Path) -> None:
        """Test that same files produce same hash."""
        feature = Feature(name="auth", description="", files=["src/auth/**"])

        hash1, _ = compute_source_hash(feature, project_root)
        hash2, _ = compute_source_hash(feature, project_root)

        assert hash1 == hash2

    def test_empty_for_no_matches(self, project_root: Path) -> None:
        """Test empty matched list for non-matching patterns."""
        feature = Feature(name="nope", description="", files=["nonexistent/**"])

        digest, matched = compute_source_hash(feature, project_root)

        assert matched == []
        assert len(digest) == 64  # Empty hash is still valid


class TestStalenessReport:
    """Tests for StalenessReport properties."""

    def test_stale_count(self) -> None:
        """Test stale_count property."""
        report = StalenessReport(
            entries=[
                FeatureStaleness("a", is_stale=True, current_hash="x", stored_hash="y"),
                FeatureStaleness("b", is_stale=False, current_hash="z", stored_hash="z"),
                FeatureStaleness("c", is_stale=True, current_hash="w", stored_hash=None),
            ]
        )

        assert report.stale_count == 2
        assert report.current_count == 1
        assert report.stale_features == ["a", "c"]


class TestCheckStaleness:
    """Tests for check_staleness()."""

    def test_all_stale_without_templates(self, help_dir: Path, project_root: Path) -> None:
        """Test that features without templates are stale."""
        manifest = load_manifest(help_dir)
        report = check_staleness(manifest, help_dir, project_root)

        # No templates exist yet, so stored hash is None -> stale
        assert report.stale_count == 2

    def test_filter_by_feature_name(self, help_dir: Path, project_root: Path) -> None:
        """Test filtering staleness check by feature name."""
        manifest = load_manifest(help_dir)
        report = check_staleness(manifest, help_dir, project_root, features=["auth"])

        assert len(report.entries) == 1
        assert report.entries[0].feature == "auth"
