"""Tests for help/bootstrap.py — project scanning and manifest proposal."""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.help.bootstrap import (
    ProposedFeature,
    proposals_to_manifest,
    scan_project,
)


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project with multiple feature dirs."""
    # Source directories
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "auth" / "__init__.py").write_text(
        '"""User authentication."""\n', encoding="utf-8"
    )
    (tmp_path / "src" / "auth" / "login.py").write_text("def login(): pass\n", encoding="utf-8")
    (tmp_path / "src" / "auth" / "logout.py").write_text("def logout(): pass\n", encoding="utf-8")

    (tmp_path / "src" / "billing").mkdir(parents=True)
    (tmp_path / "src" / "billing" / "__init__.py").write_text(
        '"""Stripe billing integration."""\n', encoding="utf-8"
    )
    (tmp_path / "src" / "billing" / "charge.py").write_text(
        "def charge(): pass\n", encoding="utf-8"
    )

    # Config directory
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text("debug: false\n", encoding="utf-8")

    # An empty dir (should be skipped)
    (tmp_path / "src" / "empty").mkdir()

    return tmp_path


class TestScanProject:
    """Tests for scan_project()."""

    def test_discovers_source_directories(self, project: Path) -> None:
        proposals = scan_project(project)
        names = [p.name for p in proposals]
        assert "auth" in names
        assert "billing" in names

    def test_skips_empty_directories(self, project: Path) -> None:
        proposals = scan_project(project)
        names = [p.name for p in proposals]
        assert "empty" not in names

    def test_skips_hidden_directories(self, project: Path) -> None:
        (project / "src" / ".hidden").mkdir()
        (project / "src" / ".hidden" / "f.py").write_text("x=1\n")
        proposals = scan_project(project)
        names = [p.name for p in proposals]
        assert ".hidden" not in names

    def test_skips_underscore_directories(self, project: Path) -> None:
        proposals = scan_project(project)
        names = [p.name for p in proposals]
        assert "__pycache__" not in names

    def test_infers_description_from_init_docstring(self, project: Path) -> None:
        proposals = scan_project(project)
        auth = next(p for p in proposals if p.name == "auth")
        assert "authentication" in auth.description.lower()

    def test_assigns_glob_patterns(self, project: Path) -> None:
        proposals = scan_project(project)
        auth = next(p for p in proposals if p.name == "auth")
        assert any("auth" in f for f in auth.files)

    def test_sorted_by_confidence(self, project: Path) -> None:
        proposals = scan_project(project)
        confidences = [p.confidence for p in proposals]
        # high comes before medium comes before low
        order = {"high": 0, "medium": 1, "low": 2}
        values = [order[c] for c in confidences]
        assert values == sorted(values)

    def test_discovers_config_directory(self, project: Path) -> None:
        proposals = scan_project(project)
        names = [p.name for p in proposals]
        assert "configuration" in names

    def test_infers_tags_from_name(self, project: Path) -> None:
        proposals = scan_project(project)
        auth = next(p for p in proposals if p.name == "auth")
        assert "security" in auth.tags


class TestProposalsToManifest:
    """Tests for proposals_to_manifest()."""

    def test_converts_proposals_to_manifest(self) -> None:
        proposals = [
            ProposedFeature(
                name="auth",
                description="Authentication",
                files=["src/auth/**"],
                tags=["security"],
            ),
            ProposedFeature(
                name="api",
                description="REST API",
                files=["src/api/**"],
                tags=["api"],
            ),
        ]
        manifest = proposals_to_manifest(proposals)
        assert manifest.version == 1
        assert len(manifest.features) == 2
        assert manifest.features["auth"].description == "Authentication"
        assert manifest.features["api"].files == ["src/api/**"]

    def test_empty_proposals(self) -> None:
        manifest = proposals_to_manifest([])
        assert manifest.version == 1
        assert len(manifest.features) == 0


# ===========================================================================
# Coverage gap tests
# ===========================================================================


class TestFindSourceRoot:
    """Cover lines 164, 169-178: source root pattern variants."""

    def test_single_src_child_returned(self, tmp_path: Path) -> None:
        """Line 164: src/<single-pkg>/ → return that single package."""
        from attune.help.bootstrap import _find_source_root

        (tmp_path / "src" / "mypkg").mkdir(parents=True)
        result = _find_source_root(tmp_path)
        assert result == (tmp_path / "src" / "mypkg")

    def test_lib_pattern(self, tmp_path: Path) -> None:
        """Lines 169-171: lib/ → return lib/."""
        from attune.help.bootstrap import _find_source_root

        (tmp_path / "lib").mkdir()
        result = _find_source_root(tmp_path)
        assert result == tmp_path / "lib"

    def test_app_pattern(self, tmp_path: Path) -> None:
        """Lines 173-176: app/ → return app/."""
        from attune.help.bootstrap import _find_source_root

        (tmp_path / "app").mkdir()
        result = _find_source_root(tmp_path)
        assert result == tmp_path / "app"

    def test_fallback_to_project_root(self, tmp_path: Path) -> None:
        """Line 178: no src/lib/app → project root itself."""
        from attune.help.bootstrap import _find_source_root

        result = _find_source_root(tmp_path)
        assert result == tmp_path

    def test_src_with_only_skip_dirs_falls_back(self, tmp_path: Path) -> None:
        """src/ with only __pycache__ → falls back."""
        from attune.help.bootstrap import _find_source_root

        (tmp_path / "src" / "__pycache__").mkdir(parents=True)
        # Single child but skipped — children list is empty after filter
        result = _find_source_root(tmp_path)
        # Falls through to lib/app/root
        assert result == tmp_path


class TestDiscoverFromDirectoriesEdgeCases:
    """Cover lines 202, 206, 210, 214 in _discover_from_directories."""

    def test_src_root_not_a_dir(self, tmp_path: Path) -> None:
        """Line 202: src_root is not a directory → empty list."""
        from attune.help.bootstrap import _discover_from_directories

        # Create a file at the path expected to be src_root
        fake_root = tmp_path / "not_a_dir"
        fake_root.write_text("hi")
        result = _discover_from_directories(fake_root, tmp_path, set())
        assert result == []

    def test_skips_files_in_src_root(self, tmp_path: Path) -> None:
        """Line 206: file (not dir) inside src_root → continue."""
        from attune.help.bootstrap import _discover_from_directories

        src = tmp_path / "src"
        src.mkdir()
        (src / "loose_file.py").write_text("pass\n")
        result = _discover_from_directories(src, tmp_path, set())
        # Files are skipped — no proposals
        assert result == []

    def test_skips_dirs_in_skip_list(self, tmp_path: Path) -> None:
        """Line 210: child name in _SKIP_DIRS → continue."""
        from attune.help.bootstrap import _discover_from_directories

        src = tmp_path / "src"
        src.mkdir()
        (src / "node_modules").mkdir()
        (src / "node_modules" / "junk.js").write_text("")
        result = _discover_from_directories(src, tmp_path, set())
        assert result == []

    def test_skips_already_seen_names(self, tmp_path: Path) -> None:
        """Line 214: name already in seen → continue."""
        from attune.help.bootstrap import _discover_from_directories

        src = tmp_path / "src"
        src.mkdir()
        (src / "auth").mkdir()
        (src / "auth" / "x.py").write_text("pass")
        seen = {"auth"}
        result = _discover_from_directories(src, tmp_path, seen)
        assert result == []


class TestDiscoverFromEntryPoints:
    """Cover lines 263-275 in _discover_from_entry_points."""

    def test_finds_main_at_project_root(self, tmp_path: Path) -> None:
        """parent_name == project_root.name → name 'main'."""
        from attune.help.bootstrap import _discover_from_entry_points

        (tmp_path / "main.py").write_text("def main(): pass\n")
        proposals = _discover_from_entry_points(tmp_path, set())
        # parent.name will equal tmp_path.name → name = "main"
        assert any(p.name == "main" for p in proposals)

    def test_finds_entry_in_subdir(self, tmp_path: Path) -> None:
        """Entry in subdir → name '<subdir>-entry'."""
        from attune.help.bootstrap import _discover_from_entry_points

        (tmp_path / "cli_app").mkdir()
        (tmp_path / "cli_app" / "cli.py").write_text("pass")
        proposals = _discover_from_entry_points(tmp_path, set())
        names = [p.name for p in proposals]
        assert "cli_app-entry" in names
        # Confidence is 'low'
        assert all(p.confidence == "low" for p in proposals if p.name == "cli_app-entry")

    def test_skips_entry_in_skip_dir(self, tmp_path: Path) -> None:
        """parent_name in _SKIP_DIRS → continue."""
        from attune.help.bootstrap import _discover_from_entry_points

        # Create a real dir and put cli.py inside, but the entry-point loop
        # should not visit it because os.walk filters via dirnames mutation.
        # Instead, use a parent named in _SKIP_DIRS via a path the walker still visits.
        # Easiest: simulate entry inside .git.
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "main.py").write_text("pass")
        proposals = _discover_from_entry_points(tmp_path, set())
        # .git is in _SKIP_DIRS → walker prunes it
        assert all(".git" not in p.name for p in proposals)

    def test_seen_set_skips_entries(self, tmp_path: Path) -> None:
        """Line 271-272: name already in seen → skip."""
        from attune.help.bootstrap import _discover_from_entry_points

        (tmp_path / "main.py").write_text("pass")
        # Pre-populate seen with the would-be name
        seen = {"main"}
        proposals = _discover_from_entry_points(tmp_path, seen)
        assert all(p.name != "main" for p in proposals)

    def test_parent_in_seen_skips(self, tmp_path: Path) -> None:
        """Line 267-268: parent_name already in seen → skip."""
        from attune.help.bootstrap import _discover_from_entry_points

        (tmp_path / "auth").mkdir()
        (tmp_path / "auth" / "cli.py").write_text("pass")
        seen = {"auth"}
        proposals = _discover_from_entry_points(tmp_path, seen)
        # parent_name 'auth' in seen → skip
        assert all(p.name != "auth-entry" for p in proposals)


class TestDiscoverFromConfigEdgeCases:
    """Cover lines 306, 312 in _discover_from_config."""

    def test_skips_files_in_root(self, tmp_path: Path) -> None:
        """Line 306: file (not dir) at root → continue."""
        from attune.help.bootstrap import _discover_from_config

        # A file named 'config' (without extension) — shouldn't be considered
        (tmp_path / "config").write_text("not a dir\n")
        # Build a sibling regular dir
        (tmp_path / "settings").mkdir()
        proposals = _discover_from_config(tmp_path, set())
        # Only 'settings' dir was a config match; 'config' file was skipped
        assert len(proposals) == 1

    def test_seen_skips_duplicate_configuration(self, tmp_path: Path) -> None:
        """Line 312: 'configuration' already in seen → skip."""
        from attune.help.bootstrap import _discover_from_config

        (tmp_path / "config").mkdir()
        (tmp_path / "settings").mkdir()
        # Pre-populate seen
        seen = {"configuration"}
        proposals = _discover_from_config(tmp_path, seen)
        assert proposals == []


class TestInferDescription:
    """Cover lines 348->347, 353->347, 355-369 in _infer_description."""

    def test_init_no_docstring_falls_back_to_readme(self, tmp_path: Path) -> None:
        """Lines 358-364: README.md fallback."""
        from attune.help.bootstrap import _infer_description

        d = tmp_path / "feature"
        d.mkdir()
        # __init__.py with no docstring — has neither delim
        (d / "__init__.py").write_text("import os\n")
        (d / "README.md").write_text("# My Feature Title\nMore details.\n")
        result = _infer_description(d)
        assert result == "My Feature Title"

    def test_init_docstring_with_empty_first_line_skipped(self, tmp_path: Path) -> None:
        """Line 353->347: empty first_line → continue to next delim or fallback."""
        from attune.help.bootstrap import _infer_description

        d = tmp_path / "feature"
        d.mkdir()
        # Docstring is empty (just whitespace between """ """)
        (d / "__init__.py").write_text('"""   """\n')
        # No README → falls back to humanized dir name
        result = _infer_description(d)
        assert result == "Feature"

    def test_init_read_oserror_falls_through(self, tmp_path: Path) -> None:
        """Lines 355-356: OSError caught."""
        from unittest.mock import patch

        from attune.help.bootstrap import _infer_description

        d = tmp_path / "feature"
        d.mkdir()
        (d / "__init__.py").write_text('"""hi."""\n')

        # Mock read_text to raise OSError specifically for __init__.py
        original_read = Path.read_text

        def fake_read(self, *args, **kwargs):
            if self.name == "__init__.py":
                raise OSError("perm denied")
            return original_read(self, *args, **kwargs)

        with patch.object(Path, "read_text", fake_read):
            result = _infer_description(d)
        # Falls through to humanized name
        assert result == "Feature"

    def test_readme_rst_fallback(self, tmp_path: Path) -> None:
        """README.rst is checked when README.md is absent."""
        from attune.help.bootstrap import _infer_description

        d = tmp_path / "feature"
        d.mkdir()
        (d / "README.rst").write_text("RST Description\n=================\n")
        result = _infer_description(d)
        assert result == "RST Description"

    def test_readme_oserror_falls_through(self, tmp_path: Path) -> None:
        """Lines 365-366: README read_text OSError → fall through."""
        from unittest.mock import patch

        from attune.help.bootstrap import _infer_description

        d = tmp_path / "feature"
        d.mkdir()
        (d / "README.md").write_text("Title\n")

        original_read = Path.read_text

        def fake_read(self, *args, **kwargs):
            if self.name in ("README.md", "README.rst", "README"):
                raise OSError("perm denied")
            return original_read(self, *args, **kwargs)

        with patch.object(Path, "read_text", fake_read):
            result = _infer_description(d)
        # All README reads fail → fall back to humanized name
        assert result == "Feature"

    def test_humanized_name_dashes(self, tmp_path: Path) -> None:
        """Line 369: humanize replaces dashes/underscores."""
        from attune.help.bootstrap import _infer_description

        d = tmp_path / "user-auth_module"
        d.mkdir()
        result = _infer_description(d)
        assert result == "User Auth Module"

    def test_init_docstring_value_error_caught(self, tmp_path: Path) -> None:
        """Lines 355-356: ValueError on missing closing delim → caught."""
        from attune.help.bootstrap import _infer_description

        d = tmp_path / "feature"
        d.mkdir()
        # Opening delim but no closing → ValueError on second .index()
        (d / "__init__.py").write_text('"""no closing\nlots of text\n')
        # Falls through to humanized name (no README either)
        result = _infer_description(d)
        assert result == "Feature"


class TestInferTags:
    """Cover _infer_tags edge cases."""

    def test_no_match_returns_empty(self) -> None:
        from attune.help.bootstrap import _infer_tags

        assert _infer_tags("randomname") == []

    def test_dedupes_tags(self) -> None:
        """'auth' adds ['security','users']; 'security' would also add ['security']."""
        from attune.help.bootstrap import _infer_tags

        tags = _infer_tags("auth-security")
        # Dedupe preserves order
        assert tags.count("security") == 1
