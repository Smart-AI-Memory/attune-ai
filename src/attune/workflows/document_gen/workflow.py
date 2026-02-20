"""Document Generation Workflow.

Main workflow orchestration for documentation generation.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from pathlib import Path
from typing import Any

from ..base import BaseWorkflow, ModelTier
from ..context import WorkflowContext
from ..services import ParsingService, PromptService
from .api_reference import APIReferenceMixin
from .chunked_generation import ChunkedGenerationMixin
from .config import DOC_GEN_STEPS, TOKEN_COSTS  # noqa: F401  # re-export
from .cost_management import DocGenCostMixin
from .outline_stage import OutlineStageMixin
from .polish_stage import PolishStageMixin
from .write_stage import WriteStageMixin

logger = logging.getLogger(__name__)


class DocumentGenerationWorkflow(
    DocGenCostMixin,
    ChunkedGenerationMixin,
    APIReferenceMixin,
    OutlineStageMixin,
    WriteStageMixin,
    PolishStageMixin,
    BaseWorkflow,
):
    """Multi-tier document generation workflow.

    Uses cheap models for outlining, capable models for content
    generation, and premium models for final polish and consistency
    review.

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.

    Usage:
        workflow = DocumentGenerationWorkflow()
        result = await workflow.execute(
            source_code="...",
            doc_type="api_reference",
            audience="developers"
        )
    """

    name = "doc-gen"
    description = "Cost-optimized documentation generation pipeline"
    stages = ["outline", "write", "polish"]
    tier_map = {
        "outline": ModelTier.CHEAP,
        "write": ModelTier.CAPABLE,
        "polish": ModelTier.PREMIUM,
    }

    def __init__(
        self,
        skip_polish_threshold: int = 1000,
        max_sections: int = 10,
        max_write_tokens: int | None = None,  # Auto-scaled if None
        section_focus: list[str] | None = None,
        chunked_generation: bool = True,
        sections_per_chunk: int = 3,
        max_cost: float = 5.0,  # Cost guardrail in USD
        cost_warning_threshold: float = 0.8,  # Warn at 80% of max_cost
        graceful_degradation: bool = True,  # Return partial results on error
        export_path: str | Path | None = None,  # Export docs to file
        max_display_chars: int = 45000,  # Max chars before chunking output
        enable_auth_strategy: bool = True,  # Enable intelligent auth routing
        **kwargs: Any,
    ):
        """Initialize workflow with enterprise-safe defaults.

        Args:
            skip_polish_threshold: Skip premium polish for docs under this
                token count (they're already good enough).
            max_sections: Maximum number of sections to generate.
            max_write_tokens: Maximum tokens for content generation.
                If None, auto-scales based on section count (recommended).
            section_focus: Optional list of specific sections to generate
                (e.g., ["Testing Guide", "API Reference"]).
            chunked_generation: If True, generates large docs in chunks to avoid
                truncation (default True).
            sections_per_chunk: Number of sections to generate per chunk (default 3).
            max_cost: Maximum cost in USD before stopping (default $5).
                Set to 0 to disable cost limits.
            cost_warning_threshold: Percentage of max_cost to trigger warning (default 0.8).
            graceful_degradation: If True, return partial results on errors
                instead of failing completely (default True).
            export_path: Optional directory to export generated docs (e.g., "docs/generated").
                If provided, documentation will be saved to a file automatically.
            max_display_chars: Maximum characters before splitting output into chunks
                for display (default 45000). Helps avoid terminal/UI truncation.
            enable_auth_strategy: If True, use intelligent subscription vs API routing
                based on module size (default True).

        """
        super().__init__(**kwargs)
        self.tier_map = dict(self.__class__.tier_map)  # Instance copy to avoid mutating class
        self.skip_polish_threshold = skip_polish_threshold
        self.max_sections = max_sections
        self._user_max_write_tokens = max_write_tokens  # Store user preference
        self.max_write_tokens = max_write_tokens or 16000  # Will be auto-scaled
        self.section_focus = section_focus
        self.chunked_generation = chunked_generation
        self.sections_per_chunk = sections_per_chunk
        self.max_cost = max_cost
        self.cost_warning_threshold = cost_warning_threshold
        self.graceful_degradation = graceful_degradation
        self.export_path = Path(export_path) if export_path else None
        self.max_display_chars = max_display_chars
        self.enable_auth_strategy = enable_auth_strategy
        self._total_content_tokens: int = 0
        self._accumulated_cost: float = 0.0
        self._cost_warning_issued: bool = False
        self._partial_results: dict = {}
        self._auth_mode_used: str | None = None  # Track which auth was recommended

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for document generation.

        Args:
            xml_config: Optional XML prompt configuration dict.

        Returns:
            WorkflowContext with prompt and parsing services.

        """
        return WorkflowContext(
            prompt=PromptService("doc-gen", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Skip polish for short documents."""
        if stage_name == "polish":
            if self._total_content_tokens < self.skip_polish_threshold:
                self.tier_map["polish"] = ModelTier.CAPABLE
                return False, None
        return False, None

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Execute a document generation stage."""
        if stage_name == "outline":
            return await self._outline(input_data, tier)
        if stage_name == "write":
            return await self._write(input_data, tier)
        if stage_name == "polish":
            return await self._polish(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")
