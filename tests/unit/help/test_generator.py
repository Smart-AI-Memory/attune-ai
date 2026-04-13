"""Tests for help/generator.py — template generation from source files."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from attune.help.generator import (
    GenerationResult,
    generate_feature_templates,
)
from attune.help.manifest import Feature


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a project with Python source files."""
    src = tmp_path / "src" / "auth"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text(
        '"""User authentication module."""\n',
        encoding="utf-8",
    )
    (src / "login.py").write_text(
        '"""Login handlers."""\n\n\n'
        "class LoginManager:\n"
        '    """Manages user login sessions."""\n\n'
        "    def authenticate(self, user: str) -> bool:\n"
        '        """Authenticate a user."""\n'
        "        return True\n\n\n"
        "def create_session(user_id: str) -> str:\n"
        '    """Create a new session token."""\n'
        '    return "token"\n',
        encoding="utf-8",
    )
    (src / "permissions.py").write_text(
        "def check_permission(user: str, resource: str) -> bool:\n"
        '    """Check if user has permission."""\n'
        "    return True\n\n\n"
        "def _internal_helper():\n"
        "    pass\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def feature() -> Feature:
    return Feature(
        name="auth",
        description="User authentication and sessions",
        files=["src/auth/**"],
        tags=["security", "users"],
    )


@pytest.fixture()
def help_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".help"
    d.mkdir()
    return d


class TestGenerateFeatureTemplates:
    """Tests for generate_feature_templates()."""

    def test_generates_all_three_depths(
        self, feature: Feature, help_dir: Path, project: Path
    ) -> None:
        result = generate_feature_templates(feature, help_dir, project)
        assert isinstance(result, GenerationResult)
        assert len(result.templates) == 3
        depths = {t.depth for t in result.templates}
        assert depths == {"concept", "task", "reference"}

    def test_creates_directory_structure(
        self, feature: Feature, help_dir: Path, project: Path
    ) -> None:
        generate_feature_templates(feature, help_dir, project)
        template_dir = help_dir / "templates" / "auth"
        assert template_dir.is_dir()
        assert (template_dir / "concept.md").exists()
        assert (template_dir / "task.md").exists()
        assert (template_dir / "reference.md").exists()

    def test_concept_contains_description(
        self, feature: Feature, help_dir: Path, project: Path
    ) -> None:
        generate_feature_templates(feature, help_dir, project)
        text = (help_dir / "templates" / "auth" / "concept.md").read_text(encoding="utf-8")
        assert "User authentication and sessions" in text

    def test_concept_contains_classes(
        self, feature: Feature, help_dir: Path, project: Path
    ) -> None:
        generate_feature_templates(feature, help_dir, project)
        text = (help_dir / "templates" / "auth" / "concept.md").read_text(encoding="utf-8")
        assert "LoginManager" in text

    def test_reference_contains_functions(
        self, feature: Feature, help_dir: Path, project: Path
    ) -> None:
        generate_feature_templates(feature, help_dir, project)
        text = (help_dir / "templates" / "auth" / "reference.md").read_text(encoding="utf-8")
        assert "create_session" in text
        assert "check_permission" in text

    def test_reference_excludes_private(
        self, feature: Feature, help_dir: Path, project: Path
    ) -> None:
        generate_feature_templates(feature, help_dir, project)
        text = (help_dir / "templates" / "auth" / "reference.md").read_text(encoding="utf-8")
        assert "_internal_helper" not in text

    def test_frontmatter_contains_source_hash(
        self, feature: Feature, help_dir: Path, project: Path
    ) -> None:
        generate_feature_templates(feature, help_dir, project)
        text = (help_dir / "templates" / "auth" / "concept.md").read_text(encoding="utf-8")
        assert "source_hash:" in text
        assert "status: generated" in text
        assert "feature: auth" in text

    def test_records_matched_files(self, feature: Feature, help_dir: Path, project: Path) -> None:
        result = generate_feature_templates(feature, help_dir, project)
        assert len(result.matched_files) == 3  # __init__, login, permissions
        assert result.source_hash

    def test_selective_depths(self, feature: Feature, help_dir: Path, project: Path) -> None:
        result = generate_feature_templates(feature, help_dir, project, depths=["concept"])
        assert len(result.templates) == 1
        assert result.templates[0].depth == "concept"
        assert not (help_dir / "templates" / "auth" / "task.md").exists()

    def test_respects_manual_status(self, feature: Feature, help_dir: Path, project: Path) -> None:
        """Templates with status: manual are not overwritten."""
        template_dir = help_dir / "templates" / "auth"
        template_dir.mkdir(parents=True)
        manual_content = (
            "---\nfeature: auth\ndepth: concept\n"
            "source_hash: old\nstatus: manual\n---\n\n"
            "# Hand-written content\n"
        )
        (template_dir / "concept.md").write_text(manual_content, encoding="utf-8")

        result = generate_feature_templates(feature, help_dir, project)

        # concept.md should NOT be regenerated
        text = (template_dir / "concept.md").read_text(encoding="utf-8")
        assert "Hand-written content" in text

        # But task and reference should be generated
        depths = {t.depth for t in result.templates}
        assert "concept" not in depths
        assert "task" in depths
        assert "reference" in depths

    def test_overwrite_flag_ignores_manual(
        self, feature: Feature, help_dir: Path, project: Path
    ) -> None:
        template_dir = help_dir / "templates" / "auth"
        template_dir.mkdir(parents=True)
        (template_dir / "concept.md").write_text(
            "---\nfeature: auth\ndepth: concept\n"
            "source_hash: old\nstatus: manual\n---\n\n"
            "# Old\n",
            encoding="utf-8",
        )

        result = generate_feature_templates(feature, help_dir, project, overwrite=True)
        depths = {t.depth for t in result.templates}
        assert "concept" in depths

    def test_task_lists_key_files(self, feature: Feature, help_dir: Path, project: Path) -> None:
        generate_feature_templates(feature, help_dir, project)
        text = (help_dir / "templates" / "auth" / "task.md").read_text(encoding="utf-8")
        assert "src/auth/**" in text

    def test_reference_contains_tags(self, feature: Feature, help_dir: Path, project: Path) -> None:
        generate_feature_templates(feature, help_dir, project)
        text = (help_dir / "templates" / "auth" / "reference.md").read_text(encoding="utf-8")
        assert "`security`" in text
        assert "`users`" in text

    def test_unknown_depth_skipped(self, feature: Feature, help_dir: Path, project: Path) -> None:
        """Unknown depth names are skipped with a warning."""
        result = generate_feature_templates(feature, help_dir, project, depths=["bogus"])
        assert len(result.templates) == 0

    def test_syntax_error_file_skipped(
        self, feature: Feature, help_dir: Path, project: Path
    ) -> None:
        """Files with syntax errors are skipped gracefully."""
        (project / "src" / "auth" / "broken.py").write_text("def oops(\n", encoding="utf-8")
        result = generate_feature_templates(feature, help_dir, project)
        # Still generates all 3 templates from the valid files
        assert len(result.templates) == 3

    def test_async_functions_included(self, help_dir: Path, tmp_path: Path) -> None:
        """Async public functions appear in generated reference."""
        src = tmp_path / "src" / "svc"
        src.mkdir(parents=True)
        (src / "handler.py").write_text(
            "async def fetch_data(url: str) -> dict:\n"
            '    """Fetch data from URL."""\n'
            "    return {}\n",
            encoding="utf-8",
        )
        feat = Feature(
            name="svc",
            description="Service layer",
            files=["src/svc/**"],
            tags=[],
        )
        result = generate_feature_templates(feat, help_dir, tmp_path)
        text = (help_dir / "templates" / "svc" / "reference.md").read_text(encoding="utf-8")
        assert "fetch_data" in text
        assert len(result.templates) == 3

    def test_invalid_feature_name_raises(self, help_dir: Path, project: Path) -> None:
        """Feature names with path traversal characters are rejected."""
        bad_names = ["../../etc", "a/b", "a\\b", "a\x00b", ""]
        for name in bad_names:
            feat = Feature(name=name, description="bad", files=[])
            with pytest.raises(ValueError, match="Invalid feature name"):
                generate_feature_templates(feat, help_dir, project)


class TestPolishIntegration:
    """Integration: generate_feature_templates calls polish when API key is set."""

    def test_polish_called_and_output_written(
        self, feature: Feature, help_dir: Path, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Polished content is written to disk when API key is available."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret

        def fake_polish(content: str, name: str, summary: str) -> str:
            return content.replace("# Auth", "# Auth (polished)")

        with patch(
            "attune.help.polish.polish_template",
            side_effect=fake_polish,
        ):
            generate_feature_templates(feature, help_dir, project, depths=["concept"])

        text = (help_dir / "templates" / "auth" / "concept.md").read_text(encoding="utf-8")
        assert "(polished)" in text

    def test_polish_skipped_without_api_key(
        self, feature: Feature, help_dir: Path, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Templates are still written when API key is absent (no polish)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        generate_feature_templates(feature, help_dir, project, depths=["concept"])

        text = (help_dir / "templates" / "auth" / "concept.md").read_text(encoding="utf-8")
        assert "# Auth" in text
        assert "(polished)" not in text
