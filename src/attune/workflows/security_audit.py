"""Security Audit Workflow

OWASP-focused security scan with intelligent vulnerability assessment.
Integrates with team security decisions to filter known false positives.

Stages:
1. triage (CHEAP) - Quick scan for common vulnerability patterns
2. analyze (CAPABLE) - Deep analysis of flagged areas
3. assess (CAPABLE) - Risk scoring and severity classification
4. remediate (PREMIUM) - Generate remediation plan (conditional)

Architecture:
- SecurityFilterMixin  (security_audit_filters.py) - false-positive filtering
- TriageStageMixin     (security_audit_triage.py)   - triage stage
- AnalyzeStageMixin    (security_audit_stages.py)   - analyze stage
- AssessStageMixin     (security_audit_stages.py)   - assess stage
- RemediateStageMixin  (security_audit_stages.py)   - remediate stage
- SecurityAuditWorkflow (this file)                 - orchestration

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
from pathlib import Path
from typing import Any

from .base import BaseWorkflow, ModelTier
from .context import WorkflowContext
from .security_audit_filters import SecurityFilterMixin
from .security_audit_patterns import (
    DETECTION_PATTERNS,  # noqa: F401  # re-export
    FAKE_CREDENTIAL_PATTERNS,  # noqa: F401  # re-export
    SECURITY_EXAMPLE_PATHS,  # noqa: F401  # re-export
    SECURITY_PATTERNS,  # noqa: F401  # re-export
    SKIP_DIRECTORIES,  # noqa: F401  # re-export
    TEST_FILE_PATTERNS,  # noqa: F401  # re-export
    TEST_FIXTURE_PATTERNS,  # noqa: F401  # re-export
)
from .security_audit_report import (
    format_security_report,  # noqa: F401  # re-export
    main,  # noqa: F401  # re-export
)
from .security_audit_stages import (
    SECURITY_STEPS,  # noqa: F401  # re-export
    AnalyzeStageMixin,
    AssessStageMixin,
    RemediateStageMixin,
)
from .security_audit_triage import TriageStageMixin
from .services import ParsingService, PromptService
from .validation import InputSchema, StageContract

logger = logging.getLogger(__name__)


class SecurityAuditWorkflow(
    SecurityFilterMixin,
    TriageStageMixin,
    AnalyzeStageMixin,
    AssessStageMixin,
    RemediateStageMixin,
    BaseWorkflow,
):
    """OWASP-focused security audit with team decision integration.

    Scans code for security vulnerabilities while respecting
    team decisions about false positives and accepted risks.

    Supports composition via ``WorkflowContext`` -- use ``default_context()``
    to get a pre-configured context with prompt and parsing services.
    """

    name = "security-audit"
    description = "OWASP-focused security scan with vulnerability assessment"
    stages = ["triage", "analyze", "assess", "remediate"]
    tier_map = {
        "triage": ModelTier.CHEAP,
        "analyze": ModelTier.CAPABLE,
        "assess": ModelTier.CAPABLE,
        "remediate": ModelTier.PREMIUM,
    }
    input_schema = InputSchema(
        required_fields={"path": str},
    )
    stage_contracts = {
        "triage": StageContract(required_keys={"vulnerabilities"}),
        "assess": StageContract(required_keys={"risk_assessment"}),
    }

    def __init__(
        self,
        patterns_dir: str = "./patterns",
        skip_remediate_if_clean: bool = True,
        use_crew_for_assessment: bool = True,
        use_crew_for_remediation: bool = False,
        crew_config: dict | None = None,
        enable_auth_strategy: bool = True,
        **kwargs: Any,
    ):
        """Initialize security audit workflow.

        Args:
            patterns_dir: Directory containing security decisions
            skip_remediate_if_clean: Skip remediation if no
                high/critical findings
            use_crew_for_assessment: Use SecurityAuditCrew for
                vulnerability assessment (default: True)
            use_crew_for_remediation: Use SecurityAuditCrew for
                enhanced remediation (default: True)
            crew_config: Configuration dict for SecurityAuditCrew
            enable_auth_strategy: If True, use intelligent
                subscription vs API routing based on codebase
                size (default: True)
            **kwargs: Additional arguments passed to BaseWorkflow

        """
        super().__init__(**kwargs)
        self.patterns_dir = patterns_dir
        self.skip_remediate_if_clean = skip_remediate_if_clean
        self.use_crew_for_assessment = use_crew_for_assessment
        self.use_crew_for_remediation = use_crew_for_remediation
        self.crew_config = crew_config or {}
        self.enable_auth_strategy = enable_auth_strategy
        self._has_critical: bool = False
        self._team_decisions: dict[str, dict] = {}
        self._crew: Any = None
        self._crew_available = False
        self._auth_mode_used: str | None = None
        self._load_team_decisions()

    @classmethod
    def default_context(cls, xml_config: dict | None = None) -> WorkflowContext:
        """Create a WorkflowContext pre-configured for security auditing.

        Args:
            xml_config: Optional XML prompt configuration dict.
                Defaults to XML enabled -- benchmarks on Claude 4.x
                show +30% quality, +15% cost. Best ROI of all
                workflows.

        Returns:
            WorkflowContext with prompt and parsing services.

        """
        if xml_config is None:
            xml_config = {"enabled": True, "enforce_response_xml": True}
        return WorkflowContext(
            prompt=PromptService("security-audit", xml_config=xml_config),
            parsing=ParsingService(xml_config=xml_config),
        )

    def _load_team_decisions(self) -> None:
        """Load team security decisions for false positive filtering."""
        decisions_file = Path(self.patterns_dir) / "security" / "team_decisions.json"
        if decisions_file.exists():
            try:
                with open(decisions_file) as f:
                    data = json.load(f)
                    for decision in data.get("decisions", []):
                        key = decision.get("finding_hash", "")
                        self._team_decisions[key] = decision
            except (json.JSONDecodeError, OSError):
                pass

    async def _initialize_crew(self) -> None:
        """Initialize the SecurityAuditCrew."""
        if self._crew is not None:
            return

        try:
            from attune.agent_factory.crews.security_audit import (
                SecurityAuditCrew,
            )

            self._crew = SecurityAuditCrew()
            self._crew_available = True
            logger.info("SecurityAuditCrew initialized successfully")
        except ImportError as e:
            logger.warning("SecurityAuditCrew not available: %s", e)
            self._crew_available = False

    def should_skip_stage(self, stage_name: str, input_data: Any) -> tuple[bool, str | None]:
        """Skip remediation stage if no critical/high findings.

        Args:
            stage_name: Name of the stage to check
            input_data: Current workflow data

        Returns:
            Tuple of (should_skip, reason)

        """
        if stage_name == "remediate" and self.skip_remediate_if_clean:
            if not self._has_critical:
                return (
                    True,
                    "No high/critical findings requiring remediation",
                )
        return False, None
