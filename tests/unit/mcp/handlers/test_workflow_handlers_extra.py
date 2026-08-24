"""Tests for uncovered branches in WorkflowHandlersMixin.

Covers _run_analyze_batch, _run_analyze_image early-return paths, and the
non-dict branch of _run_research_synthesis.
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.mcp.server import AttuneMCPServer


@pytest.fixture(autouse=True)
def _bypass_path_validation():
    def _passthrough(path, **_kwargs):
        return PurePosixPath(path)

    with patch(
        "attune.security.path_validation._validate_file_path",
        side_effect=_passthrough,
    ):
        yield


def _make_server(workspace_root: str = "/") -> AttuneMCPServer:
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            return AttuneMCPServer(workspace_root=workspace_root)


# ---------------------------------------------------------------------------
# _run_analyze_batch
# ---------------------------------------------------------------------------


class TestRunAnalyzeBatch:
    @pytest.mark.asyncio
    async def test_empty_requests_returns_error(self):
        server = _make_server()
        result = await server._run_analyze_batch({"requests": []})
        assert result["success"] is False
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_missing_requests_key_returns_error(self):
        server = _make_server()
        result = await server._run_analyze_batch({})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_valid_requests_returns_results(self):
        server = _make_server()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.task_id = "t1"
        mock_result.output = "done"
        mock_result.error = None

        mock_workflow = MagicMock()
        mock_workflow.execute_batch = AsyncMock(return_value=[mock_result])

        with patch(
            "attune.workflows.batch_processing.BatchProcessingWorkflow",
            return_value=mock_workflow,
        ):
            result = await server._run_analyze_batch(
                {
                    "requests": [
                        {
                            "task_id": "t1",
                            "task_type": "code_review",
                            "input_data": {"code": "x = 1"},
                        }
                    ]
                }
            )

        assert result["success"] is True
        assert result["total"] == 1
        assert result["succeeded"] == 1
        assert result["failed"] == 0
        assert result["results"][0]["task_id"] == "t1"

    @pytest.mark.asyncio
    async def test_failed_request_counted(self):
        server = _make_server()

        mock_ok = MagicMock(success=True, task_id="ok", output="good", error=None)
        mock_fail = MagicMock(success=False, task_id="bad", output=None, error="oops")

        mock_workflow = MagicMock()
        mock_workflow.execute_batch = AsyncMock(return_value=[mock_ok, mock_fail])

        with patch(
            "attune.workflows.batch_processing.BatchProcessingWorkflow",
            return_value=mock_workflow,
        ):
            result = await server._run_analyze_batch(
                {
                    "requests": [
                        {"task_id": "ok", "task_type": "t", "input_data": {}},
                        {"task_id": "bad", "task_type": "t", "input_data": {}},
                    ]
                }
            )

        assert result["succeeded"] == 1
        assert result["failed"] == 1


# ---------------------------------------------------------------------------
# _run_analyze_image early-return paths
# ---------------------------------------------------------------------------


class TestRunAnalyzeImageEarlyReturns:
    @pytest.mark.asyncio
    async def test_missing_image_path_returns_error(self):
        server = _make_server()
        result = await server._run_analyze_image({})
        assert result["success"] is False
        assert "image_path" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_image_path_returns_error(self):
        server = _make_server()
        result = await server._run_analyze_image({"image_path": ""})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self, tmp_path):
        server = _make_server(workspace_root=str(tmp_path))
        nonexistent = tmp_path / "missing.png"

        with patch(
            "attune.security.path_validation._validate_file_path",
            return_value=nonexistent,
        ):
            result = await server._run_analyze_image({"image_path": str(nonexistent)})

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_file_too_large_returns_error(self, tmp_path):
        large_file = tmp_path / "big.png"
        large_file.write_bytes(b"x" * 100)

        with (
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=large_file,
            ),
            patch.object(
                large_file.__class__,
                "stat",
                return_value=MagicMock(st_size=11 * 1024 * 1024),
            ),
        ):
            server = _make_server(workspace_root=str(tmp_path))
            result = await server._run_analyze_image({"image_path": str(large_file)})

        assert result["success"] is False
        assert "large" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_unsupported_format_returns_error(self, tmp_path):
        bmp_file = tmp_path / "image.bmp"
        bmp_file.write_bytes(b"BM" + b"\x00" * 50)

        with patch(
            "attune.security.path_validation._validate_file_path",
            return_value=bmp_file,
        ):
            server = _make_server(workspace_root=str(tmp_path))
            result = await server._run_analyze_image({"image_path": str(bmp_file)})

        assert result["success"] is False
        assert "unsupported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_no_api_key_returns_error(self, tmp_path, monkeypatch):
        png_file = tmp_path / "img.png"
        png_file.write_bytes(b"\x89PNG" + b"\x00" * 50)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with patch(
            "attune.security.path_validation._validate_file_path",
            return_value=png_file,
        ):
            server = _make_server(workspace_root=str(tmp_path))
            result = await server._run_analyze_image({"image_path": str(png_file)})

        assert result["success"] is False
        assert "ANTHROPIC_API_KEY" in result["error"]


# ---------------------------------------------------------------------------
# _run_research_synthesis — non-dict final output branch
# ---------------------------------------------------------------------------


class TestRunResearchSynthesisNonDict:
    @pytest.mark.asyncio
    async def test_non_dict_result_returns_string_output(self):
        server = _make_server()

        mock_result = MagicMock()
        mock_result.final_output = "plain text synthesis"
        mock_result.cost_report = MagicMock(total_cost=0.02)

        with patch(
            "attune.workflows.research_synthesis.ResearchSynthesisWorkflow.execute",
            new=AsyncMock(return_value=mock_result),
        ):
            result = await server._run_research_synthesis({"path": "docs", "depth": "quick"})

        assert result["success"] is True
        assert "output" in result
        assert "plain text synthesis" in result["output"]


# ---------------------------------------------------------------------------
# _run_doc_gen — OSError path when reading source file
# ---------------------------------------------------------------------------


class TestRunDocGenReadError:
    @pytest.mark.asyncio
    async def test_unreadable_source_file_falls_back_to_empty(self, tmp_path):
        server = _make_server(workspace_root=str(tmp_path))

        # File exists but raises OSError on read (simulate permissions issue)
        bad_file = tmp_path / "locked.py"
        bad_file.write_text("# code")

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = {"document": "generated doc"}
        mock_result.cost_report = MagicMock(total_cost=0.01)

        mock_workflow_instance = MagicMock()
        mock_workflow_instance.execute = AsyncMock(return_value=mock_result)

        with (
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=bad_file,
            ),
            patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")),
            patch(
                "attune.workflows.document_gen.DocumentGenerationWorkflow",
                return_value=mock_workflow_instance,
            ),
        ):
            result = await server._run_doc_gen({"source_path": str(bad_file)})

        # Workflow was called with empty source_code (fallback), result returned
        assert result["success"] is True
