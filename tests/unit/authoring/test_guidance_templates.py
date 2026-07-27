"""Tests for the tier-2 guidance-shaped meta templates.

Covers the four kinds added in the tier-2 expansion:

- quickstart.md.j2
- tip.md.j2
- note.md.j2
- comparison.md.j2

Parallels :mod:`tests.test_problem_templates` but exercises
the guidance shape rather than the problem shape.
Per-kind polish prompts for these types are also tested in
this file so the polish guidance stays in lockstep with
the template bodies.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from attune.authoring.generator import (
    _ALL_TEMPLATE_NAMES,
    _CORE_DEPTH_NAMES,
    _GUIDANCE_TEMPLATE_NAMES,
    _PROBLEM_TEMPLATE_NAMES,
    _PROJECT_DOC_NAMES,  # noqa: F401 — used in test_all_template_names_covers_all_groups
    generate_feature_templates,
)
from attune.authoring.manifest import Feature
from attune.authoring.polish_prompts import (
    ANTI_PATTERNS,
    SYSTEM_PROMPTS,
    get_system_prompt,
)

GUIDANCE_KINDS: tuple[str, ...] = _GUIDANCE_TEMPLATE_NAMES


@pytest.fixture
def guidance_feature() -> Feature:
    """A feature with classes and functions for rendering."""
    return Feature(
        name="auth",
        description="Authentication and authorization",
        files=["src/auth/**"],
        tags=["security", "users"],
    )


class TestGuidanceTemplateGeneration:
    """End-to-end rendering of each guidance-shaped template."""

    @pytest.mark.parametrize("kind", GUIDANCE_KINDS)
    def test_generates_each_kind(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        guidance_feature: Feature,
    ) -> None:
        """Each guidance kind renders a single file on request."""
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=guidance_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        assert len(result.templates) == 1
        generated = result.templates[0]
        assert generated.depth == kind
        assert generated.path.name == f"{kind}.md"
        assert generated.path.exists()

    @pytest.mark.parametrize("kind", GUIDANCE_KINDS)
    def test_frontmatter_has_type_field(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        guidance_feature: Feature,
    ) -> None:
        """Guidance templates carry both ``type`` and legacy
        ``depth`` frontmatter fields.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=guidance_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        assert f"type: {kind}" in content
        assert f"depth: {kind}" in content
        assert f"feature: {guidance_feature.name}" in content

    @pytest.mark.parametrize("kind", GUIDANCE_KINDS)
    def test_renders_feature_description_in_body(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        guidance_feature: Feature,
    ) -> None:
        """The feature description should surface in each
        template so the polish pass has a concrete anchor.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=guidance_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        assert guidance_feature.description in content

    @pytest.mark.parametrize("kind", GUIDANCE_KINDS)
    def test_renders_public_api_in_body(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        guidance_feature: Feature,
    ) -> None:
        """Public functions from the fixture project should
        appear in each rendered body.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=guidance_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        assert "authenticate" in content

    @pytest.mark.parametrize("kind", GUIDANCE_KINDS)
    def test_renders_tags_line(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        guidance_feature: Feature,
    ) -> None:
        """Every guidance template emits a ``**Tags:**`` line."""
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=guidance_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        assert "**Tags:**" in content
        for tag in guidance_feature.tags:
            assert f"`{tag}`" in content

    @pytest.mark.parametrize("kind", GUIDANCE_KINDS)
    def test_no_trailing_whitespace(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        guidance_feature: Feature,
    ) -> None:
        """Guidance templates honor the no-trailing-whitespace
        invariant that avoids pre-commit stash conflicts.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=guidance_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        for line in content.splitlines():
            assert line == line.rstrip(), f"{kind}: line has trailing whitespace: {line!r}"

    @pytest.mark.parametrize("kind", GUIDANCE_KINDS)
    def test_ends_with_single_newline(
        self,
        kind: str,
        help_dir: Path,
        project_root: Path,
        guidance_feature: Feature,
    ) -> None:
        """Every guidance template ends with exactly one
        trailing newline.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=guidance_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=[kind],
            )

        content = result.templates[0].path.read_text(encoding="utf-8")
        assert content.endswith("\n")
        assert not content.endswith("\n\n")


class TestGuidanceInteroperability:
    """Mixed calls that combine core, problem, and guidance
    kinds in a single invocation.
    """

    def test_mixed_core_problem_guidance(
        self,
        help_dir: Path,
        project_root: Path,
        guidance_feature: Feature,
    ) -> None:
        """Callers can mix kinds from all three groups in one
        call and receive the right set back.
        """
        depths = ["concept", "error", "quickstart", "comparison"]
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=guidance_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=depths,
            )

        produced = {t.depth for t in result.templates}
        assert produced == set(depths)

    def test_all_eleven_kinds_generate(
        self,
        help_dir: Path,
        project_root: Path,
        guidance_feature: Feature,
    ) -> None:
        """Generating every known kind in a single call
        produces 11 output files.
        """
        with patch.dict("os.environ", {}, clear=False):
            result = generate_feature_templates(
                feature=guidance_feature,
                help_dir=help_dir,
                project_root=project_root,
                depths=list(_ALL_TEMPLATE_NAMES),
            )

        kinds = {t.depth for t in result.templates}
        assert kinds == set(_ALL_TEMPLATE_NAMES)
        assert len(result.templates) == len(_ALL_TEMPLATE_NAMES)


class TestGuidanceTemplateConstants:
    """Regression guard on the template-kind constants."""

    def test_guidance_set_has_four_kinds(self) -> None:
        assert set(_GUIDANCE_TEMPLATE_NAMES) == {
            "quickstart",
            "tip",
            "note",
            "comparison",
        }

    def test_all_groups_disjoint(self) -> None:
        core = set(_CORE_DEPTH_NAMES)
        problem = set(_PROBLEM_TEMPLATE_NAMES)
        guidance = set(_GUIDANCE_TEMPLATE_NAMES)
        assert core.isdisjoint(problem)
        assert core.isdisjoint(guidance)
        assert problem.isdisjoint(guidance)

    def test_all_template_names_covers_all_groups(self) -> None:
        expected = (
            set(_CORE_DEPTH_NAMES)
            | set(_PROBLEM_TEMPLATE_NAMES)
            | set(_GUIDANCE_TEMPLATE_NAMES)
            | set(_PROJECT_DOC_NAMES)
        )
        assert set(_ALL_TEMPLATE_NAMES) == expected


class TestGuidancePolishPrompts:
    """Per-kind polish prompts for the guidance templates.

    These tests keep the polish guidance in lockstep with
    the template body — adding a new guidance kind without
    adding a matching prompt would silently fall back to
    the base rules.
    """

    @pytest.mark.parametrize("kind", GUIDANCE_KINDS)
    def test_prompt_exists_for_every_guidance_kind(self, kind: str) -> None:
        prompt = get_system_prompt(kind)
        assert prompt
        assert kind in SYSTEM_PROMPTS

    @pytest.mark.parametrize(
        "kind,expected_phrase",
        [
            ("quickstart", "runnable command"),
            ("tip", "one idea, not a checklist"),
            ("note", "factual, not instructional"),
            ("comparison", "decision rule"),
        ],
    )
    def test_kind_guidance_has_distinctive_phrase(self, kind: str, expected_phrase: str) -> None:
        """Each guidance-kind prompt carries a phrase unique
        to that kind — guards against silent regression
        to the base-only fallback.
        """
        prompt = SYSTEM_PROMPTS[kind]
        assert (
            expected_phrase in prompt
        ), f"{kind} prompt missing expected guidance: {expected_phrase!r}"

    @pytest.mark.parametrize("kind", GUIDANCE_KINDS)
    def test_anti_patterns_present(self, kind: str) -> None:
        """Every guidance kind has at least one anti-pattern
        registered and embedded in its prompt.
        """
        assert kind in ANTI_PATTERNS
        assert len(ANTI_PATTERNS[kind]) >= 1

        prompt = SYSTEM_PROMPTS[kind]
        for phrase in ANTI_PATTERNS[kind]:
            assert phrase in prompt, f"{kind}: anti-pattern {phrase!r} missing from prompt"
