"""Tests for attune.authoring.generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from attune.authoring.generator import (
    GenerationResult,
    _split_signature,
    generate_feature_templates,
)
from attune.authoring.manifest import Feature


class TestSplitSignature:
    """Tests for ``_split_signature``."""

    def test_typed_params_and_return(self) -> None:
        params, returns = _split_signature(
            "authenticate(username: str, password: str) -> bool", "authenticate"
        )
        assert params == "username: str, password: str"
        assert returns == "bool"

    def test_no_return_annotation(self) -> None:
        params, returns = _split_signature("main()", "main")
        assert params == ""
        assert returns == ""

    def test_complex_return_with_pipe(self) -> None:
        params, returns = _split_signature("main(argv: list[str] | None = None) -> int", "main")
        assert params == "argv: list[str] | None = None"
        assert returns == "int"

    def test_unexpected_shape_returns_empty(self) -> None:
        # Defensive: anything not matching ``name(...)`` shouldn't crash.
        assert _split_signature("not a signature", "anything") == ("", "")


class TestReferenceTemplateColumns:
    """Reference template must surface Parameters/Returns columns
    from ``function_signatures`` without depending on the LLM polish
    pass — otherwise a polish bypass (no API key, lenient mode,
    cached miss) silently drops typed argument and return data that
    the AST already has.
    """

    def test_reference_table_includes_typed_params_and_return(
        self, help_dir: Path, project_root: Path
    ) -> None:
        feature = Feature(
            name="auth",
            description="Authentication and authorization",
            files=["src/auth/**"],
            tags=["security"],
        )

        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=["reference"],
                use_rag=False,
            )

        ref = next(t for t in result.templates if t.depth == "reference")
        content = ref.path.read_text(encoding="utf-8")

        # 4-column header is the structural fix — without polish,
        # the old template emitted only ``Function | Description | File``.
        assert "| Function | Parameters | Returns | Description | File |" in content
        # Typed parameters from the AST are surfaced verbatim.
        assert "`username: str, password: str`" in content
        # Return annotation is surfaced verbatim.
        assert "`bool`" in content
        # Feature description from features.yaml lands directly under
        # the title, not only via LLM-polish synthesis.
        assert "Authentication and authorization" in content


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
            # Schema requires `name`; combining feature+depth keeps it
            # distinct across features. Regression: prior versions
            # omitted `name`, which surfaced as a `missing-required`
            # diagnostic in the editor for every generated template.
            assert f"name: auth-{t.depth}" in content

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

    def test_feature_glob_with_zero_matches(
        self,
        help_dir: Path,
        project_root: Path,
    ) -> None:
        """A feature whose glob matches no files must still
        generate templates gracefully.

        The review flagged this as an undocumented edge case:
        source_hash is computed over an empty file list and
        the renderer sees ``file_count=0``. The generator
        must not crash and must still write the three core
        templates — callers depend on this when scaffolding
        features before the source code exists.
        """
        feature = Feature(
            name="ghost",
            description="No files yet",
            files=["src/does-not-exist/**"],
        )

        result = generate_feature_templates(
            feature=feature,
            help_dir=help_dir,
            project_root=project_root,
        )

        assert result.feature == "ghost"
        assert len(result.templates) == 3
        assert result.matched_files == []
        for t in result.templates:
            assert t.path.exists()
            content = t.path.read_text(encoding="utf-8")
            assert content.startswith("---\n")
            assert "feature: ghost" in content

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
