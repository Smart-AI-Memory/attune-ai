"""Tests for DebugWizard's uninitialized-session guards.

The existing built-in wizard suite always seeds ``_session`` before calling
``build_prompt_context`` / ``process_step_result``, so the two RuntimeError
guards never execute. These tests pin the guard behavior and the no-op path
for non-analyze step results.
"""

from __future__ import annotations

import pytest

from attune.wizards.base import WizardSession
from attune.wizards.builtin.debug_wizard import DebugWizard

pytestmark = pytest.mark.unit


class TestSessionGuards:
    """Both public hooks refuse to run before start() initializes a session."""

    def test_build_prompt_context_without_session_raises(self):
        wizard = DebugWizard()
        assert wizard._session is None
        with pytest.raises(RuntimeError, match="session not initialized"):
            wizard.build_prompt_context(DebugWizard.steps[1])

    def test_process_step_result_without_session_raises(self):
        wizard = DebugWizard()
        with pytest.raises(RuntimeError, match="session not initialized"):
            wizard.process_step_result(DebugWizard.steps[1], {"summary": "x"})


class TestProcessStepResultNonAnalyze:
    """Results from steps other than `analyze` are deliberately not stored."""

    def test_non_analyze_step_result_is_a_noop(self):
        wizard = DebugWizard()
        wizard._session = WizardSession(wizard_id="debug")

        wizard.process_step_result(DebugWizard.steps[3], {"summary": "plan"})

        assert wizard._session.get("analysis") is None
