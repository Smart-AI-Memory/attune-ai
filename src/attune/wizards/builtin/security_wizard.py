"""Security Audit Wizard.

Guided flow: scope -> scan -> generate fixes -> decompose -> preview.

Delegates LLM_CALL steps to ``SecurityAuditWorkflow`` for mature
multi-stage scanning (triage → analyze → assess → remediate) while
preserving the wizard-guided UX.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext
from attune.workflows.compat import ModelTier

if TYPE_CHECKING:
    from attune.workflows.base import BaseWorkflow

from ..base import BaseWizard, StepType, WizardConfig, WizardStep
from ..session import WizardSession

logger = logging.getLogger(__name__)


def _has_findings(session: WizardSession) -> bool:
    """Check if the scan step found actionable issues.

    Handles both workflow output format (``assessment.severity_breakdown``)
    and the legacy LLM output format (``findings`` list, severity counts).

    Args:
        session: Current wizard session.

    Returns:
        True if high or critical findings exist.

    """
    scan_result = session.step_results.get("scan", {})

    # Workflow output format: assessment with severity breakdown
    assessment = scan_result.get("assessment", {})
    if isinstance(assessment, dict):
        breakdown = assessment.get("severity_breakdown", {})
        if breakdown:
            critical = breakdown.get("critical", 0)
            high = breakdown.get("high", 0)
            if (critical + high) > 0:
                return True

    # Workflow output format: findings list from triage
    findings = scan_result.get("findings", [])
    if isinstance(findings, list) and findings:
        return any(
            f.get("severity") in ("critical", "high") for f in findings if isinstance(f, dict)
        )

    # Legacy LLM output format: severity counts
    n_critical = int(scan_result.get("critical_issues", 0))
    n_high = int(scan_result.get("high_issues", 0))
    return (n_critical + n_high) > 0


class SecurityWizard(BaseWizard):
    """Guided security audit wizard.

    Delegates scan and remediation steps to ``SecurityAuditWorkflow``
    for mature multi-stage analysis. Falls back to independent LLM
    calls if the workflow is unavailable.

    Steps:
        1. Define audit scope (QUESTION)
        2. Run security scan via SecurityAuditWorkflow (LLM_CALL)
        3. Generate fixes via SecurityAuditWorkflow (LLM_CALL, conditional)
        4. Decompose remediation tasks (TASK_DECOMPOSE)
        5. Preview findings and plan (PREVIEW)
    """

    config = WizardConfig(
        wizard_id="security",
        name="Security Audit Wizard",
        description="Guided security vulnerability scanning and remediation",
        domain="security",
        estimated_cost_range=(0.03, 0.50),
        estimated_duration_minutes=8,
    )

    steps = [
        WizardStep(
            id="gather_info",
            name="Define Scope",
            description="Choose what to audit",
            step_type=StepType.QUESTION,
            questions=[
                FormQuestion(
                    id="scope",
                    text="What should be audited?",
                    type=QuestionType.SINGLE_SELECT,
                    options=["Full project (src/)", "Specific directory", "Single file"],
                    default="Full project (src/)",
                ),
                FormQuestion(
                    id="target_path",
                    text="Target path (if not full project)?",
                    type=QuestionType.TEXT_INPUT,
                    default="src/",
                    help_text="e.g. src/attune/config.py or src/attune/workflows/",
                ),
                FormQuestion(
                    id="focus_areas",
                    text="Focus areas?",
                    type=QuestionType.SINGLE_SELECT,
                    options=[
                        "All categories (Recommended)",
                        "OWASP Top 10",
                        "Dependency vulnerabilities",
                        "Secrets and credentials",
                        "Authentication and authorization",
                    ],
                    default="All categories (Recommended)",
                ),
            ],
        ),
        WizardStep(
            id="scan",
            name="Security Scan",
            description="Analyze code for vulnerabilities",
            step_type=StepType.LLM_CALL,
            prompt_template="security-audit",
            tier="capable",
        ),
        WizardStep(
            id="generate_fixes",
            name="Generate Fixes",
            description="Create remediation suggestions for high/critical findings",
            step_type=StepType.LLM_CALL,
            prompt_template="bug-analysis",
            tier="capable",
            condition=_has_findings,
        ),
        WizardStep(
            id="decompose_remediation",
            name="Remediation Plan",
            description="Break fixes into tasks",
            step_type=StepType.TASK_DECOMPOSE,
            tier="capable",
        ),
        WizardStep(
            id="preview",
            name="Review Findings",
            description="Review security findings and remediation plan",
            step_type=StepType.PREVIEW,
        ),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize security wizard.

        Args:
            **kwargs: Forwarded to ``BaseWizard.__init__``.

        """
        super().__init__(**kwargs)
        self._security_workflow: BaseWorkflow | None = None
        self._workflow_state: dict[str, Any] = {}

    # -----------------------------------------------------------------
    # Workflow delegation
    # -----------------------------------------------------------------

    def _get_or_create_workflow(self) -> Any:
        """Lazily instantiate and cache SecurityAuditWorkflow.

        Returns:
            SecurityAuditWorkflow instance, or None if unavailable.

        """
        if self._security_workflow is not None:
            return self._security_workflow

        try:
            from attune.workflows.security_audit import SecurityAuditWorkflow

            # No constructor kwargs: the SDK-native SecurityAuditWorkflow
            # accepts only system_prompt_suffix. The legacy kwargs
            # (skip_remediate_if_clean, use_crew_*, enable_auth_strategy)
            # raised TypeError here, which the except below swallowed —
            # so the wizard silently ALWAYS used the LLM fallback.
            self._security_workflow = SecurityAuditWorkflow()
            return self._security_workflow
        except ImportError:
            logger.warning("SecurityAuditWorkflow not available, using LLM fallback")
            return None
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Workflow is optional enhancement, not required
            logger.exception("Failed to initialize SecurityAuditWorkflow")
            return None

    async def _run_llm_step(self, step: WizardStep) -> None:
        """Override to delegate LLM steps to SecurityAuditWorkflow.

        Falls back to the base LLM call if the workflow is unavailable
        or encounters an error.

        Args:
            step: A step with ``step_type == StepType.LLM_CALL``.

        """
        if step.id == "scan":
            try:
                await self._run_scan_via_workflow()
                return
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Graceful fallback to independent LLM call
                logger.exception("Workflow scan failed, falling back to LLM")

        if step.id == "generate_fixes":
            try:
                await self._run_fixes_via_workflow()
                return
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Graceful fallback to independent LLM call
                logger.exception("Workflow remediation failed, falling back to LLM")

        # Fall back to base LLM call
        await super()._run_llm_step(step)

    async def _run_scan_via_workflow(self) -> None:
        """Run triage + analyze + assess via SecurityAuditWorkflow.

        Builds input from wizard session, runs three workflow stages,
        and stores the combined result in the wizard session.

        Raises:
            RuntimeError: If the workflow is not available.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        workflow = self._get_or_create_workflow()
        if workflow is None:
            raise RuntimeError("SecurityAuditWorkflow not available")

        target = self._session.get("target_path", "src/")
        input_data: dict[str, Any] = {"path": target}

        # Stage 1: Triage — quick pattern scan
        triage_result, _, _ = await workflow.run_stage(
            "triage",
            ModelTier.CHEAP,
            input_data,
        )
        self._workflow_state["triage"] = triage_result

        # Stage 2: Analyze — deep analysis with team decision filtering
        analyze_input = {**input_data, **triage_result}
        analyze_result, _, _ = await workflow.run_stage(
            "analyze",
            ModelTier.CAPABLE,
            analyze_input,
        )
        self._workflow_state["analyze"] = analyze_result

        # Stage 3: Assess — risk scoring and severity classification
        assess_input = {**analyze_input, **analyze_result}
        assess_result, _, _ = await workflow.run_stage(
            "assess",
            ModelTier.CAPABLE,
            assess_input,
        )
        self._workflow_state["assess"] = assess_result

        # Combine results for session storage
        combined: dict[str, Any] = {
            "findings": triage_result.get("findings", []),
            "files_scanned": triage_result.get("files_scanned", 0),
            "analyzed_findings": analyze_result.get("analyzed_findings", []),
            "assessment": assess_result.get("assessment", {}),
            "formatted_report": assess_result.get("formatted_report", ""),
            "workflow_delegated": True,
        }

        self.process_step_result(
            self._required_step("scan"),
            combined,
        )
        self._session.complete_step("scan", result=combined)

    async def _run_fixes_via_workflow(self) -> None:
        """Run remediate stage via SecurityAuditWorkflow.

        Uses accumulated state from the scan stages.

        Raises:
            RuntimeError: If the workflow is not available.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        workflow = self._get_or_create_workflow()
        if workflow is None:
            raise RuntimeError("SecurityAuditWorkflow not available")

        # Build input from all prior workflow state
        input_data: dict[str, Any] = {
            "path": self._session.get("target_path", "src/"),
            **self._workflow_state.get("triage", {}),
            **self._workflow_state.get("analyze", {}),
            **self._workflow_state.get("assess", {}),
        }

        remediate_result, _, _ = await workflow.run_stage(
            "remediate",
            ModelTier.PREMIUM,
            input_data,
        )

        combined: dict[str, Any] = {
            "remediation_plan": remediate_result.get("remediation_plan", ""),
            "fixes": remediate_result.get("fixes", []),
            "workflow_delegated": True,
        }

        self.process_step_result(
            self._required_step("generate_fixes"),
            combined,
        )
        self._session.complete_step("generate_fixes", result=combined)

    # -----------------------------------------------------------------
    # Abstract method implementations
    # -----------------------------------------------------------------

    def build_prompt_context(self, step: WizardStep) -> PromptContext:
        """Build prompt context from session state.

        Used as fallback when workflow delegation is not available.

        Args:
            step: The current step.

        Returns:
            PromptContext for the LLM call.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")

        if step.id == "scan":
            target = self._session.get("target_path", "src/")
            focus = self._session.get("focus_areas", "All categories")

            return PromptContext.for_security_audit(
                code=f"Target: {target}",
                findings_summary="",
                risk_level="unknown",
                focus_areas=focus,
            )

        if step.id == "generate_fixes":
            scan_result = self._session.step_results.get("scan", {})
            findings_text = str(scan_result.get("findings", []))
            return PromptContext(
                role="security remediation specialist",
                goal="Generate concrete fixes for high and critical security findings",
                instructions=[
                    "For each high/critical finding, provide a specific code fix",
                    "Include before/after code examples",
                    "Prioritize by severity",
                ],
                constraints=[
                    "Fixes must not break existing functionality",
                    "Follow project coding standards",
                ],
                input_type="security_findings",
                input_payload=findings_text,
            )

        if step.id == "decompose_remediation":
            scan_result = self._session.step_results.get("scan", {})
            fixes = self._session.step_results.get("generate_fixes", {})
            combined = f"Findings: {scan_result}\nFixes: {fixes}"
            return PromptContext(
                role="security remediation planner",
                goal="Create remediation tasks ordered by severity",
                instructions=["One task per vulnerability or closely related group"],
                constraints=["Critical issues first"],
                input_type="remediation_data",
                input_payload=combined,
            )

        return PromptContext(role="assistant", goal="Perform security audit")

    def process_step_result(self, step: WizardStep, result: dict[str, Any]) -> None:
        """Store scan and fix results in session.

        Args:
            step: The step that produced this result.
            result: Parsed LLM response or workflow output.

        """
        if self._session is None:
            raise RuntimeError("Wizard session not initialized")
        if step.id == "scan":
            self._session.set("scan_findings", result)
        elif step.id == "generate_fixes":
            self._session.set("fixes", result)
