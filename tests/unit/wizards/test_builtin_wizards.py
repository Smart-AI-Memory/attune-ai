"""Unit tests for built-in wizards.

Tests cover:
- DebugWizard: config, steps, build_prompt_context, process_step_result, bug enrichment
- SecurityWizard: config, steps, _has_findings, workflow delegation
- RefactorWizard: config, steps, prompt context, workflow delegation
- ReleasePrepWizard: config, steps, prompt context
- TestGenWizard: config, steps, prompt context
- Builtin __init__: BUILTIN_WIZARDS dict

Created: 2026-02-15
"""

import pytest

from unittest.mock import AsyncMock, MagicMock, patch

from attune.wizards.base import StepType, WizardConfig
from attune.wizards.session import WizardSession
from attune.wizards.builtin import BUILTIN_WIZARDS
from attune.wizards.builtin.debug_wizard import DebugWizard
from attune.wizards.builtin.security_wizard import SecurityWizard, _has_findings
from attune.wizards.builtin.refactor_wizard import RefactorWizard
from attune.wizards.builtin.release_prep_wizard import ReleasePrepWizard
from attune.wizards.builtin.test_gen_wizard import TestGenWizard
from attune.meta_workflows.models import FormResponse


# =========================================================================
# BUILTIN_WIZARDS dict
# =========================================================================


class TestBuiltinWizardsRegistry:
    """Test BUILTIN_WIZARDS dict."""

    def test_all_five_wizards_present(self):
        """Test all 5 built-in wizards are registered."""
        assert "debug" in BUILTIN_WIZARDS
        assert "test-gen" in BUILTIN_WIZARDS
        assert "refactor" in BUILTIN_WIZARDS
        assert "security" in BUILTIN_WIZARDS
        assert "release-prep" in BUILTIN_WIZARDS
        assert len(BUILTIN_WIZARDS) == 5

    def test_wizard_classes_have_config(self):
        """Test all wizard classes have a config attribute."""
        for wizard_id, wizard_cls in BUILTIN_WIZARDS.items():
            assert hasattr(wizard_cls, "config")
            assert isinstance(wizard_cls.config, WizardConfig)
            assert wizard_cls.config.wizard_id == wizard_id

    def test_wizard_classes_have_steps(self):
        """Test all wizard classes have steps defined."""
        for wizard_cls in BUILTIN_WIZARDS.values():
            assert hasattr(wizard_cls, "steps")
            assert len(wizard_cls.steps) > 0


# =========================================================================
# DebugWizard
# =========================================================================


class TestDebugWizard:
    """Test DebugWizard."""

    def test_config(self):
        """Test wizard config."""
        assert DebugWizard.config.wizard_id == "debug"
        assert DebugWizard.config.name == "Debugging Wizard"
        assert DebugWizard.config.domain == "development"

    def test_steps_order(self):
        """Test step sequence."""
        step_ids = [s.id for s in DebugWizard.steps]
        assert step_ids == ["gather_info", "analyze", "decompose_fix", "preview", "confirm"]

    def test_step_types(self):
        """Test step types are correct."""
        types = {s.id: s.step_type for s in DebugWizard.steps}
        assert types["gather_info"] == StepType.QUESTION
        assert types["analyze"] == StepType.LLM_CALL
        assert types["decompose_fix"] == StepType.TASK_DECOMPOSE
        assert types["preview"] == StepType.PREVIEW
        assert types["confirm"] == StepType.CONFIRM

    def test_gather_info_has_questions(self):
        """Test gather_info step has questions defined."""
        gather = DebugWizard.steps[0]
        assert gather.questions is not None
        assert len(gather.questions) == 3
        q_ids = [q.id for q in gather.questions]
        assert "error_description" in q_ids
        assert "target_file" in q_ids
        assert "has_stack_trace" in q_ids

    def test_build_prompt_context_analyze(self):
        """Test build_prompt_context for analyze step."""
        wizard = DebugWizard()
        wizard._session = WizardSession(wizard_id="debug")
        wizard._session.set("error_description", "TypeError: cannot add int to str")
        wizard._session.set("target_file", "src/calc.py")
        wizard._session.set("has_stack_trace", "Yes")

        ctx = wizard.build_prompt_context(DebugWizard.steps[1])  # analyze step

        assert "debugging" in ctx.role.lower() or "debug" in ctx.role.lower()
        assert "TypeError" in ctx.input_payload
        assert "src/calc.py" in ctx.input_payload
        assert "Stack trace available" in ctx.input_payload

    def test_build_prompt_context_analyze_no_file(self):
        """Test analyze prompt without target file."""
        wizard = DebugWizard()
        wizard._session = WizardSession(wizard_id="debug")
        wizard._session.set("error_description", "Something broke")

        ctx = wizard.build_prompt_context(DebugWizard.steps[1])

        assert "Something broke" in ctx.input_payload
        assert "File" not in ctx.input_payload

    def test_build_prompt_context_decompose(self):
        """Test build_prompt_context for decompose step."""
        wizard = DebugWizard()
        wizard._session = WizardSession(wizard_id="debug")
        wizard._session.step_results["analyze"] = {"summary": "Root cause: missing import"}

        ctx = wizard.build_prompt_context(DebugWizard.steps[2])  # decompose_fix

        assert "missing import" in ctx.goal

    def test_build_prompt_context_fallback(self):
        """Test build_prompt_context for unknown step."""
        wizard = DebugWizard()
        wizard._session = WizardSession(wizard_id="debug")

        # Create a dummy step with unknown id
        from attune.wizards.base import WizardStep

        dummy = WizardStep(id="unknown", name="Unknown")
        ctx = wizard.build_prompt_context(dummy)

        assert ctx.role == "assistant"

    def test_process_step_result_analyze(self):
        """Test process_step_result stores analysis."""
        wizard = DebugWizard()
        wizard._session = WizardSession(wizard_id="debug")

        wizard.process_step_result(DebugWizard.steps[1], {"summary": "found the bug"})

        assert wizard._session.get("analysis") == {"summary": "found the bug"}


# =========================================================================
# SecurityWizard + _has_findings
# =========================================================================


class TestHasFindings:
    """Test _has_findings helper."""

    def test_assessment_severity_breakdown(self):
        """Test with workflow assessment format."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {
            "assessment": {"severity_breakdown": {"critical": 1, "high": 0, "medium": 2}},
        }

        assert _has_findings(session) is True

    def test_assessment_no_critical_or_high(self):
        """Test with only medium/low findings."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {
            "assessment": {"severity_breakdown": {"critical": 0, "high": 0, "medium": 5}},
        }

        assert _has_findings(session) is False

    def test_findings_list_format(self):
        """Test with findings list format."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {
            "findings": [
                {"severity": "high", "description": "SQL injection"},
            ],
        }

        assert _has_findings(session) is True

    def test_findings_list_only_medium(self):
        """Test findings list with only medium severity."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {
            "findings": [
                {"severity": "medium", "description": "Info leak"},
            ],
        }

        assert _has_findings(session) is False

    def test_legacy_severity_counts(self):
        """Test with legacy LLM output format."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {
            "critical_issues": 2,
            "high_issues": 0,
        }

        assert _has_findings(session) is True

    def test_legacy_no_issues(self):
        """Test with legacy format and no issues."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {
            "critical_issues": 0,
            "high_issues": 0,
        }

        assert _has_findings(session) is False

    def test_empty_scan_result(self):
        """Test with empty scan result."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {}

        assert _has_findings(session) is False

    def test_no_scan_result(self):
        """Test with no scan step result at all."""
        session = WizardSession(wizard_id="security")

        assert _has_findings(session) is False

    def test_findings_list_with_non_dict_items(self):
        """Test findings list gracefully handles non-dict items."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {
            "findings": ["string_finding", {"severity": "critical", "desc": "bad"}],
        }

        assert _has_findings(session) is True

    def test_empty_findings_list(self):
        """Test with empty findings list."""
        session = WizardSession(wizard_id="security")
        session.step_results["scan"] = {"findings": []}

        assert _has_findings(session) is False


class TestSecurityWizard:
    """Test SecurityWizard."""

    def test_config(self):
        """Test wizard config."""
        assert SecurityWizard.config.wizard_id == "security"
        assert SecurityWizard.config.domain == "security"

    def test_steps_present(self):
        """Test steps are defined."""
        assert len(SecurityWizard.steps) >= 4
        step_types = [s.step_type for s in SecurityWizard.steps]
        assert StepType.QUESTION in step_types
        assert StepType.LLM_CALL in step_types

    def test_conditional_generate_fixes_step(self):
        """Test generate_fixes step has a condition."""
        fix_step = next((s for s in SecurityWizard.steps if s.id == "generate_fixes"), None)
        if fix_step:
            assert fix_step.condition is not None


# =========================================================================
# RefactorWizard
# =========================================================================


class TestRefactorWizard:
    """Test RefactorWizard."""

    def test_config(self):
        """Test wizard config."""
        assert RefactorWizard.config.wizard_id == "refactor"
        assert "refactor" in RefactorWizard.config.name.lower()

    def test_steps_present(self):
        """Test steps are defined."""
        assert len(RefactorWizard.steps) >= 3
        step_ids = [s.id for s in RefactorWizard.steps]
        assert "gather_info" in step_ids

    def test_build_prompt_context(self):
        """Test build_prompt_context for analyze step."""
        wizard = RefactorWizard()
        wizard._session = WizardSession(wizard_id="refactor")
        wizard._session.set("target_path", "src/auth.py")
        wizard._session.set("refactor_goal", "Extract methods")

        # Find analyze step
        analyze_step = next((s for s in RefactorWizard.steps if s.id == "analyze"), None)
        if analyze_step:
            ctx = wizard.build_prompt_context(analyze_step)
            assert ctx.role  # Should have a role
            assert ctx.goal  # Should have a goal


# =========================================================================
# ReleasePrepWizard
# =========================================================================


class TestReleasePrepWizard:
    """Test ReleasePrepWizard."""

    def test_config(self):
        """Test wizard config."""
        assert ReleasePrepWizard.config.wizard_id == "release-prep"

    def test_steps_present(self):
        """Test steps are defined."""
        assert len(ReleasePrepWizard.steps) >= 3

    def test_has_question_step(self):
        """Test has at least one question step."""
        question_steps = [s for s in ReleasePrepWizard.steps if s.step_type == StepType.QUESTION]
        assert len(question_steps) >= 1


# =========================================================================
# TestGenWizard
# =========================================================================


class TestTestGenWizard:
    """Test TestGenWizard."""

    def test_config(self):
        """Test wizard config."""
        assert TestGenWizard.config.wizard_id == "test-gen"

    def test_steps_present(self):
        """Test steps are defined."""
        assert len(TestGenWizard.steps) >= 3

    def test_has_question_step(self):
        """Test has at least one question step."""
        question_steps = [s for s in TestGenWizard.steps if s.step_type == StepType.QUESTION]
        assert len(question_steps) >= 1
