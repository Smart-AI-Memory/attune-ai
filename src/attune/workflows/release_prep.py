"""Release Preparation Workflow

Pre-release quality gate combining health checks, security scan,
and changelog generation.

Stages:
1. health (CHEAP) - Run health checks (lint, types, tests)
2. security (CAPABLE) - Security scan summary
3. changelog (CAPABLE) - Generate changelog from commits
4. approve (PREMIUM) - Final release readiness assessment (conditional)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

from .base import BaseWorkflow, ModelTier
from .context import WorkflowContext
from .release_prep_approve import RELEASE_PREP_STEPS, ReleasePrepApproveMixin
from .release_prep_report import format_release_prep_report, main
from .release_prep_stages import ReleasePrepStagesMixin
from .services import ParsingService, PromptService

__all__ = [
    "RELEASE_PREP_STEPS",
    "ReleasePreparationWorkflow",
    "format_release_prep_report",
    "main",
]


class ReleasePreparationWorkflow(
    ReleasePrepStagesMixin,
    ReleasePrepApproveMixin,
    BaseWorkflow,
):
    """Pre-release quality gate workflow.

    Combines multiple checks to determine if the codebase
    is ready for release.

    When use_security_crew=True, adds an additional crew_security stage
    that runs SecurityAuditCrew for comprehensive security analysis.

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.
    """

    name = "release-prep"
    description = "Pre-release quality gate with health, security, and changelog"

    # Default stages (can be modified in __init__)
    stages = ["health", "security", "changelog", "approve"]
    tier_map = {
        "health": ModelTier.CHEAP,
        "security": ModelTier.CAPABLE,
        "changelog": ModelTier.CAPABLE,
        "approve": ModelTier.PREMIUM,
    }

    def __init__(
        self,
        skip_approve_if_clean: bool = True,
        use_security_crew: bool = False,
        crew_config: dict | None = None,
        enable_auth_strategy: bool = True,
        **kwargs: Any,
    ):
        """Initialize release preparation workflow.

        Args:
            skip_approve_if_clean: Skip premium approval if all checks pass
            use_security_crew: Enable SecurityAuditCrew for comprehensive security audit
            crew_config: Configuration dict for SecurityAuditCrew
            enable_auth_strategy: Enable intelligent auth routing (default: True)
            **kwargs: Additional arguments passed to BaseWorkflow

        """
        super().__init__(**kwargs)
        self.skip_approve_if_clean = skip_approve_if_clean
        self.use_security_crew = use_security_crew
        self.crew_config = crew_config or {}
        self.enable_auth_strategy = enable_auth_strategy
        self._has_blockers: bool = False
        self._auth_mode_used: str | None = None

        # Dynamically configure stages based on security crew setting
        if use_security_crew:
            self.stages = ["health", "security", "crew_security", "changelog", "approve"]
            self.tier_map = {
                "health": ModelTier.CHEAP,
                "security": ModelTier.CAPABLE,
                "crew_security": ModelTier.PREMIUM,
                "changelog": ModelTier.CAPABLE,
                "approve": ModelTier.PREMIUM,
            }
        else:
            self.stages = ["health", "security", "changelog", "approve"]
            self.tier_map = {
                "health": ModelTier.CHEAP,
                "security": ModelTier.CAPABLE,
                "changelog": ModelTier.CAPABLE,
                "approve": ModelTier.PREMIUM,
            }

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for release preparation.

        Args:
            xml_config: Optional XML prompt configuration dict.

        Returns:
            WorkflowContext with prompt and parsing services.

        """
        return WorkflowContext(
            prompt=PromptService("release-prep", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Skip approval if all checks pass cleanly.

        Args:
            stage_name: Name of the stage to check
            input_data: Current workflow data

        Returns:
            Tuple of (should_skip, reason)

        """
        if stage_name == "approve" and self.skip_approve_if_clean:
            if not self._has_blockers:
                return True, "All checks passed - auto-approved"
        return False, None

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Route to specific stage implementation."""
        if stage_name == "health":
            return await self._health(input_data, tier)
        if stage_name == "security":
            return await self._security(input_data, tier)
        if stage_name == "crew_security":
            return await self._crew_security(input_data, tier)
        if stage_name == "changelog":
            return await self._changelog(input_data, tier)
        if stage_name == "approve":
            return await self._approve(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")


if __name__ == "__main__":
    main()
