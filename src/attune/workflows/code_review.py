"""Code Review Workflow

A tiered code analysis pipeline:
1. Haiku: Classify change type (cheap, fast)
2. Sonnet: Security scan + bug pattern matching
3. Opus: Architectural review (conditional on complexity)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from typing import Any

from .base import BaseWorkflow, ModelTier
from .code_review_analysis_mixin import CodeReviewAnalysisMixin
from .code_review_architect import ArchitectMixin
from .code_review_classify import ClassifyMixin
from .code_review_crew_mixin import CrewMixin
from .code_review_report import format_code_review_report  # noqa: F401
from .code_review_scan import ScanMixin
from .context import WorkflowContext
from .services import ParsingService, PromptService
from .step_config import WorkflowStepConfig

logger = logging.getLogger(__name__)

# Quality check thresholds
MAX_FILE_LINES = 500
CHARS_PER_TOKEN_ESTIMATE = 4

# Define step configurations for executor-based execution
CODE_REVIEW_STEPS = {
    "architect_review": WorkflowStepConfig(
        name="architect_review",
        task_type="architectural_decision",  # Premium tier task
        tier_hint="premium",
        description="Comprehensive architectural code review",
        max_tokens=3000,
    ),
}


class CodeReviewWorkflow(
    ClassifyMixin,
    ScanMixin,
    ArchitectMixin,
    CrewMixin,
    CodeReviewAnalysisMixin,
    BaseWorkflow,
):
    """Multi-tier code review workflow.

    Uses cheap models for classification, capable models for security
    and bug scanning, and premium models only for complex architectural
    reviews (10+ files or core module changes).

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.

    Usage:
        workflow = CodeReviewWorkflow()
        result = await workflow.execute(
            diff="...",
            files_changed=["src/main.py", "tests/test_main.py"],
            is_core_module=False
        )
    """

    name = "code-review"
    description = "Tiered code analysis with conditional premium review"
    stages = [
        "classify",
        "scan",
        "perf_check",
        "perf_check_deep",
        "health_monitor",
        "quality_check",
        "quality_check_deep",
        "architect_review",
    ]
    tier_map = {
        "classify": ModelTier.CHEAP,
        "scan": ModelTier.CAPABLE,
        "perf_check": ModelTier.CHEAP,
        "perf_check_deep": ModelTier.CAPABLE,
        "health_monitor": ModelTier.CHEAP,
        "quality_check": ModelTier.CHEAP,
        "quality_check_deep": ModelTier.CAPABLE,
        "architect_review": ModelTier.PREMIUM,
    }

    def __init__(
        self,
        file_threshold: int = 10,
        core_modules: list[str] | None = None,
        use_crew: bool = True,
        crew_config: dict | None = None,
        enable_auth_strategy: bool = True,
        **kwargs: Any,
    ):
        """Initialize workflow.

        Args:
            file_threshold: Number of files above which premium review is used.
            core_modules: List of module paths considered "core" (trigger premium).
            use_crew: Enable CodeReviewCrew for comprehensive 5-agent analysis (default: True).
            crew_config: Configuration dict for CodeReviewCrew.
            enable_auth_strategy: If True, use intelligent subscription vs API routing
                based on module size (default True).

        """
        super().__init__(**kwargs)
        self.file_threshold = file_threshold
        self.core_modules = core_modules or [
            "src/core/",
            "src/security/",
            "src/auth/",
            "empathy_os/core.py",
            "empathy_os/security/",
        ]
        self.use_crew = use_crew
        self.crew_config = crew_config or {}
        self.enable_auth_strategy = enable_auth_strategy
        self._needs_architect_review: bool = False
        self._change_type: str = "unknown"
        self._crew: Any = None
        self._crew_available = False
        self._auth_mode_used: str | None = None

        # Dynamically configure stages based on crew setting
        if use_crew:
            self.stages = [
                "classify",
                "crew_review",
                "scan",
                "perf_check",
                "perf_check_deep",
                "health_monitor",
                "quality_check",
                "quality_check_deep",
                "architect_review",
            ]
            self.tier_map = {
                "classify": ModelTier.CHEAP,
                "crew_review": ModelTier.CAPABLE,
                "scan": ModelTier.CAPABLE,
                "perf_check": ModelTier.CHEAP,
                "perf_check_deep": ModelTier.CAPABLE,
                "health_monitor": ModelTier.CHEAP,
                "quality_check": ModelTier.CHEAP,
                "quality_check_deep": ModelTier.CAPABLE,
                "architect_review": ModelTier.PREMIUM,
            }

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for code review.

        Args:
            xml_config: Optional XML prompt configuration dict.
                Defaults to XML disabled --- benchmarks on Claude 4.x show
                +56% cost overhead with no quality improvement for code review.

        Returns:
            WorkflowContext with prompt and parsing services.
        """
        if xml_config is None:
            xml_config = {"enabled": False}
        return WorkflowContext(
            prompt=PromptService("code-review", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Skip stages when appropriate."""
        # Skip all stages after classify if there was an input error
        if isinstance(input_data, dict) and input_data.get("error"):
            if stage_name != "classify":
                return True, "Skipped due to input validation error"

        # Skip crew review if crew is not available
        if stage_name == "crew_review" and not self._crew_available:
            return True, "CodeReviewCrew not available"

        # Skip perf_check and quality_check if no files to analyze
        if stage_name in ("perf_check", "quality_check"):
            files = input_data.get("files_changed", []) if isinstance(input_data, dict) else []
            if not files:
                return True, f"No files_changed provided for {stage_name}"

        # Skip deep stages if their CHEAP counterpart found nothing
        if stage_name == "perf_check_deep":
            count = input_data.get("perf_finding_count", 0) if isinstance(input_data, dict) else 0
            if count == 0:
                return True, "No perf findings to enrich"

        if stage_name == "quality_check_deep":
            count = (
                input_data.get("quality_finding_count", 0) if isinstance(input_data, dict) else 0
            )
            if count == 0:
                return True, "No quality findings to enrich"

        # Skip architectural review if change is simple
        if stage_name == "architect_review" and not self._needs_architect_review:
            return True, "Simple change - architectural review not needed"
        return False, None

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Execute a code review stage."""
        if stage_name == "classify":
            return await self._classify(input_data, tier)
        if stage_name == "crew_review":
            return await self._crew_review(input_data, tier)
        if stage_name == "scan":
            return await self._scan(input_data, tier)
        if stage_name == "perf_check":
            return await self._perf_check(input_data, tier)
        if stage_name == "perf_check_deep":
            return await self._perf_check_deep(input_data, tier)
        if stage_name == "health_monitor":
            return await self._health_monitor(input_data, tier)
        if stage_name == "quality_check":
            return await self._quality_check(input_data, tier)
        if stage_name == "quality_check_deep":
            return await self._quality_check_deep(input_data, tier)
        if stage_name == "architect_review":
            return await self._architect_review(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")
