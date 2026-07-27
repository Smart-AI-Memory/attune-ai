"""Ground-truth context injection for the polish pass.

Phase 2 of the polish-fact-check spec
(``docs/specs/polish-fact-check``). Builds and injects authoritative
surface details (CLI ``--help`` output, public API signatures,
dataclass fields) into the polish prompt so the LLM has to anchor
on real names instead of inventing them.

The fact-check pass (Phase 1) catches mistakes after the fact.
This phase prevents them by changing what the model sees.
"""

from __future__ import annotations

import logging
from pathlib import Path

from attune.authoring.manifest import Feature

from .budget import enforce_budget
from .cli_help import extract_cli_help
from .config import GroundTruthConfig, load_config
from .dataclass_refs import extract_dataclasses
from .public_api import extract_public_api

logger = logging.getLogger(__name__)


#: System-prompt clause appended (by callers that inject context)
#: instructing the model to anchor on the ground-truth blocks. The
#: text is intentionally short and concrete — the existing polish
#: system prompts are already long, so we keep this addition tight.
ANCHORING_CLAUSE = (
    "\n\nThe user message contains <cli_help>, <public_api>, and "
    "<dataclasses> blocks with ground-truth surface details for this "
    "feature. When you reference a CLI flag, public function, import "
    "path, or dataclass field, it MUST appear verbatim in one of those "
    "blocks. If you need to describe something not in the ground "
    "truth, describe the behavior without inventing a specific name."
)


def build_context(
    feature: Feature,
    source_paths: list[Path],
    *,
    project_root: Path,
    config: GroundTruthConfig | None = None,
) -> str | None:
    """Build a ground-truth context string for the polish prompt.

    Args:
        feature: The feature being documented. ``feature.cli_command``
            drives the CLI ``--help`` block; absence skips that block.
        source_paths: Source ``.py`` files matched by ``feature.files``.
            Used for ``__all__``, public-API signatures, and dataclass
            extraction.
        project_root: Used to invoke the consumer's CLI for ``--help``.
        config: Optional explicit config; ``None`` loads from the
            project's ``pyproject.toml``.

    Returns:
        A context string with sentinel-tagged blocks, ready to pass as
        ``augmented_context=`` to :func:`attune.authoring.polish.polish_template`.
        Returns ``None`` if the feature is disabled or no source had any
        extractable surface.
    """
    cfg = config if config is not None else load_config(project_root)
    if not cfg.enabled:
        return None

    blocks: list[tuple[str, str]] = []

    cli_help_text = ""
    if cfg.inject_cli_help and feature.cli_command:
        cli_help_text = extract_cli_help(
            cfg.cli_executable,
            feature.cli_command,
            project_root=project_root,
        )
        if cli_help_text:
            blocks.append(("cli_help", cli_help_text))

    public_api_text = ""
    if cfg.inject_public_api:
        public_api_text = extract_public_api(source_paths)
        if public_api_text:
            blocks.append(("public_api", public_api_text))

    dataclass_text = ""
    if cfg.inject_dataclasses:
        dataclass_text = extract_dataclasses(source_paths)
        if dataclass_text:
            blocks.append(("dataclasses", dataclass_text))

    if not blocks:
        return None

    blocks = enforce_budget(blocks, cfg.budget_bytes)

    parts: list[str] = ["## Ground-truth context\n"]
    for tag, body in blocks:
        parts.append(f"<{tag}>\n{body.rstrip()}\n</{tag}>\n")
    return "\n".join(parts) + "\n"


__all__ = [
    "ANCHORING_CLAUSE",
    "GroundTruthConfig",
    "build_context",
    "enforce_budget",
    "extract_cli_help",
    "extract_dataclasses",
    "extract_public_api",
    "load_config",
]
