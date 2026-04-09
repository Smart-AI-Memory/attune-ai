"""Tests for help/manifest.py — features.yaml parsing and query."""

from __future__ import annotations

import pytest

pytest.importorskip("yaml")

from pathlib import Path  # noqa: E402

from attune.help.manifest import (  # noqa: E402
    Feature,
    FeatureManifest,
    load_manifest,
    match_files_to_features,
    resolve_topic,
    save_manifest,
)

_SAMPLE_YAML = """\
version: 1

features:
  authentication:
    description: User auth and session management
    files:
      - src/auth/**
      - src/middleware/session.py
    tags: [security, users]

  payments:
    description: Stripe integration and billing
    files:
      - src/billing/**
    tags: [billing, stripe]

  api:
    description: REST API endpoints
    files:
      - src/api/**
    tags: [api, rest]
"""


@pytest.fixture()
def help_dir(tmp_path: Path) -> Path:
    """Create a .help/ dir with sample features.yaml."""
    d = tmp_path / ".help"
    d.mkdir()
    (d / "features.yaml").write_text(_SAMPLE_YAML, encoding="utf-8")
    return d


class TestLoadManifest:
    """Tests for load_manifest()."""

    def test_loads_valid_manifest(self, help_dir: Path) -> None:
        manifest = load_manifest(help_dir)
        assert manifest.version == 1
        assert len(manifest.features) == 3
        assert "authentication" in manifest.features
        assert manifest.path == help_dir / "features.yaml"

    def test_parses_feature_fields(self, help_dir: Path) -> None:
        manifest = load_manifest(help_dir)
        auth = manifest.features["authentication"]
        assert auth.name == "authentication"
        assert auth.description == "User auth and session management"
        assert "src/auth/**" in auth.files
        assert "security" in auth.tags

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(FileNotFoundError):
            load_manifest(empty)

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        d = tmp_path / ".help"
        d.mkdir()
        (d / "features.yaml").write_text("not_a_mapping", encoding="utf-8")
        with pytest.raises(ValueError, match="expected mapping"):
            load_manifest(d)

    def test_invalid_features_key_raises(self, tmp_path: Path) -> None:
        d = tmp_path / ".help"
        d.mkdir()
        (d / "features.yaml").write_text(
            "version: 1\nfeatures: not_a_dict\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="must be a mapping"):
            load_manifest(d)

    def test_invalid_feature_entry_raises(self, tmp_path: Path) -> None:
        d = tmp_path / ".help"
        d.mkdir()
        (d / "features.yaml").write_text(
            "version: 1\nfeatures:\n  bad: just_a_string\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="'bad' must be a mapping"):
            load_manifest(d)


class TestSaveManifest:
    """Tests for save_manifest()."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Save then load produces the same features."""
        d = tmp_path / ".help"
        manifest = FeatureManifest(
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
        save_manifest(manifest, d)
        loaded = load_manifest(d)
        assert "auth" in loaded.features
        assert loaded.features["auth"].description == "Authentication"
        assert loaded.features["auth"].files == ["src/auth/**"]

    def test_creates_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "new" / ".help"
        manifest = FeatureManifest(version=1, features={})
        path = save_manifest(manifest, d)
        assert path.exists()


class TestMatchFilesToFeatures:
    """Tests for match_files_to_features()."""

    def test_matches_glob_patterns(self, help_dir: Path) -> None:
        manifest = load_manifest(help_dir)
        changed = [
            "src/auth/login.py",
            "src/billing/charge.py",
            "src/utils/helpers.py",
        ]
        matches = match_files_to_features(changed, manifest)
        assert "authentication" in matches
        assert "src/auth/login.py" in matches["authentication"]
        assert "payments" in matches
        assert "src/billing/charge.py" in matches["payments"]
        assert "api" not in matches  # no api files changed

    def test_no_matches_returns_empty(self, help_dir: Path) -> None:
        manifest = load_manifest(help_dir)
        matches = match_files_to_features(["README.md"], manifest)
        assert matches == {}

    def test_file_matches_multiple_features(self, tmp_path: Path) -> None:
        """A file can match multiple features."""
        d = tmp_path / ".help"
        d.mkdir()
        (d / "features.yaml").write_text(
            "version: 1\nfeatures:\n"
            "  a:\n    description: A\n    files: ['src/*']\n"
            "  b:\n    description: B\n    files: ['src/*']\n",
            encoding="utf-8",
        )
        manifest = load_manifest(d)
        matches = match_files_to_features(["src/foo.py"], manifest)
        assert "a" in matches
        assert "b" in matches

    def test_star_does_not_cross_directory(self) -> None:
        """Single * must not match across / boundaries."""
        manifest = FeatureManifest(
            version=1,
            features={
                "a": Feature(
                    name="a",
                    description="A",
                    files=["src/attune/*"],
                ),
            },
        )
        result = match_files_to_features(
            ["src/attune/foo.py", "src/attune-redis/foo.py"],
            manifest,
        )
        assert "a" in result
        assert result["a"] == ["src/attune/foo.py"]

    def test_doublestar_crosses_directories(self) -> None:
        """** matches across path separators."""
        manifest = FeatureManifest(
            version=1,
            features={
                "auth": Feature(
                    name="auth",
                    description="Auth",
                    files=["src/auth/**"],
                ),
            },
        )
        result = match_files_to_features(
            [
                "src/auth/login.py",
                "src/auth/providers/google.py",
            ],
            manifest,
        )
        assert "auth" in result
        assert len(result["auth"]) == 2

    def test_exact_path_matches(self) -> None:
        """Literal path without globs matches itself."""
        manifest = FeatureManifest(
            version=1,
            features={
                "m": Feature(
                    name="m",
                    description="M",
                    files=["src/middleware/session.py"],
                ),
            },
        )
        result = match_files_to_features(
            ["src/middleware/session.py"],
            manifest,
        )
        assert "m" in result


class TestResolveTopic:
    """Tests for resolve_topic()."""

    def test_exact_match(self, help_dir: Path) -> None:
        manifest = load_manifest(help_dir)
        assert resolve_topic("authentication", manifest) == "authentication"

    def test_substring_match(self, help_dir: Path) -> None:
        manifest = load_manifest(help_dir)
        assert resolve_topic("auth", manifest) == "authentication"

    def test_description_match(self, help_dir: Path) -> None:
        manifest = load_manifest(help_dir)
        assert resolve_topic("stripe", manifest) == "payments"

    def test_tag_match(self, help_dir: Path) -> None:
        manifest = load_manifest(help_dir)
        assert resolve_topic("rest", manifest) == "api"

    def test_no_match_returns_none(self, help_dir: Path) -> None:
        manifest = load_manifest(help_dir)
        assert resolve_topic("nonexistent", manifest) is None

    def test_ambiguous_returns_none(self, tmp_path: Path) -> None:
        """Multiple substring matches → None (ambiguous)."""
        d = tmp_path / ".help"
        d.mkdir()
        (d / "features.yaml").write_text(
            "version: 1\nfeatures:\n"
            "  auth-basic:\n    description: basic auth flow\n"
            "  auth-oauth:\n    description: auth via oauth\n",
            encoding="utf-8",
        )
        manifest = load_manifest(d)
        assert resolve_topic("auth", manifest) is None


class TestVersionMismatch:
    """Tests for manifest version handling."""

    def test_version_mismatch_loads_with_warning(self, tmp_path: Path) -> None:
        """A future manifest version still loads (with warning)."""
        d = tmp_path / ".help"
        d.mkdir()
        (d / "features.yaml").write_text(
            "version: 99\nfeatures:\n" "  x:\n    description: test\n",
            encoding="utf-8",
        )
        manifest = load_manifest(d)
        assert manifest.version == 99
        assert "x" in manifest.features
