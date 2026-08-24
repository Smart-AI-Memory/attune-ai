"""Network-gated tests for WorkflowHandlersMixin live API paths.

Skipped by default (-m "not network").  Run locally with:
    pytest -m network tests/unit/mcp/handlers/test_workflow_handlers_network.py

Requires ANTHROPIC_API_KEY in the environment or a .env file.
"""

from __future__ import annotations

import struct
import sys
import zlib
from unittest.mock import MagicMock, patch

import pytest

from attune.mcp.server import AttuneMCPServer


def _make_minimal_png() -> bytes:
    """Build a valid 1×1 red pixel PNG without external deps."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(ctype: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + ctype + data
        return c + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\x00\x00"  # filter=0, R=255 G=0 B=0
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def _make_server(workspace_root: str) -> AttuneMCPServer:
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            return AttuneMCPServer(workspace_root=workspace_root)


@pytest.mark.network
class TestRunAnalyzeImageLive:
    """Live Anthropic API tests for _run_analyze_image."""

    @pytest.mark.asyncio
    async def test_analyze_png_returns_analysis(self, tmp_path):
        """Happy-path: a 1×1 PNG is analysed via the live vision API."""
        import os

        from dotenv import load_dotenv

        load_dotenv()

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not available")

        png_file = tmp_path / "red_pixel.png"
        png_file.write_bytes(_make_minimal_png())

        server = _make_server(workspace_root=str(tmp_path))
        result = await server._run_analyze_image(
            {"image_path": str(png_file), "prompt": "Describe this image in one sentence."}
        )

        assert result["success"] is True, f"Expected success, got: {result}"
        assert isinstance(result.get("analysis"), str)
        assert len(result["analysis"]) > 0
        assert result["media_type"] == "image/png"
        assert result["file_size_bytes"] > 0
