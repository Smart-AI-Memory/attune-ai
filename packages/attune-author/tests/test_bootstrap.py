"""Tests for attune_author.bootstrap."""

from __future__ import annotations

from pathlib import Path

from attune_author.bootstrap import (
    ProposedFeature,
    _find_source_root,
    _infer_description,
    _infer_tags,
    proposals_to_manifest,
    scan_project,
)


class TestScanProject:
    """Tests for scan_project()."""

    def test_discovers_source_directories(self, tmp_path: Path) -> None:
        """Test that source directories are proposed as features."""
        # Create a src/pkg/ structure
        src = tmp_path / "src" / "myapp"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('"""My app."""\n')

        auth = src / "auth"
        auth.mkdir()
        (auth / "__init__.py").write_text('"""Auth module."""\n')
        (auth / "login.py").write_text("def login(): pass\n")
        (auth / "session.py").write_text("def session(): pass\n")

        proposals = scan_project(tmp_path)

        names = [p.name for p in proposals]
        assert "auth" in names

    def test_skips_hidden_and_cache_dirs(self, tmp_path: Path) -> None:
        """Test that hidden/cache directories are skipped."""
        src = tmp_path / "src" / "pkg"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("")

        for skip_name in ["__pycache__", ".git", "node_modules"]:
            d = src / skip_name
            d.mkdir()
            (d / "file.py").write_text("")

        proposals = scan_project(tmp_path)
        names = [p.name for p in proposals]

        assert "__pycache__" not in names
        assert ".git" not in names
        assert "node-modules" not in names

    def test_empty_project(self, tmp_path: Path) -> None:
        """Test scanning an empty project."""
        proposals = scan_project(tmp_path)
        assert isinstance(proposals, list)

    def test_discovers_config_directory(self, tmp_path: Path) -> None:
        """Test that config directories are discovered."""
        cfg = tmp_path / "config"
        cfg.mkdir()
        (cfg / "settings.yaml").write_text("key: value\n")

        proposals = scan_project(tmp_path)
        names = [p.name for p in proposals]

        assert "configuration" in names

    def test_discovers_entry_point_directly(self, tmp_path: Path) -> None:
        """Test entry point discovery via private function."""
        from attune_author.bootstrap import _discover_from_entry_points

        sub = tmp_path / "scripts"
        sub.mkdir()
        (sub / "main.py").write_text("def main(): pass\n")

        seen: set[str] = set()
        proposals = _discover_from_entry_points(tmp_path, seen)

        assert len(proposals) > 0
        assert any("entry-point" in p.tags for p in proposals)

    def test_proposals_sorted_by_confidence(self, tmp_path: Path) -> None:
        """Test that high-confidence proposals come first."""
        # Single src directory with one feature having many files (high)
        src = tmp_path / "src" / "pkg"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("")

        big = src / "big"
        big.mkdir()
        for i in range(5):
            (big / f"file{i}.py").write_text("")

        small = src / "small"
        small.mkdir()
        (small / "one.py").write_text("")

        proposals = scan_project(tmp_path)

        confidences = [p.confidence for p in proposals]
        # High should come before medium
        if "high" in confidences and "medium" in confidences:
            assert confidences.index("high") < confidences.index("medium")


class TestFindSourceRoot:
    """Tests for _find_source_root()."""

    def test_src_with_single_package(self, tmp_path: Path) -> None:
        """Test src/<single-pkg>/ pattern."""
        pkg = tmp_path / "src" / "myapp"
        pkg.mkdir(parents=True)

        result = _find_source_root(tmp_path)
        assert result == pkg

    def test_src_with_multiple_packages(self, tmp_path: Path) -> None:
        """Test src/ with multiple subdirectories."""
        (tmp_path / "src" / "a").mkdir(parents=True)
        (tmp_path / "src" / "b").mkdir(parents=True)

        result = _find_source_root(tmp_path)
        assert result == tmp_path / "src"

    def test_lib_pattern(self, tmp_path: Path) -> None:
        """Test lib/ pattern."""
        (tmp_path / "lib").mkdir()
        result = _find_source_root(tmp_path)
        assert result == tmp_path / "lib"

    def test_app_pattern(self, tmp_path: Path) -> None:
        """Test app/ pattern."""
        (tmp_path / "app").mkdir()
        result = _find_source_root(tmp_path)
        assert result == tmp_path / "app"

    def test_fallback_to_root(self, tmp_path: Path) -> None:
        """Test fallback to project root when no src/lib/app."""
        result = _find_source_root(tmp_path)
        assert result == tmp_path


class TestInferDescription:
    """Tests for _infer_description()."""

    def test_from_init_docstring(self, tmp_path: Path) -> None:
        """Test extracting from __init__.py docstring."""
        d = tmp_path / "mod"
        d.mkdir()
        (d / "__init__.py").write_text('"""Module purpose line."""\n')

        result = _infer_description(d)
        assert result == "Module purpose line."

    def test_from_init_single_quotes(self, tmp_path: Path) -> None:
        """Test extracting from triple-single-quote docstring."""
        d = tmp_path / "mod"
        d.mkdir()
        (d / "__init__.py").write_text("'''Single quote docstring.'''\n")

        result = _infer_description(d)
        assert result == "Single quote docstring."

    def test_from_readme(self, tmp_path: Path) -> None:
        """Test extracting from README.md."""
        d = tmp_path / "mod"
        d.mkdir()
        (d / "README.md").write_text("# My Module\n\nDetails.\n")

        result = _infer_description(d)
        assert result == "My Module"

    def test_fallback_to_directory_name(self, tmp_path: Path) -> None:
        """Test fallback when no docstring or README."""
        d = tmp_path / "my_module-name"
        d.mkdir()

        result = _infer_description(d)
        assert result == "My Module Name"

    def test_handles_unreadable_init(self, tmp_path: Path) -> None:
        """Test that unreadable init.py falls through gracefully."""
        d = tmp_path / "mod"
        d.mkdir()
        # Empty __init__.py with no docstring
        (d / "__init__.py").write_text("x = 1\n")

        result = _infer_description(d)
        # Should fall back to directory name
        assert "Mod" in result


class TestInferTags:
    """Tests for _infer_tags()."""

    def test_auth_tags(self) -> None:
        """Test auth-related name produces security/users tags."""
        tags = _infer_tags("auth")
        assert "security" in tags
        assert "users" in tags

    def test_api_tags(self) -> None:
        """Test API-related name."""
        assert "api" in _infer_tags("api")
        assert "rest" in _infer_tags("api")

    def test_cli_tags(self) -> None:
        """Test CLI-related name."""
        assert "cli" in _infer_tags("cli")

    def test_no_match_returns_empty(self) -> None:
        """Test unrecognized name returns empty list."""
        assert _infer_tags("xyzfoobar") == []

    def test_dedupes_tags(self) -> None:
        """Test that duplicate tags are removed."""
        # 'auth' and 'security' both add 'security'
        tags = _infer_tags("authsecurity")
        assert tags.count("security") == 1


class TestProposalsToManifest:
    """Tests for proposals_to_manifest()."""

    def test_converts_proposals(self) -> None:
        """Test converting proposals to a manifest."""
        proposals = [
            ProposedFeature(
                name="auth",
                description="Authentication",
                files=["src/auth/**"],
                tags=["security"],
            ),
        ]

        manifest = proposals_to_manifest(proposals)

        assert manifest.version == 1
        assert "auth" in manifest.features
        assert manifest.features["auth"].description == "Authentication"

    def test_empty_proposals(self) -> None:
        """Test empty proposal list yields empty manifest."""
        manifest = proposals_to_manifest([])
        assert manifest.features == {}

    def test_multiple_proposals(self) -> None:
        """Test converting multiple proposals."""
        proposals = [
            ProposedFeature(name="a", description="A"),
            ProposedFeature(name="b", description="B"),
            ProposedFeature(name="c", description="C"),
        ]
        manifest = proposals_to_manifest(proposals)
        assert len(manifest.features) == 3
