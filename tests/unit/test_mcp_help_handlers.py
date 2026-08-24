"""Tests for MCP help_init, help_status, help_update handlers.

These handlers were added to AttuneMCPServer for the
project-local help system. Tests verify:
- help_init scan and accept actions
- help_status with and without manifest
- help_update regeneration and dry_run
- help_lookup preamble and related modes
- Input validation and error paths
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("yaml")

from attune.mcp.server import AttuneMCPServer  # noqa: E402


@pytest.fixture()
def server(tmp_path: Path):
    """Create an AttuneMCPServer with workspace_root in tmp_path."""
    with patch("attune.mcp.version_check.check_for_updates", return_value=None):
        srv = AttuneMCPServer()
    srv._workspace_root = str(tmp_path)
    return srv


@pytest.fixture()
def project_with_manifest(tmp_path: Path):
    """Create a project with source files and .help/ manifest."""
    from attune.help.generator import generate_feature_templates
    from attune.help.manifest import Feature, FeatureManifest, save_manifest

    src = tmp_path / "src" / "auth"
    src.mkdir(parents=True)
    (src / "login.py").write_text("def login(): pass\n", encoding="utf-8")

    manifest = FeatureManifest(
        version=1,
        features={
            "auth": Feature(
                name="auth",
                description="Authentication system",
                files=["src/auth/**"],
            ),
        },
    )
    help_dir = tmp_path / ".help"
    save_manifest(manifest, help_dir)

    for feat in manifest.features.values():
        generate_feature_templates(feat, help_dir, tmp_path)

    return tmp_path


# ── help_init ─────────────────────────────────────────────


class TestHelpInit:
    """Tests for _handle_help_init."""

    @pytest.mark.asyncio
    async def test_scan_returns_proposals(self, server, tmp_path: Path) -> None:
        """Scan action discovers project features."""
        # Create minimal source structure
        src = tmp_path / "src" / "auth"
        src.mkdir(parents=True)
        (src / "login.py").write_text("def login(): pass\n", encoding="utf-8")
        (src / "__init__.py").write_text("", encoding="utf-8")

        result = await server.call_tool("help_init", {"action": "scan"})
        assert result["success"] is True
        assert "proposals" in result
        assert isinstance(result["proposals"], list)
        assert "count" in result

    @pytest.mark.asyncio
    async def test_accept_saves_manifest(self, server, tmp_path: Path) -> None:
        """Accept action saves manifest and generates templates."""
        # Create source files so template generation finds something
        src = tmp_path / "src" / "auth"
        src.mkdir(parents=True)
        (src / "login.py").write_text("def login(): pass\n", encoding="utf-8")

        result = await server.call_tool(
            "help_init",
            {
                "action": "accept",
                "accepted": [
                    {
                        "name": "auth",
                        "description": "Auth system",
                        "files": ["src/auth/**"],
                        "tags": ["security"],
                    }
                ],
            },
        )
        assert result["success"] is True
        assert result["features"] == 1
        assert (tmp_path / ".help" / "features.yaml").exists()
        assert isinstance(result["generated"], list)

    @pytest.mark.asyncio
    async def test_accept_missing_name_returns_error(self, server) -> None:
        """Accept with missing name returns validation error."""
        result = await server.call_tool(
            "help_init",
            {
                "action": "accept",
                "accepted": [{"description": "Auth"}],
            },
        )
        assert result["success"] is False
        assert "name" in result["error"]

    @pytest.mark.asyncio
    async def test_accept_missing_description_returns_error(self, server) -> None:
        """Accept with missing description returns validation error."""
        result = await server.call_tool(
            "help_init",
            {
                "action": "accept",
                "accepted": [{"name": "auth"}],
            },
        )
        assert result["success"] is False
        assert "description" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self, server) -> None:
        """Unknown action returns error."""
        result = await server.call_tool("help_init", {"action": "invalid"})
        assert result["success"] is False
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_accept_generation_failure_recorded(self, server, tmp_path: Path) -> None:
        """OSError during template generation is caught and recorded."""
        src = tmp_path / "src" / "auth"
        src.mkdir(parents=True)
        (src / "login.py").write_text("def login(): pass\n", encoding="utf-8")

        with patch(
            "attune.help.generator.generate_feature_templates",
            side_effect=OSError("disk full"),
        ):
            result = await server.call_tool(
                "help_init",
                {
                    "action": "accept",
                    "accepted": [
                        {
                            "name": "auth",
                            "description": "Auth",
                            "files": ["src/auth/**"],
                        }
                    ],
                },
            )
        assert result["success"] is True
        assert "auth" in result["failed"]
        assert len(result["generated"]) == 0


# ── help_status ───────────────────────────────────────────


class TestHelpStatus:
    """Tests for _handle_help_status."""

    @pytest.mark.asyncio
    async def test_returns_report(self, server, project_with_manifest: Path) -> None:
        """Returns staleness report when manifest exists."""
        server._workspace_root = str(project_with_manifest)
        result = await server.call_tool("help_status", {})
        assert result["success"] is True
        assert "stale_count" in result
        assert "current_count" in result
        assert "report" in result
        assert isinstance(result["report"], str)

    @pytest.mark.asyncio
    async def test_no_manifest_returns_error(self, server) -> None:
        """Returns error when .help/features.yaml missing."""
        result = await server.call_tool("help_status", {})
        assert result["success"] is False
        assert "features.yaml" in result["error"]


# ── help_update ───────────────────────────────────────────


class TestHelpUpdate:
    """Tests for _handle_help_update."""

    @pytest.mark.asyncio
    async def test_regenerates_stale(self, server, project_with_manifest: Path) -> None:
        """Regenerates templates when source files change."""
        server._workspace_root = str(project_with_manifest)

        # Make auth source stale
        (project_with_manifest / "src" / "auth" / "login.py").write_text(
            "def login(user, pw): pass\n", encoding="utf-8"
        )

        result = await server.call_tool("help_update", {})
        assert result["success"] is True
        assert result["stale_count"] >= 1
        assert result["regenerated_count"] >= 1

    @pytest.mark.asyncio
    async def test_dry_run_does_not_regenerate(self, server, project_with_manifest: Path) -> None:
        """Dry run returns counts without regenerating."""
        server._workspace_root = str(project_with_manifest)

        # Make auth source stale
        (project_with_manifest / "src" / "auth" / "login.py").write_text(
            "def login(u): pass\n", encoding="utf-8"
        )

        result = await server.call_tool("help_update", {"dry_run": True})
        assert result["success"] is True
        assert result["stale_count"] >= 1
        assert result["regenerated_count"] == 0

    @pytest.mark.asyncio
    async def test_no_manifest_returns_error(self, server) -> None:
        """Returns error when .help/features.yaml missing."""
        result = await server.call_tool("help_update", {})
        assert result["success"] is False
        assert "features.yaml" in result["error"]


# ── help_lookup ────────────────────────────────────────────


class TestHelpLookupModes:
    """Tests for help_lookup handler modes."""

    @pytest.mark.asyncio
    async def test_unknown_mode_returns_error(self, server) -> None:
        """Unknown mode returns error."""
        result = await server.call_tool(
            "help_lookup",
            {"topic": "auth", "mode": "nonexistent"},
        )
        assert result["success"] is False
        assert "Unknown mode" in result["error"]
