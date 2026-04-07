"""Tests for attune_author.preamble."""

from __future__ import annotations

from pathlib import Path

from attune_author.preamble import (
    _extract_preamble,
    get_preamble,
    get_related_preambles,
)


class TestExtractPreamble:
    """Tests for _extract_preamble()."""

    def test_extracts_first_paragraph(self) -> None:
        """Test extracting the first non-heading line."""
        text = (
            "---\n"
            "feature: foo\n"
            "---\n"
            "\n"
            "# Foo Title\n"
            "\n"
            "Use foo when you need bar.\n"
            "\n"
            "More content here.\n"
        )
        assert _extract_preamble(text) == "Use foo when you need bar."

    def test_skips_frontmatter(self) -> None:
        """Test that frontmatter is skipped."""
        text = "---\n" "key: value\n" "---\n" "First line.\n"
        assert _extract_preamble(text) == "First line."

    def test_skips_headings(self) -> None:
        """Test that headings are skipped."""
        text = "---\n" "---\n" "# Heading 1\n" "## Heading 2\n" "Real content.\n"
        assert _extract_preamble(text) == "Real content."

    def test_returns_none_for_empty(self) -> None:
        """Test None for content with no extractable preamble."""
        text = "---\n---\n\n# Only Heading\n"
        assert _extract_preamble(text) is None

    def test_no_frontmatter(self) -> None:
        """Test extraction when there's no frontmatter."""
        text = "First line.\n"
        assert _extract_preamble(text) == "First line."


class TestGetPreamble:
    """Tests for get_preamble()."""

    def test_reads_task_template(self, tmp_path: Path) -> None:
        """Test reading preamble from a task template."""
        help_dir = tmp_path / ".help"
        tpl_dir = help_dir / "templates" / "auth"
        tpl_dir.mkdir(parents=True)

        (tpl_dir / "task.md").write_text(
            "---\nfeature: auth\n---\n\n# Auth Tasks\n\n"
            "Use auth when you need to verify users.\n",
            encoding="utf-8",
        )

        result = get_preamble("auth", help_dir)
        assert result == "Use auth when you need to verify users."

    def test_returns_none_for_missing_template(self, tmp_path: Path) -> None:
        """Test None when task template doesn't exist."""
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        assert get_preamble("nonexistent", help_dir) is None

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        """Test that path traversal in feature name is blocked."""
        help_dir = tmp_path / ".help"
        help_dir.mkdir()

        for bad_name in ["../etc", "foo/bar", "test\x00null", ""]:
            assert get_preamble(bad_name, help_dir) is None

    def test_default_help_dir(self, tmp_path: Path, monkeypatch) -> None:
        """Test that .help/ in cwd is the default."""
        monkeypatch.chdir(tmp_path)
        tpl_dir = tmp_path / ".help" / "templates" / "foo"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "task.md").write_text("---\n---\nUse foo for stuff.\n", encoding="utf-8")

        assert get_preamble("foo") == "Use foo for stuff."


class TestGetRelatedPreambles:
    """Tests for get_related_preambles()."""

    def test_finds_related_by_tags(self, tmp_path: Path) -> None:
        """Test finding features related by shared tags."""
        help_dir = tmp_path / ".help"
        help_dir.mkdir()

        # Create manifest with tagged features
        (help_dir / "features.yaml").write_text(
            "version: 1\n"
            "features:\n"
            "  auth:\n"
            "    description: Auth\n"
            "    tags: [security, users]\n"
            "  permissions:\n"
            "    description: Permissions\n"
            "    tags: [security, access]\n"
            "  unrelated:\n"
            "    description: Other\n"
            "    tags: [misc]\n",
            encoding="utf-8",
        )

        # Create task templates with preambles
        for feat in ["permissions"]:
            tpl_dir = help_dir / "templates" / feat
            tpl_dir.mkdir(parents=True)
            (tpl_dir / "task.md").write_text(
                f"---\n---\nUse {feat} when needed.\n",
                encoding="utf-8",
            )

        results = get_related_preambles("auth", help_dir)

        assert len(results) >= 1
        feat_names = [r["feature"] for r in results]
        assert "permissions" in feat_names
        assert "unrelated" not in feat_names

    def test_returns_empty_for_no_manifest(self, tmp_path: Path) -> None:
        """Test empty list when manifest doesn't exist."""
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        assert get_related_preambles("foo", help_dir) == []

    def test_returns_empty_for_no_tags(self, tmp_path: Path) -> None:
        """Test empty list when feature has no tags."""
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        (help_dir / "features.yaml").write_text(
            "version: 1\nfeatures:\n  foo:\n    description: Foo\n",
            encoding="utf-8",
        )
        assert get_related_preambles("foo", help_dir) == []

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        """Test path traversal protection."""
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        for bad in ["../etc", "foo/bar", "x\x00y", ""]:
            assert get_related_preambles(bad, help_dir) == []
