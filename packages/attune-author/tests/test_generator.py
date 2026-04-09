"""Tests for attune_author.generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from attune_author.generator import (
    GenerationResult,
    generate_feature_templates,
)
from attune_author.manifest import Feature


class TestGenerateFeatureTemplates:
    """Tests for generate_feature_templates()."""

    def test_generates_three_templates(self, help_dir: Path, project_root: Path) -> None:
        """Test that all three depth templates are created."""
        feature = Feature(
            name="auth",
            description="Authentication and authorization",
            files=["src/auth/**"],
            tags=["security"],
        )

        # Patch out the polish pass (no API key in tests)
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=feature,
                help_dir=help_dir,
                project_root=project_root,
            )

        assert isinstance(result, GenerationResult)
        assert result.feature == "auth"
        assert len(result.templates) == 3

        depths = {t.depth for t in result.templates}
        assert depths == {"concept", "task", "reference"}

    def test_templates_have_frontmatter(self, help_dir: Path, project_root: Path) -> None:
        """Test that generated templates contain frontmatter."""
        feature = Feature(
            name="auth",
            description="Auth module",
            files=["src/auth/**"],
        )

        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=feature,
                help_dir=help_dir,
                project_root=project_root,
            )

        for t in result.templates:
            content = t.path.read_text(encoding="utf-8")
            assert content.startswith("---\n")
            assert "source_hash:" in content
            assert "feature: auth" in content

    def test_specific_depths(self, help_dir: Path, project_root: Path) -> None:
        """Test generating only specific depths."""
        feature = Feature(name="cli", description="CLI", files=["src/cli.py"])

        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=["concept"],
            )

        assert len(result.templates) == 1
        assert result.templates[0].depth == "concept"

    def test_rejects_path_traversal_name(self, help_dir: Path, project_root: Path) -> None:
        """Test that path traversal in feature name is blocked."""
        import pytest

        bad_names = ["../etc", "foo/bar", "test\x00null"]
        for name in bad_names:
            feature = Feature(name=name, description="bad")
            with pytest.raises(ValueError, match="Invalid feature name"):
                generate_feature_templates(
                    feature=feature,
                    help_dir=help_dir,
                    project_root=project_root,
                )

    def test_skips_manual_templates(self, help_dir: Path, project_root: Path) -> None:
        """Test that manual templates are not overwritten."""
        feature = Feature(
            name="auth",
            description="Auth",
            files=["src/auth/**"],
        )

        # Create a manual concept template
        tpl_dir = help_dir / "templates" / "auth"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "concept.md").write_text(
            "---\nstatus: manual\n---\nHand-written.\n",
            encoding="utf-8",
        )

        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=feature,
                help_dir=help_dir,
                project_root=project_root,
            )

        # concept should be skipped, task and reference generated
        depths = {t.depth for t in result.templates}
        assert "concept" not in depths
        assert "task" in depths
        assert "reference" in depths
