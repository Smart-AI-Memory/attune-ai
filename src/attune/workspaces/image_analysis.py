"""Shared-renderer adapter for validated local image analysis."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from attune_forms import WorkspaceActionResponse, workspace_from_dict

from attune.elicitation.command_workspace import (
    CommandWorkspaceError,
    CommandWorkspaceProjection,
    CommandWorkspaceTransition,
)
from attune.security.path_validation import _validate_file_path

_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_SUFFIX_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_JPEG_SOF = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
)


def _jpeg_info(data: bytes) -> tuple[str, int, int] | None:
    index = 2
    while index + 8 <= len(data):
        while index < len(data) and data[index] != 0xFF:
            index += 1
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            return None
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            return None
        segment_length = int.from_bytes(data[index : index + 2], "big")
        if marker in _JPEG_SOF and index + 7 <= len(data):
            height = int.from_bytes(data[index + 3 : index + 5], "big")
            width = int.from_bytes(data[index + 5 : index + 7], "big")
            return "image/jpeg", width, height
        if segment_length < 2:
            return None
        index += segment_length
    return None


def _webp_info(data: bytes) -> tuple[str, int, int] | None:
    subtype = data[12:16]
    if subtype == b"VP8X":
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return "image/webp", width, height
    if subtype == b"VP8L" and data[20] == 0x2F:
        b1, b2, b3, b4 = data[21:25]
        width = 1 + b1 + ((b2 & 0x3F) << 8)
        height = 1 + ((b2 & 0xC0) >> 6) + (b3 << 2) + ((b4 & 0x0F) << 10)
        return "image/webp", width, height
    if subtype == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        width = int.from_bytes(data[26:28], "little") & 0x3FFF
        height = int.from_bytes(data[28:30], "little") & 0x3FFF
        return "image/webp", width, height
    return None


def _image_info(data: bytes) -> tuple[str, int, int]:
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if len(data) >= 10 and data[:6] in {b"GIF87a", b"GIF89a"}:
        return (
            "image/gif",
            int.from_bytes(data[6:8], "little"),
            int.from_bytes(data[8:10], "little"),
        )
    if len(data) >= 4 and data.startswith(b"\xff\xd8"):
        info = _jpeg_info(data)
        if info is not None:
            return info
    if len(data) >= 30 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        info = _webp_info(data)
        if info is not None:
            return info
    raise CommandWorkspaceError(["Image content is not a supported PNG, JPEG, GIF, or WebP"])


@dataclass(frozen=True)
class ImageAnalysisWorkspaceState:
    """Image-owned canonical input fingerprint and provider receipt."""

    image_path: str
    prompt: str
    media_type: str
    width: int
    height: int
    file_size_bytes: int
    sha256: str
    stage: str = "running"
    success: bool | None = None
    analysis: str = ""
    error: str = ""
    provider: str = ""

    def __post_init__(self) -> None:
        problems: list[str] = []
        if not self.image_path.strip() or not self.prompt.strip():
            problems.append("Image path and prompt are required")
        if self.media_type not in set(_SUFFIX_MIME.values()):
            problems.append("Image media type is invalid")
        if self.width < 1 or self.height < 1:
            problems.append("Image dimensions must be positive")
        if self.file_size_bytes < 1 or self.file_size_bytes > _MAX_IMAGE_BYTES:
            problems.append("Image file size is invalid")
        if len(self.sha256) != 64:
            problems.append("Image sha256 is invalid")
        if self.stage not in {"running", "receipt"}:
            problems.append("Image workspace stage is invalid")
        if self.success is True and not self.analysis.strip():
            problems.append("Successful image analysis requires analysis text")
        if self.success is False and not self.error.strip():
            problems.append("Failed image analysis requires an error receipt")
        if self.success is True and self.error:
            problems.append("Successful image analysis cannot carry an error")
        if problems:
            raise CommandWorkspaceError(problems)


class ImageAnalysisWorkspaceAdapter:
    """Validate binary input before an immediate read-only vision call."""

    adapter_id = "image-analysis"
    schema_version = 1

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> ImageAnalysisWorkspaceState:
        """Fingerprint a local image and enter running state without an action."""
        if prior_state is not None:
            raise CommandWorkspaceError(["Image-analysis workspaces cannot be replaced"])
        allowed = {"image_path", "prompt"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError(
                [f"unknown image-analysis intake key {key!r}" for key in unknown]
            )
        raw_path = str(intake.get("image_path", "")).strip()
        candidate = (self.repo_root / raw_path).resolve()
        try:
            relative = candidate.relative_to(self.repo_root).as_posix()
        except ValueError as exc:
            raise CommandWorkspaceError(["Image path escapes the repository"]) from exc
        validated = _validate_file_path(str(candidate), str(self.repo_root))
        if not validated.is_file():
            raise CommandWorkspaceError(["Image path does not exist"])
        size = validated.stat().st_size
        if size > _MAX_IMAGE_BYTES:
            raise CommandWorkspaceError(["Image file exceeds the 10MB limit"])
        suffix_mime = _SUFFIX_MIME.get(validated.suffix.lower())
        if suffix_mime is None:
            raise CommandWorkspaceError(["Image filename extension is unsupported"])
        data = validated.read_bytes()
        media_type, width, height = _image_info(data)
        if media_type != suffix_mime:
            raise CommandWorkspaceError(["Image extension does not match file content"])
        if width < 1 or height < 1:
            raise CommandWorkspaceError(["Image dimensions must be positive"])
        prompt = str(
            intake.get(
                "prompt",
                "Analyze this image and describe notable elements or errors.",
            )
        ).strip()
        return ImageAnalysisWorkspaceState(
            image_path=relative,
            prompt=prompt,
            media_type=media_type,
            width=width,
            height=height,
            file_size_bytes=size,
            sha256=hashlib.sha256(data).hexdigest(),
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render validated input or a truthful provider terminal receipt."""
        if not isinstance(state, ImageAnalysisWorkspaceState):
            raise CommandWorkspaceError(["image-analysis adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "stage": state.stage,
            "image": state.image_path,
            "sha256": state.sha256,
            "actions": [action.id for action in view.actions],
        }
        digest = hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return CommandWorkspaceProjection(view, digest if view.actions else "")

    def apply(
        self,
        state: object,
        response: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition:
        """Reject client actions because invocation authorized this read-only call."""
        raise CommandWorkspaceError(["image-analysis is read-only and has no actions"])

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish progress or one non-empty provider result."""
        if not isinstance(state, ImageAnalysisWorkspaceState):
            raise CommandWorkspaceError(["image-analysis adapter received incompatible state"])
        if state.stage != "running":
            raise CommandWorkspaceError(["Terminal image analysis cannot accept events"])
        kind = event.get("kind")
        if kind == "progress":
            return CommandWorkspaceTransition(state, authority_changed=False)
        if kind != "analysis_result":
            raise CommandWorkspaceError([f"Unknown image-analysis event {kind!r}"])
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Image provider success must be boolean"])
        analysis = str(event.get("analysis", "")).strip()
        error = str(event.get("error", "")).strip()
        returned_media = str(event.get("media_type", state.media_type))
        returned_size = event.get("file_size_bytes", state.file_size_bytes)
        if returned_media != state.media_type or returned_size != state.file_size_bytes:
            raise CommandWorkspaceError(["Image provider receipt does not match canonical input"])
        successor = replace(
            state,
            stage="receipt",
            success=success,
            analysis=analysis,
            error=error,
            provider=str(event.get("provider", "")).strip(),
        )
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={
                "success": success,
                "image_path": state.image_path,
                "media_type": state.media_type,
                "dimensions": [state.width, state.height],
                "file_size_bytes": state.file_size_bytes,
                "sha256": state.sha256,
                "analysis": analysis,
                "error": error,
            },
        )

    @staticmethod
    def _input_section(state: ImageAnalysisWorkspaceState) -> dict[str, object]:
        return {
            "heading": "Validated image",
            "blocks": [
                {
                    "kind": "key_value",
                    "items": [
                        {"label": "Path", "value": state.image_path},
                        {"label": "MIME", "value": state.media_type},
                        {"label": "Dimensions", "value": f"{state.width} × {state.height}"},
                        {"label": "Bytes", "value": str(state.file_size_bytes)},
                        {"label": "SHA-256", "value": state.sha256},
                    ],
                }
            ],
        }

    @classmethod
    def _view_data(cls, state: ImageAnalysisWorkspaceState) -> dict[str, object]:
        if state.stage == "running":
            return {
                "id": "execution",
                "title": "Image analysis running",
                "summary": "Validated local image; awaiting vision provider receipt.",
                "sections": [cls._input_section(state)],
            }
        summary = (
            "Image analysis completed."
            if state.success
            else f"Image analysis did not complete: {state.error}"
        )
        sections = [cls._input_section(state)]
        if state.success:
            sections.append(
                {
                    "heading": "Analysis",
                    "blocks": [
                        {
                            "kind": "key_value",
                            "items": [{"label": "Result", "value": state.analysis}],
                        }
                    ],
                }
            )
        return {
            "id": "receipt",
            "title": "Image analysis receipt",
            "summary": summary,
            "sections": sections,
        }
