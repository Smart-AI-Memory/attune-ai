"""Document generation pipeline orchestrator.

Ties together the three stages (outline, write, review) into
a single ``generate_docs()`` entry point.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from attune_author.doc_gen.config import DocGenConfig

logger = logging.getLogger(__name__)


@dataclass
class DocGenResult:
    """Result of document generation.

    Attributes:
        content: Final documentation content.
        outline: Generated outline.
        draft: Draft before review.
        stages_completed: List of completed stage names.
        source_path: Path to the source file (if provided).
    """

    content: str = ""
    outline: str = ""
    draft: str = ""
    stages_completed: list[str] = field(default_factory=list)
    source_path: str = ""


def generate_docs(
    target: str,
    config: DocGenConfig | None = None,
    output_path: str | None = None,
) -> DocGenResult:
    """Generate documentation for a source file or content.

    Runs the three-stage pipeline: outline -> write -> review.
    Requires ``ANTHROPIC_API_KEY`` environment variable.

    Args:
        target: File path or raw source content to document.
        config: Generation configuration (uses defaults if None).
        output_path: Optional path to write the output file.

    Returns:
        DocGenResult with the generated documentation.

    Raises:
        RuntimeError: If ANTHROPIC_API_KEY is not set.
        FileNotFoundError: If target is a path that doesn't exist.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY required for doc generation. "
            "Install with: pip install 'attune-author[ai]'"
        )

    from anthropic import Anthropic

    from attune_author.doc_gen.stages import (
        build_outline,
        review_content,
        write_content,
    )

    cfg = config or DocGenConfig()
    client = Anthropic(api_key=api_key)
    result = DocGenResult()

    # Read source content
    source_content = target
    target_path = Path(target)
    if target_path.exists() and target_path.is_file():
        source_content = target_path.read_text(encoding="utf-8")
        result.source_path = str(target_path)

    # Stage 1: Outline
    logger.info("Stage 1/3: Generating outline...")
    result.outline = build_outline(
        client=client,
        source_content=source_content,
        doc_type=cfg.doc_type,
        audience=cfg.audience,
        model=cfg.model,
        max_tokens=cfg.max_outline_tokens,
    )
    result.stages_completed.append("outline")

    # Stage 2: Write
    logger.info("Stage 2/3: Writing content...")
    result.draft = write_content(
        client=client,
        outline=result.outline,
        source_content=source_content,
        doc_type=cfg.doc_type,
        audience=cfg.audience,
        model=cfg.model,
        max_tokens=cfg.max_write_tokens,
        section_focus=cfg.section_focus or None,
    )
    result.stages_completed.append("write")

    # Stage 3: Review
    logger.info("Stage 3/3: Reviewing and polishing...")
    result.content = review_content(
        client=client,
        draft=result.draft,
        source_content=source_content,
        doc_type=cfg.doc_type,
        audience=cfg.audience,
        model=cfg.model,
        max_tokens=cfg.max_review_tokens,
    )
    result.stages_completed.append("review")

    # Write output if requested
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.content, encoding="utf-8")
        logger.info("Documentation written to %s", output_path)

    return result
