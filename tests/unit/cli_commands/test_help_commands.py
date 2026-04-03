"""Unit tests for attune.cli_commands.help_commands module.

Tests cover:
- _list_categories output and exit codes
- _list_category for valid/invalid categories
- _show_template delegation to populate + render_cli
- _filter_by_tag delegation to search_by_tag
- _list_all_tags delegation to list_tags
- cmd_help routing logic

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("frontmatter")

from attune.cli_commands.help_commands import (  # noqa: E402
    _filter_by_tag,
    _list_all_tags,
    _list_categories,
    _list_category,
    _show_template,
    cmd_help,
)

# -- Fixtures --------------------------------------------------------


@pytest.fixture()
def generated_dir(tmp_path: Path) -> Path:
    """Create a minimal generated/ directory structure."""
    gen = tmp_path / "generated"
    (gen / "errors").mkdir(parents=True)
    (gen / "warnings").mkdir(parents=True)
    (gen / "tips").mkdir(parents=True)
    (gen / "references").mkdir(parents=True)

    # Add a few template files
    (gen / "errors" / "shadow-dirs.md").write_text(
        "---\ntype: error\nname: shadow-dirs\n"
        "confidence: Verified\ntags: [imports]\nsource: test\n---\n"
        "# Error: Shadow dirs\n\n## Signature\n\nImportError\n",
        encoding="utf-8",
    )
    (gen / "tips" / "check-dirs.md").write_text(
        "---\ntype: tip\nname: check-dirs\n"
        "confidence: High\ntags: [imports]\nsource: test\n---\n"
        "# Tip: Check dirs\n\n## Recommendation\n\nCheck.\n",
        encoding="utf-8",
    )

    cross_links = {
        "stats": {"linked_templates": 1, "total_tags": 1},
        "links": {},
        "tag_index": {
            "imports": ["err-shadow-dirs", "tip-check-dirs"],
        },
    }
    (gen / "cross_links.json").write_text(
        json.dumps(cross_links),
        encoding="utf-8",
    )

    return gen


# -- _list_categories --------------------------------------------------


@pytest.mark.unit
class TestListCategories:
    """Tests for _list_categories."""

    def test_returns_0_when_templates_exist(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test exit code 0 when generated dir exists."""
        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=generated_dir,
        ):
            code = _list_categories()
        assert code == 0
        out = capsys.readouterr().out
        assert "errors" in out

    def test_returns_1_when_no_templates(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test exit code 1 when generated dir doesn't exist."""
        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=tmp_path / "nonexistent",
        ):
            code = _list_categories()
        assert code == 1
        assert "No generated templates" in capsys.readouterr().out

    def test_shows_counts(self, generated_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test output includes template counts."""
        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=generated_dir,
        ):
            _list_categories()
        out = capsys.readouterr().out
        assert "1" in out  # 1 error template


# -- _list_category ----------------------------------------------------


@pytest.mark.unit
class TestListCategory:
    """Tests for _list_category."""

    def test_lists_templates_in_category(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test listing templates in errors category."""
        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=generated_dir,
        ):
            code = _list_category("errors")
        assert code == 0
        assert "shadow-dirs" in capsys.readouterr().out

    def test_returns_1_for_missing_category(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test exit code 1 for nonexistent category."""
        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=generated_dir,
        ):
            code = _list_category("nonexistent")
        assert code == 1


# -- _show_template ----------------------------------------------------


@pytest.mark.unit
class TestShowTemplate:
    """Tests for _show_template."""

    def test_shows_template_by_prefixed_name(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test showing a template with prefix."""
        with patch(
            "attune.help.templates._DEFAULT_GENERATED_DIR",
            generated_dir,
        ):
            code = _show_template("err-shadow-dirs")
        assert code == 0
        out = capsys.readouterr().out
        assert "Shadow dirs" in out

    def test_shows_template_by_bare_name(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test showing a template by name without prefix."""
        with patch(
            "attune.help.templates._DEFAULT_GENERATED_DIR",
            generated_dir,
        ):
            code = _show_template("shadow-dirs")
        assert code == 0

    def test_returns_1_for_missing_template(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test exit code 1 when template not found."""
        with patch(
            "attune.help.templates._DEFAULT_GENERATED_DIR",
            generated_dir,
        ):
            code = _show_template("nonexistent-template")
        assert code == 1
        assert "not found" in capsys.readouterr().out


# -- _filter_by_tag ----------------------------------------------------


@pytest.mark.unit
class TestFilterByTag:
    """Tests for _filter_by_tag."""

    def test_lists_matching_templates(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test filtering by existing tag."""
        with patch(
            "attune.help.feedback._DEFAULT_GENERATED_DIR",
            generated_dir,
        ):
            code = _filter_by_tag("imports")
        assert code == 0
        out = capsys.readouterr().out
        assert "err-shadow-dirs" in out

    def test_returns_1_for_no_matches(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test exit code 1 when no templates match tag."""
        with patch(
            "attune.help.feedback._DEFAULT_GENERATED_DIR",
            generated_dir,
        ):
            code = _filter_by_tag("nonexistent")
        assert code == 1


# -- _list_all_tags ----------------------------------------------------


@pytest.mark.unit
class TestListAllTags:
    """Tests for _list_all_tags."""

    def test_lists_tags_with_counts(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test listing all tags."""
        with patch(
            "attune.help.feedback._DEFAULT_GENERATED_DIR",
            generated_dir,
        ):
            code = _list_all_tags()
        assert code == 0
        out = capsys.readouterr().out
        assert "imports" in out


# -- cmd_help routing ---------------------------------------------------


@pytest.mark.unit
class TestCmdHelp:
    """Tests for cmd_help routing."""

    def test_no_topic_lists_categories(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test no topic arg shows categories."""
        args = argparse.Namespace(topic=None, tag=None, tags=False)
        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=generated_dir,
        ):
            code = cmd_help(args)
        assert code == 0

    def test_category_topic_lists_category(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test category name routes to _list_category."""
        args = argparse.Namespace(topic="errors", tag=None, tags=False)
        with patch(
            "attune.cli_commands.help_commands._get_generated_dir",
            return_value=generated_dir,
        ):
            code = cmd_help(args)
        assert code == 0
        assert "shadow-dirs" in capsys.readouterr().out

    def test_tags_flag_lists_all_tags(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --tags flag routes to _list_all_tags."""
        args = argparse.Namespace(topic=None, tag=None, tags=True)
        with patch(
            "attune.help.feedback._DEFAULT_GENERATED_DIR",
            generated_dir,
        ):
            code = cmd_help(args)
        assert code == 0

    def test_tag_filter_routes(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --tag <tag> routes to _filter_by_tag."""
        args = argparse.Namespace(topic=None, tag="imports", tags=False)
        with patch(
            "attune.help.feedback._DEFAULT_GENERATED_DIR",
            generated_dir,
        ):
            code = cmd_help(args)
        assert code == 0

    def test_specific_template_routes(
        self, generated_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test specific template name routes to _show_template."""
        args = argparse.Namespace(topic="err-shadow-dirs", tag=None, tags=False)
        with patch(
            "attune.help.templates._DEFAULT_GENERATED_DIR",
            generated_dir,
        ):
            code = cmd_help(args)
        assert code == 0
