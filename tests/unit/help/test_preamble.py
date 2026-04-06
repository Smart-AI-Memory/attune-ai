"""Unit tests for attune.help.preamble module.

Tests cover:
- get_preamble: file lookup, read errors, delegation
- _extract_preamble: frontmatter skipping, heading skipping,
  blank lines, edge cases
- get_related_preambles: tag matching, scoring, limits

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.help.preamble import (
    _extract_preamble,
    get_preamble,
    get_related_preambles,
)

# -- Helpers ---------------------------------------------------------


def _write_task_template(help_dir: Path, feature: str, content: str) -> Path:
    """Write a task.md file for a feature under help_dir."""
    path = help_dir / "templates" / feature / "task.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# -- get_preamble ----------------------------------------------------


class TestGetPreamble:
    """Tests for get_preamble()."""

    def test_returns_preamble_from_task_template(self, tmp_path: Path) -> None:
        """Extracts preamble from a valid task template."""
        _write_task_template(
            tmp_path,
            "security",
            "---\ntitle: Security\n---\n\n# Security Audit\n\n"
            "Run a security audit when you need to check for vulnerabilities.\n",
        )
        result = get_preamble("security", help_dir=tmp_path)
        assert result == "Run a security audit when you need to check for vulnerabilities."

    def test_returns_none_when_no_template(self, tmp_path: Path) -> None:
        """Returns None when task.md does not exist."""
        result = get_preamble("nonexistent", help_dir=tmp_path)
        assert result is None

    def test_returns_none_on_read_error(self, tmp_path: Path) -> None:
        """Returns None when file read raises OSError."""
        task_path = tmp_path / "templates" / "broken" / "task.md"
        task_path.parent.mkdir(parents=True)
        task_path.write_text("content", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("denied")):
            result = get_preamble("broken", help_dir=tmp_path)
        assert result is None

    def test_uses_default_help_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back to _DEFAULT_HELP_DIR when help_dir is None."""
        monkeypatch.setattr(
            "attune.help.preamble._DEFAULT_HELP_DIR",
            tmp_path,
        )
        _write_task_template(
            tmp_path,
            "test-feat",
            "# Heading\n\nPreamble line here.\n",
        )
        result = get_preamble("test-feat")
        assert result == "Preamble line here."


# -- _extract_preamble -----------------------------------------------


class TestExtractPreamble:
    """Tests for _extract_preamble()."""

    def test_skips_frontmatter_and_heading(self) -> None:
        """Returns first content line after frontmatter and h1."""
        text = "---\ntitle: Test\n---\n\n# Heading\n\nPreamble here.\n"
        assert _extract_preamble(text) == "Preamble here."

    def test_no_frontmatter(self) -> None:
        """Returns first non-heading line when no frontmatter."""
        text = "# Heading\n\nJust a line.\n"
        assert _extract_preamble(text) == "Just a line."

    def test_skips_multiple_headings(self) -> None:
        """Skips all heading lines until content found."""
        text = "# H1\n## H2\n### H3\n\nContent here.\n"
        assert _extract_preamble(text) == "Content here."

    def test_empty_content(self) -> None:
        """Returns None for empty string."""
        assert _extract_preamble("") is None

    def test_only_frontmatter(self) -> None:
        """Returns None when file is only frontmatter."""
        text = "---\ntitle: Test\n---\n"
        assert _extract_preamble(text) is None

    def test_only_headings(self) -> None:
        """Returns None when file has only headings."""
        text = "---\ntitle: T\n---\n# H1\n## H2\n"
        assert _extract_preamble(text) is None

    def test_blank_lines_between_frontmatter_and_heading(self) -> None:
        """Blank lines between frontmatter and heading are skipped."""
        text = "---\nk: v\n---\n\n\n# Heading\n\nActual content.\n"
        assert _extract_preamble(text) == "Actual content."

    def test_content_immediately_after_frontmatter(self) -> None:
        """Content line right after frontmatter (no heading)."""
        text = "---\nk: v\n---\nDirect content.\n"
        assert _extract_preamble(text) == "Direct content."

    def test_whitespace_stripped(self) -> None:
        """Leading/trailing whitespace is stripped from result."""
        text = "# H\n\n   Indented content   \n"
        assert _extract_preamble(text) == "Indented content"


# -- get_related_preambles ------------------------------------------


@dataclass
class _FakeFeature:
    name: str
    tags: list[str] = field(default_factory=list)


@dataclass
class _FakeManifest:
    features: dict[str, _FakeFeature] = field(default_factory=dict)


class TestGetRelatedPreambles:
    """Tests for get_related_preambles()."""

    def test_returns_related_by_shared_tags(self, tmp_path: Path) -> None:
        """Returns features ranked by shared tag count."""
        manifest = _FakeManifest(
            features={
                "security": _FakeFeature("security", ["audit", "cli"]),
                "code-review": _FakeFeature("code-review", ["audit", "quality"]),
                "test-gen": _FakeFeature("test-gen", ["testing"]),
                "deep-review": _FakeFeature("deep-review", ["audit", "quality", "cli"]),
            }
        )
        # Write task templates for matches
        for feat in ["code-review", "deep-review"]:
            _write_task_template(tmp_path, feat, f"# {feat}\n\nUse {feat} when needed.\n")

        # Write features.yaml so manifest_path.exists() passes
        (tmp_path / "features.yaml").write_text("features: {}", encoding="utf-8")

        with patch("attune.help.manifest.load_manifest", return_value=manifest):
            result = get_related_preambles("security", help_dir=tmp_path)

        assert len(result) == 2
        # deep-review has 2 shared tags (audit, cli) > code-review has 1 (audit)
        assert result[0]["feature"] == "deep-review"
        assert result[1]["feature"] == "code-review"

    def test_returns_empty_when_no_manifest(self, tmp_path: Path) -> None:
        """Returns empty list when features.yaml missing."""
        result = get_related_preambles("anything", help_dir=tmp_path)
        assert result == []

    def test_returns_empty_when_feature_not_in_manifest(self, tmp_path: Path) -> None:
        """Returns empty list when current feature not found."""
        manifest = _FakeManifest(features={"other": _FakeFeature("other", ["tag"])})
        (tmp_path / "features.yaml").write_text("f: {}", encoding="utf-8")

        with patch("attune.help.manifest.load_manifest", return_value=manifest):
            result = get_related_preambles("missing", help_dir=tmp_path)
        assert result == []

    def test_returns_empty_when_feature_has_no_tags(self, tmp_path: Path) -> None:
        """Returns empty list when current feature has no tags."""
        manifest = _FakeManifest(features={"feat": _FakeFeature("feat", [])})
        (tmp_path / "features.yaml").write_text("f: {}", encoding="utf-8")

        with patch("attune.help.manifest.load_manifest", return_value=manifest):
            result = get_related_preambles("feat", help_dir=tmp_path)
        assert result == []

    def test_respects_max_results(self, tmp_path: Path) -> None:
        """Limits output to max_results."""
        manifest = _FakeManifest(
            features={
                "a": _FakeFeature("a", ["t1"]),
                "b": _FakeFeature("b", ["t1"]),
                "c": _FakeFeature("c", ["t1"]),
                "d": _FakeFeature("d", ["t1"]),
            }
        )
        for feat in ["b", "c", "d"]:
            _write_task_template(tmp_path, feat, f"# {feat}\n\nPreamble for {feat}.\n")
        (tmp_path / "features.yaml").write_text("f: {}", encoding="utf-8")

        with patch("attune.help.manifest.load_manifest", return_value=manifest):
            result = get_related_preambles("a", help_dir=tmp_path, max_results=2)
        assert len(result) == 2

    def test_skips_features_without_preamble(self, tmp_path: Path) -> None:
        """Excludes related features that have no task template."""
        manifest = _FakeManifest(
            features={
                "a": _FakeFeature("a", ["shared"]),
                "b": _FakeFeature("b", ["shared"]),
            }
        )
        (tmp_path / "features.yaml").write_text("f: {}", encoding="utf-8")
        # No task template for "b"

        with patch("attune.help.manifest.load_manifest", return_value=manifest):
            result = get_related_preambles("a", help_dir=tmp_path)
        assert result == []
