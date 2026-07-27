"""Tests for the tier-1 problem-shaped meta templates.

Covers the four template kinds added alongside the core
progressive-depth templates:

- error.md.j2
- warning.md.j2
- troubleshooting.md.j2
- faq.md.j2

These are generated only when the caller opts in via the
``depths=`` kwarg of ``generate_feature_templates``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from attune.authoring.generator import (
    _ALL_TEMPLATE_NAMES,
    _CORE_DEPTH_NAMES,
    _PROBLEM_TEMPLATE_NAMES,
    generate_feature_templates,
)
from attune.authoring.manifest import Feature

PROBLEM_KINDS: tuple[str, ...] = _PROBLEM_TEMPLATE_NAMES


@pytest.fixture
def problem_feature() -> Feature:
    """A feature with both classes and functions for rendering."""
    return Feature(
        name="auth",
        description="Authentication and authorization",
        files=["src/auth/**"],
        tags=["security", "users"],
    )


class TestProblemTemplateGeneration:
    """End-to-end rendering of each problem-shaped template."""

    @pytest.mark.parametrize("kind", PROBLEM_KINDS)
    def test_generates_each_kind(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
    ) -> None:
        """Each problem kind renders a single file on request."""
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        assert len(result.templates) == 1
        generated = result.templates[0]
        assert generated.depth == kind
        assert generated.path.name == f"{kind}.md"
        assert generated.path.exists()

    @pytest.mark.parametrize("kind", PROBLEM_KINDS)
    def test_frontmatter_has_type_field(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
    ) -> None:
        """Problem templates must carry the canonical ``type``
        field so attune-help can discriminate them without
        falling back to the legacy ``depth`` field.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        assert f"type: {kind}" in content
        # Legacy field stays in place for compat
        assert f"depth: {kind}" in content
        assert f"feature: {problem_feature.name}" in content

    @pytest.mark.parametrize("kind", PROBLEM_KINDS)
    def test_renders_feature_description_in_body(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
    ) -> None:
        """The feature description should surface in the first
        section of each problem template — callers rely on
        this as an anchor for the polish pass to rewrite.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        assert problem_feature.description in content

    @pytest.mark.parametrize("kind", PROBLEM_KINDS)
    def test_renders_public_api_in_body(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
    ) -> None:
        """Public functions should appear in the rendered body
        when the feature has any — otherwise the generated
        content is pure boilerplate.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        # ``authenticate`` is defined in the project_root fixture
        assert "authenticate" in content

    @pytest.mark.parametrize("kind", PROBLEM_KINDS)
    def test_renders_tags_line(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
    ) -> None:
        """The tags macro should emit a bolded ``**Tags:**``
        line when the feature has tags.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        assert "**Tags:**" in content
        for tag in problem_feature.tags:
            assert f"`{tag}`" in content

    @pytest.mark.parametrize("kind", PROBLEM_KINDS)
    def test_no_trailing_whitespace(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
    ) -> None:
        """The generator strips trailing whitespace to avoid
        perpetual pre-commit failures — problem templates
        must honor the same invariant.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        for line in content.splitlines():
            assert line == line.rstrip(), f"{kind}: line has trailing whitespace: {line!r}"

    @pytest.mark.parametrize("kind", PROBLEM_KINDS)
    def test_ends_with_single_newline(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
    ) -> None:
        """Every problem template ends with exactly one
        trailing newline.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        assert content.endswith("\n")
        assert not content.endswith("\n\n")


class TestDefaultBehaviorUnchanged:
    """Regression tests proving the new additions do not
    change what existing callers receive by default.
    """

    def test_default_depths_unchanged(
        self,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
    ) -> None:
        """A call with no ``depths=`` argument still produces
        only the three core progressive-depth templates.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
            )

        kinds = {t.depth for t in result.templates}
        assert kinds == set(_CORE_DEPTH_NAMES)
        assert len(result.templates) == 3

    def test_mixed_depths_generates_requested(
        self,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
    ) -> None:
        """Callers can freely mix core and problem kinds in a
        single call.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=["concept", "error", "faq"],
            )

        kinds = {t.depth for t in result.templates}
        assert kinds == {"concept", "error", "faq"}

    def test_unknown_kind_is_skipped_with_warning(
        self,
        help_dir: Path,
        project_root: Path,
        problem_feature: Feature,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """An unknown template kind is logged and skipped.
        Known kinds in the same call still render.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=problem_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=["error", "bogus-kind", "faq"],
            )

        kinds = {t.depth for t in result.templates}
        assert kinds == {"error", "faq"}
        assert "Unknown template kind 'bogus-kind'" in caplog.text


class TestTemplateConstants:
    """Unit tests for the generator's template-kind
    constants — new kinds must appear in the consolidated
    tuple, and core kinds must keep their identity.
    """

    def test_all_template_names_contains_core_and_problem(self) -> None:
        """The core and problem kinds must always appear in
        the consolidated tuple. Additional tuples (e.g.
        guidance kinds from tier-2) may also be present —
        those are tested in their own module.
        """
        assert set(_CORE_DEPTH_NAMES) <= set(_ALL_TEMPLATE_NAMES)
        assert set(_PROBLEM_TEMPLATE_NAMES) <= set(_ALL_TEMPLATE_NAMES)

    def test_core_and_problem_are_disjoint(self) -> None:
        assert set(_CORE_DEPTH_NAMES).isdisjoint(_PROBLEM_TEMPLATE_NAMES)

    def test_problem_set_has_four_kinds(self) -> None:
        assert set(_PROBLEM_TEMPLATE_NAMES) == {
            "error",
            "warning",
            "troubleshooting",
            "faq",
        }
