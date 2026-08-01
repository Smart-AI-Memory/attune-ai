"""Tests for help/staleness.py — hash comparison and staleness detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.help.manifest import Feature, FeatureManifest
from attune.help.staleness import (
    FeatureStaleness,
    StalenessReport,
    _is_excluded,
    _read_frontmatter_value,
    _read_stored_hash,
    check_staleness,
    compute_source_hash,
)


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project with source files."""
    src = tmp_path / "src" / "auth"
    src.mkdir(parents=True)
    (src / "login.py").write_text("def login(): pass\n", encoding="utf-8")
    (src / "logout.py").write_text("def logout(): pass\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def feature() -> Feature:
    return Feature(
        name="auth",
        description="Authentication",
        files=["src/auth/**"],
        tags=["security"],
    )


class TestComputeSourceHash:
    """Tests for compute_source_hash()."""

    def test_returns_hash_and_files(self, project: Path, feature: Feature) -> None:
        digest, files = compute_source_hash(feature, project)
        assert len(digest) == 64  # SHA-256 hex
        assert len(files) == 2
        assert "src/auth/login.py" in files

    def test_deterministic(self, project: Path, feature: Feature) -> None:
        h1, _ = compute_source_hash(feature, project)
        h2, _ = compute_source_hash(feature, project)
        assert h1 == h2

    def test_changes_when_file_changes(self, project: Path, feature: Feature) -> None:
        h1, _ = compute_source_hash(feature, project)
        (project / "src" / "auth" / "login.py").write_text(
            "def login(user): pass\n", encoding="utf-8"
        )
        h2, _ = compute_source_hash(feature, project)
        assert h1 != h2

    def test_empty_feature_returns_empty_hash(self, project: Path) -> None:
        empty = Feature(name="empty", description="", files=[])
        digest, files = compute_source_hash(empty, project)
        assert len(digest) == 64  # still a valid hash
        assert files == []

    def test_nonexistent_glob_returns_no_files(self, project: Path) -> None:
        feat = Feature(
            name="missing",
            description="",
            files=["nonexistent/**"],
        )
        _, files = compute_source_hash(feat, project)
        assert files == []


class TestStalenessReport:
    """Tests for StalenessReport properties."""

    def test_counts(self) -> None:
        entries = [
            FeatureStaleness("a", is_stale=True, current_hash="x", stored_hash="y"),
            FeatureStaleness("b", is_stale=False, current_hash="x", stored_hash="x"),
            FeatureStaleness("c", is_stale=True, current_hash="z", stored_hash=None),
        ]
        report = StalenessReport(entries=entries)
        assert report.stale_count == 2
        assert report.current_count == 1
        assert report.stale_features == ["a", "c"]


class TestCheckStaleness:
    """Tests for check_staleness()."""

    def test_fresh_after_generation(self, project: Path) -> None:
        """Features are current right after template generation."""
        pytest.importorskip("yaml")
        from attune.help.generator import generate_feature_templates
        from attune.help.manifest import save_manifest

        feat = Feature(
            name="auth",
            description="Authentication",
            files=["src/auth/**"],
            tags=["security"],
        )
        manifest = FeatureManifest(
            version=1,
            features={"auth": feat},
        )
        help_dir = project / ".help"
        save_manifest(manifest, help_dir)
        generate_feature_templates(feat, help_dir, project)

        report = check_staleness(manifest, help_dir, project)
        assert report.stale_count == 0
        assert report.current_count == 1

    def test_stale_after_source_change(self, project: Path) -> None:
        """Feature becomes stale after source changes."""
        pytest.importorskip("yaml")
        from attune.help.generator import generate_feature_templates
        from attune.help.manifest import save_manifest

        feat = Feature(
            name="auth",
            description="Authentication",
            files=["src/auth/**"],
        )
        manifest = FeatureManifest(
            version=1,
            features={"auth": feat},
        )
        help_dir = project / ".help"
        save_manifest(manifest, help_dir)
        generate_feature_templates(feat, help_dir, project)

        # Modify source
        (project / "src" / "auth" / "login.py").write_text(
            "def login(user, password): pass\n",
            encoding="utf-8",
        )

        report = check_staleness(manifest, help_dir, project)
        assert report.stale_count == 1
        assert report.stale_features == ["auth"]

    def test_filter_by_feature_names(self, project: Path) -> None:
        """Can check only specific features."""
        pytest.importorskip("yaml")
        from attune.help.manifest import save_manifest

        manifest = FeatureManifest(
            version=1,
            features={
                "auth": Feature(name="auth", description="", files=["src/auth/**"]),
                "other": Feature(name="other", description="", files=["src/other/**"]),
            },
        )
        help_dir = project / ".help"
        save_manifest(manifest, help_dir)

        report = check_staleness(manifest, help_dir, project, features=["auth"])
        assert len(report.entries) == 1
        assert report.entries[0].feature == "auth"

    def test_manual_feature_excluded_from_staleness(self, project: Path) -> None:
        """A status: manual (single-sourced) feature is never reported.

        It carries no source globs and is authored/projected, so it must
        not appear in the staleness report — even though it has no stored
        template hash to compare against (which would otherwise read as
        stale). See docs/specs/help-docs-single-source/.
        """
        help_dir = project / ".help"
        help_dir.mkdir(parents=True, exist_ok=True)
        manifest = FeatureManifest(
            version=1,
            features={
                "auth": Feature(name="auth", description="", files=["src/auth/**"]),
                "spec-engine": Feature(
                    name="spec-engine",
                    description="Spec-driven development with approval loops",
                    tags=["spec", "planning"],
                    status="manual",
                ),
            },
        )

        report = check_staleness(manifest, help_dir, project)

        names = {e.feature for e in report.entries}
        assert "spec-engine" not in names
        assert "auth" in names


class TestIsExcluded:
    """Tests for _is_excluded() cache directory filtering."""

    def test_excludes_pycache(self) -> None:
        assert _is_excluded(Path("src/auth/__pycache__/login.cpython-310.pyc"))

    def test_excludes_mypy_cache(self) -> None:
        assert _is_excluded(Path("src/auth/.mypy_cache/3.10/login.data.json"))

    def test_excludes_pytest_cache(self) -> None:
        assert _is_excluded(Path(".pytest_cache/v/cache/stepwise"))

    def test_excludes_ruff_cache(self) -> None:
        assert _is_excluded(Path("src/.ruff_cache/0.8.4/content.json"))

    def test_allows_source_files(self) -> None:
        assert not _is_excluded(Path("src/auth/login.py"))

    def test_allows_nested_source(self) -> None:
        assert not _is_excluded(Path("src/attune/help/staleness.py"))

    def test_hash_excludes_cache_dirs(self, tmp_path: Path) -> None:
        """compute_source_hash skips __pycache__ files."""
        src = tmp_path / "src" / "mod"
        src.mkdir(parents=True)
        (src / "real.py").write_text("x = 1\n", encoding="utf-8")
        cache = src / "__pycache__"
        cache.mkdir()
        (cache / "real.cpython-310.pyc").write_bytes(b"\x00\x00")

        feat = Feature(name="mod", description="", files=["src/mod/**"])
        _, files = compute_source_hash(feat, tmp_path)
        assert "src/mod/real.py" in files
        assert not any("__pycache__" in f for f in files)


class TestComputeSourceHashErrors:
    """Tests for error paths in compute_source_hash."""

    def test_unreadable_file_skipped(self, tmp_path: Path) -> None:
        """Unreadable files are skipped; hash is still computed."""
        src = tmp_path / "src" / "mod"
        src.mkdir(parents=True)
        good = src / "ok.py"
        good.write_text("x = 1\n", encoding="utf-8")
        bad = src / "broken.py"
        bad.write_text("y = 2\n", encoding="utf-8")
        bad.chmod(0o000)

        feat = Feature(name="mod", description="", files=["src/mod/**"])
        try:
            digest, files = compute_source_hash(feat, tmp_path)
            # Both files are matched by glob
            assert len(files) == 2
            # Hash is still a valid SHA-256 (from the readable file)
            assert len(digest) == 64
        finally:
            # Restore permissions so tmp_path cleanup works
            bad.chmod(0o644)


class TestReadFrontmatterValue:
    """Tests for _read_frontmatter_value() edge cases."""

    def test_no_frontmatter_delimiter(self) -> None:
        """Text that doesn't start with '---' has no frontmatter."""
        assert _read_frontmatter_value("just plain content\n", "source_hash") is None

    def test_unterminated_frontmatter(self) -> None:
        """An opening '---' with no closing '---' returns None."""
        text = "---\nsource_hash: abc123\nno closing delimiter here\n"
        assert _read_frontmatter_value(text, "source_hash") is None

    def test_key_not_present(self) -> None:
        """Well-formed frontmatter without the requested key returns None."""
        text = "---\nother_key: value\n---\nbody text\n"
        assert _read_frontmatter_value(text, "source_hash") is None

    def test_key_present(self) -> None:
        """Sanity check the happy path still works alongside the edge cases."""
        text = "---\nsource_hash: abc123\n---\nbody text\n"
        assert _read_frontmatter_value(text, "source_hash") == "abc123"


class TestReadStoredHash:
    """Tests for _read_stored_hash() validation and error paths."""

    @pytest.mark.parametrize(
        "bad_name",
        ["", "a/b", "a\\b", "a..b", "a\x00b"],
    )
    def test_rejects_unsafe_feature_names(self, tmp_path: Path, bad_name: str) -> None:
        """Feature names with path-traversal-shaped characters are rejected."""
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        assert _read_stored_hash(bad_name, help_dir) is None

    def test_missing_concept_file_returns_none(self, tmp_path: Path) -> None:
        """No concept.md on disk for the feature returns None."""
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        assert _read_stored_hash("auth", help_dir) is None

    def test_unreadable_concept_file_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An OSError while reading concept.md degrades to None."""
        help_dir = tmp_path / ".help"
        concept_dir = help_dir / "templates" / "auth"
        concept_dir.mkdir(parents=True)
        concept = concept_dir / "concept.md"
        concept.write_text("---\nsource_hash: abc123\n---\nbody\n", encoding="utf-8")

        # chmod(0o000) can't make a file unreadable on Windows; force the
        # OSError branch portably instead.
        def _deny_read(self: Path, *args: object, **kwargs: object) -> str:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "read_text", _deny_read)
        assert _read_stored_hash("auth", help_dir) is None


class TestCheckStalenessUnknownFeature:
    """Tests for check_staleness() with a feature name absent from the manifest."""

    def test_unknown_feature_name_skipped(self, tmp_path: Path) -> None:
        """A requested feature name not in the manifest is logged and skipped."""
        manifest = FeatureManifest(
            version=1,
            features={
                "auth": Feature(name="auth", description="", files=["src/auth/**"]),
            },
        )
        help_dir = tmp_path / ".help"

        report = check_staleness(manifest, help_dir, tmp_path, features=["nonexistent-feature"])

        assert report.entries == []
        assert report.stale_count == 0
