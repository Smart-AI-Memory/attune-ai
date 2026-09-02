"""Behavioral coverage for the validated image-analysis workspace."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.workspaces.image_analysis import (
    ImageAnalysisWorkspaceAdapter,
    ImageAnalysisWorkspaceState,
    _image_info,
)


def _png(width: int = 2, height: int = 3) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
    )


def _repo_image(tmp_path: Path, name: str = "screen.png", data: bytes | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    (repo / name).write_bytes(data or _png())
    return repo


def _host(repo: Path) -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(ImageAnalysisWorkspaceAdapter(repo))
    return host


@pytest.mark.asyncio
async def test_opens_running_without_action_and_renders_fingerprint_and_analysis(
    tmp_path: Path,
) -> None:
    host = _host(_repo_image(tmp_path))
    running = await host.open(
        "image-analysis",
        {"image_path": "screen.png", "prompt": "What error is visible?"},
    )
    assert running.record.view.actions == ()
    assert running.record.action_nonce == ""
    assert "2 × 3" in running.markdown
    assert "image/png" in running.markdown
    progress = await host.publish(running.record.workspace_id, {"kind": "progress"})
    assert progress.record.revision == running.record.revision
    terminal = await host.publish(
        running.record.workspace_id,
        {
            "kind": "analysis_result",
            "success": True,
            "analysis": "A validation error is visible in the dialog.",
            "media_type": "image/png",
            "file_size_bytes": len(_png()),
            "provider": "fixture-vision",
        },
    )
    assert terminal.record.terminal is True
    assert terminal.result["dimensions"] == [2, 3]
    assert terminal.result["sha256"]
    assert "validation error" in terminal.render.markdown


@pytest.mark.asyncio
async def test_provider_failure_is_not_empty_success(tmp_path: Path) -> None:
    host = _host(_repo_image(tmp_path))
    running = await host.open("image-analysis", {"image_path": "screen.png"})
    failed = await host.publish(
        running.record.workspace_id,
        {
            "kind": "analysis_result",
            "success": False,
            "error": "ANTHROPIC_API_KEY not set",
        },
    )
    assert failed.result["success"] is False
    assert "did not complete" in failed.render.markdown
    assert "Analysis completed" not in failed.render.markdown


def test_png_gif_jpeg_and_webp_dimensions() -> None:
    assert _image_info(_png(4, 5)) == ("image/png", 4, 5)
    assert _image_info(b"GIF89a" + (6).to_bytes(2, "little") + (7).to_bytes(2, "little")) == (
        "image/gif",
        6,
        7,
    )
    jpeg = b"\xff\xd8\xff\xc0\x00\x11\x08\x00\x08\x00\x09" + b"\x00" * 10
    assert _image_info(jpeg) == ("image/jpeg", 9, 8)
    webp = bytearray(30)
    webp[:4] = b"RIFF"
    webp[8:12] = b"WEBP"
    webp[12:16] = b"VP8X"
    webp[24:27] = (10).to_bytes(3, "little")
    webp[27:30] = (11).to_bytes(3, "little")
    assert _image_info(bytes(webp)) == ("image/webp", 11, 12)

    lossless = bytearray(30)
    lossless[:4] = b"RIFF"
    lossless[8:12] = b"WEBP"
    lossless[12:16] = b"VP8L"
    lossless[20] = 0x2F
    lossless[21:25] = bytes([4, 0, 1, 0])
    assert _image_info(bytes(lossless)) == ("image/webp", 5, 5)

    lossy = bytearray(30)
    lossy[:4] = b"RIFF"
    lossy[8:12] = b"WEBP"
    lossy[12:16] = b"VP8 "
    lossy[23:26] = b"\x9d\x01\x2a"
    lossy[26:28] = (13).to_bytes(2, "little")
    lossy[28:30] = (14).to_bytes(2, "little")
    assert _image_info(bytes(lossy)) == ("image/webp", 13, 14)


def test_jpeg_scanner_skips_junk_standalone_and_non_sof_segments() -> None:
    jpeg = (
        b"\xff\xd8"
        + b"junk"
        + b"\xff\xd8"
        + b"\xff\xe0\x00\x04ab"
        + b"\xff\xc0\x00\x11\x08\x00\x08\x00\x09"
        + b"\x00" * 10
    )
    assert _image_info(jpeg) == ("image/jpeg", 9, 8)
    with pytest.raises(CommandWorkspaceError, match="not a supported"):
        _image_info(b"\xff\xd8" + b"\xff" * 20)
    with pytest.raises(CommandWorkspaceError, match="not a supported"):
        _image_info(b"\xff\xd8\xff\xe0\x00\x01" + b"\x00" * 20)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"image_path": ""}, "path and prompt"),
        ({"prompt": ""}, "path and prompt"),
        ({"media_type": "image/bmp"}, "media type"),
        ({"width": 0}, "dimensions"),
        ({"file_size_bytes": 0}, "file size"),
        ({"sha256": "bad"}, "sha256"),
        ({"stage": "preview"}, "stage"),
        ({"success": True, "analysis": ""}, "analysis text"),
        ({"success": False, "error": ""}, "error receipt"),
        ({"success": True, "analysis": "ok", "error": "bad"}, "cannot carry"),
    ],
)
def test_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "image_path": "screen.png",
        "prompt": "describe",
        "media_type": "image/png",
        "width": 1,
        "height": 1,
        "file_size_bytes": 24,
        "sha256": "a" * 64,
    }
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        ImageAnalysisWorkspaceState(**values)


def test_adapter_rejects_bad_paths_content_actions_and_events(tmp_path: Path) -> None:
    repo = _repo_image(tmp_path)
    adapter = ImageAnalysisWorkspaceAdapter(repo)
    with pytest.raises(CommandWorkspaceError, match="escapes"):
        adapter.create({"image_path": "../outside.png"})
    with pytest.raises(CommandWorkspaceError, match="does not exist"):
        adapter.create({"image_path": "missing.png"})
    (repo / "bad.bmp").write_bytes(_png())
    with pytest.raises(CommandWorkspaceError, match="extension is unsupported"):
        adapter.create({"image_path": "bad.bmp"})
    (repo / "bad.png").write_bytes(b"not-an-image")
    with pytest.raises(CommandWorkspaceError, match="not a supported"):
        adapter.create({"image_path": "bad.png"})
    (repo / "wrong.gif").write_bytes(_png())
    with pytest.raises(CommandWorkspaceError, match="does not match"):
        adapter.create({"image_path": "wrong.gif"})
    (repo / "zero.png").write_bytes(_png(0, 1))
    with pytest.raises(CommandWorkspaceError, match="dimensions"):
        adapter.create({"image_path": "zero.png"})
    with patch("attune.workspaces.image_analysis._MAX_IMAGE_BYTES", 1):
        with pytest.raises(CommandWorkspaceError, match="10MB"):
            adapter.create({"image_path": "screen.png"})
    with pytest.raises(CommandWorkspaceError, match="unknown image-analysis"):
        adapter.create({"image_path": "screen.png", "extra": True})
    running = adapter.create({"image_path": "screen.png"})
    with pytest.raises(CommandWorkspaceError, match="cannot be replaced"):
        adapter.create({"image_path": "screen.png"}, prior_state=running)
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.project(object())
    with pytest.raises(CommandWorkspaceError, match="no actions"):
        adapter.apply(running, object())
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.publish(object(), {"kind": "analysis_result"})
    with pytest.raises(CommandWorkspaceError, match="Unknown"):
        adapter.publish(running, {"kind": "other"})
    with pytest.raises(CommandWorkspaceError, match="success must be boolean"):
        adapter.publish(running, {"kind": "analysis_result", "success": "yes"})
    with pytest.raises(CommandWorkspaceError, match="canonical input"):
        adapter.publish(
            running,
            {"kind": "analysis_result", "success": False, "error": "x", "media_type": "x"},
        )
    terminal = replace(running, stage="receipt", success=False, error="x")
    with pytest.raises(CommandWorkspaceError, match="cannot accept"):
        adapter.publish(terminal, {"kind": "analysis_result"})
