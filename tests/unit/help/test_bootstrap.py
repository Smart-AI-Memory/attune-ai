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
