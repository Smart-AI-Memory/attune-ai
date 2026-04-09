"""Tests for the attune-author MCP server."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune_author.mcp.handlers import AttuneAuthorHandlers
from attune_author.mcp.path_validation import validate_file_path
from attune_author.mcp.server import AttuneAuthorMCPServer
from attune_author.mcp.tool_schemas import get_tools

# -- Path validation -------------------------------------------------


class TestValidateFilePath:
    """Tests for validate_file_path()."""

    def test_accepts_valid_path(self, tmp_path: Path) -> None:
        result = validate_file_path(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            validate_file_path("")

    def test_rejects_null_bytes(self) -> None:
        with pytest.raises(ValueError, match="null bytes"):
            validate_file_path("foo\x00bar")

    def test_rejects_system_dirs(self) -> None:
        for dangerous in ("/etc", "/sys", "/proc", "/dev"):
            with pytest.raises(ValueError, match="system directory"):
                validate_file_path(dangerous)

    def test_rejects_outside_allowed_dir(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="outside allowed directory"):
            validate_file_path("/usr", allowed_dir=str(tmp_path))

    def test_accepts_inside_allowed_dir(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        result = validate_file_path(str(sub), allowed_dir=str(tmp_path))
        assert result == sub.resolve()


# -- Tool schemas ----------------------------------------------------


class TestToolSchemas:
    """Validate tool schema structure."""

    def test_six_tools(self) -> None:
        tools = get_tools()
        assert len(tools) == 6

    def test_expected_tool_names(self) -> None:
        tools = get_tools()
        expected = {
            "author_init",
            "author_status",
            "author_generate",
            "author_maintain",
            "author_docs",
            "author_lookup",
        }
        assert set(tools) == expected

    def test_every_tool_has_description(self) -> None:
        for name, defn in get_tools().items():
            assert defn.get("description"), f"{name} missing description"

    def test_every_tool_has_input_schema(self) -> None:
        for name, defn in get_tools().items():
            schema = defn.get("input_schema")
            assert schema is not None, f"{name} missing input_schema"
            assert schema.get("type") == "object"
            assert "properties" in schema


# -- Server construction ---------------------------------------------


class TestServer:
    """Tests for AttuneAuthorMCPServer."""

    def test_construction(self, tmp_path: Path) -> None:
        srv = AttuneAuthorMCPServer(workspace_root=str(tmp_path))
        assert srv._workspace_root == str(tmp_path)
        assert len(srv.tools) == 6

    def test_dispatch_table_complete(self, tmp_path: Path) -> None:
        srv = AttuneAuthorMCPServer(workspace_root=str(tmp_path))
        missing = set(srv.tools) - set(srv._dispatch)
        assert not missing, f"Tools without handlers: {missing}"

    def test_call_tool_unknown(self, tmp_path: Path) -> None:
        srv = AttuneAuthorMCPServer(workspace_root=str(tmp_path))
        result = asyncio.run(srv.call_tool("nonexistent", {}))
        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    def test_call_tool_catches_handler_exceptions(self, tmp_path: Path) -> None:
        srv = AttuneAuthorMCPServer(workspace_root=str(tmp_path))
        # Patch a handler to raise
        srv._dispatch["author_status"] = MagicMock(side_effect=RuntimeError("boom"))

        async def call() -> dict:
            return await srv.call_tool("author_status", {})

        result = asyncio.run(call())
        assert result["success"] is False
        assert "boom" in result["error"]


# -- Handler integration ---------------------------------------------


class TestHandlersIntegration:
    """End-to-end tests for handlers via the server."""

    @pytest.fixture
    def project_with_help(self, tmp_path: Path) -> Path:
        """Create a tmp project with src/ and .help/ initialized."""
        # Source files
        src = tmp_path / "src" / "auth"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('"""Auth module."""\n', encoding="utf-8")
        (src / "login.py").write_text("def login() -> bool:\n    return True\n", encoding="utf-8")

        # .help/features.yaml
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        (help_dir / "features.yaml").write_text(
            "version: 1\n"
            "features:\n"
            "  auth:\n"
            "    description: Authentication\n"
            "    files:\n"
            "      - src/auth/**\n"
            "    tags: [security]\n",
            encoding="utf-8",
        )
        return tmp_path

    def test_author_status(self, project_with_help: Path) -> None:
        srv = AttuneAuthorMCPServer(workspace_root=str(project_with_help))
        result = asyncio.run(
            srv.call_tool(
                "author_status",
                {
                    "help_dir": str(project_with_help / ".help"),
                    "project_root": str(project_with_help),
                },
            )
        )
        assert result["success"] is True
        assert result["stale_count"] >= 1  # No template generated yet
        assert "Help Status" in result["report"]

    def test_author_generate(self, project_with_help: Path) -> None:
        srv = AttuneAuthorMCPServer(workspace_root=str(project_with_help))
        with patch.dict("os.environ", {}, clear=False):
            result = asyncio.run(
                srv.call_tool(
                    "author_generate",
                    {
                        "feature": "auth",
                        "help_dir": str(project_with_help / ".help"),
                        "project_root": str(project_with_help),
                    },
                )
            )
        assert result["success"] is True
        assert result["feature"] == "auth"
        assert len(result["generated"]) == 3
        depths = {t["depth"] for t in result["generated"]}
        assert depths == {"concept", "task", "reference"}

    def test_author_maintain_dry_run(self, project_with_help: Path) -> None:
        srv = AttuneAuthorMCPServer(workspace_root=str(project_with_help))
        result = asyncio.run(
            srv.call_tool(
                "author_maintain",
                {
                    "help_dir": str(project_with_help / ".help"),
                    "project_root": str(project_with_help),
                    "dry_run": True,
                },
            )
        )
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["regenerated_count"] == 0

    def test_author_lookup(self, project_with_help: Path) -> None:
        # First, generate templates so lookup has something to find
        srv = AttuneAuthorMCPServer(workspace_root=str(project_with_help))
        with patch.dict("os.environ", {}, clear=False):
            asyncio.run(
                srv.call_tool(
                    "author_generate",
                    {
                        "feature": "auth",
                        "help_dir": str(project_with_help / ".help"),
                        "project_root": str(project_with_help),
                    },
                )
            )

        # Now look it up
        result = asyncio.run(
            srv.call_tool(
                "author_lookup",
                {
                    "query": "auth",
                    "depth": "concept",
                    "help_dir": str(project_with_help / ".help"),
                },
            )
        )
        assert result["success"] is True
        assert result["feature"] == "auth"
        assert result["depth"] == "concept"
        assert "Auth" in result["content"]

    def test_author_init_creates_features(self, tmp_path: Path) -> None:
        # Set up minimal source structure
        src = tmp_path / "src" / "myapp" / "core"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('"""Core module."""\n', encoding="utf-8")
        (src / "engine.py").write_text("class Engine: pass\n", encoding="utf-8")
        (src / "utils.py").write_text("def util(): pass\n", encoding="utf-8")
        (src / "config.py").write_text("CONFIG = {}\n", encoding="utf-8")

        srv = AttuneAuthorMCPServer(workspace_root=str(tmp_path))
        result = asyncio.run(
            srv.call_tool(
                "author_init",
                {"project_root": str(tmp_path)},
            )
        )
        assert result["success"] is True
        assert (tmp_path / ".help" / "features.yaml").exists()

    def test_author_init_already_initialized(self, project_with_help: Path) -> None:
        srv = AttuneAuthorMCPServer(workspace_root=str(project_with_help))
        result = asyncio.run(
            srv.call_tool(
                "author_init",
                {"project_root": str(project_with_help)},
            )
        )
        assert result["success"] is True
        assert result.get("already_initialized") is True

    def test_path_validation_in_handlers(self, tmp_path: Path) -> None:
        srv = AttuneAuthorMCPServer(workspace_root=str(tmp_path))
        result = asyncio.run(srv.call_tool("author_status", {"help_dir": "/etc"}))
        assert result["success"] is False
        assert "system directory" in result["error"] or "outside" in result["error"]


# -- Direct handler tests --------------------------------------------


class TestHandlersDirect:
    """Test handlers without going through the server dispatch."""

    def test_author_lookup_unknown_query(self, tmp_path: Path) -> None:
        # Set up minimal manifest
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        (help_dir / "features.yaml").write_text(
            "version: 1\nfeatures:\n  foo:\n    description: Foo\n",
            encoding="utf-8",
        )

        h = AttuneAuthorHandlers(workspace_root=str(tmp_path))
        result = asyncio.run(
            h.author_lookup(
                {
                    "query": "nonexistent",
                    "help_dir": str(help_dir),
                }
            )
        )
        assert result["success"] is False
        assert "available" in result

    def test_author_lookup_invalid_depth(self, tmp_path: Path) -> None:
        h = AttuneAuthorHandlers(workspace_root=str(tmp_path))
        result = asyncio.run(h.author_lookup({"query": "foo", "depth": "invalid"}))
        assert result["success"] is False
        assert "depth must be" in result["error"]

    def test_author_generate_missing_feature(self, tmp_path: Path) -> None:
        h = AttuneAuthorHandlers(workspace_root=str(tmp_path))
        result = asyncio.run(h.author_generate({}))
        assert result["success"] is False
        assert "feature name is required" in result["error"]

    def test_author_docs_missing_target(self, tmp_path: Path) -> None:
        h = AttuneAuthorHandlers(workspace_root=str(tmp_path))
        result = asyncio.run(h.author_docs({}))
        assert result["success"] is False
        assert "target is required" in result["error"]
