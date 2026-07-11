"""Tests for the workflow-run auth pre-flight (setup-friction F1/F4).

The pre-flight sits BEFORE the spend gate in ``cmd_workflow_run`` so a
machine with no auth evidence at all gets one actionable message
instead of (a) a spend warning about dollars it cannot spend and then
(b) an SDK traceback. Evidence = ``ANTHROPIC_API_KEY`` or
``CLAUDE_CODE_OAUTH_TOKEN`` in the environment, or a ``~/.claude``
directory (Claude Code has been run on this machine).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from attune.cli_commands import workflow_commands
from attune.cli_commands.workflow_commands import _auth_preflight


@pytest.fixture()
def no_auth_evidence(monkeypatch, tmp_path):
    """Simulate a truly fresh machine: no keys, no ~/.claude."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


class TestAuthPreflight:
    def test_blocks_when_no_evidence(self, no_auth_evidence):
        message = _auth_preflight()
        assert message is not None
        assert "No auth found" in message
        assert "attune auth setup" in message

    def test_empty_string_key_is_not_evidence(self, no_auth_evidence, monkeypatch):
        """CI sets ANTHROPIC_API_KEY to the empty string — that's keyless."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        assert _auth_preflight() is not None

    def test_api_key_passes(self, no_auth_evidence, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")  # pragma: allowlist secret
        assert _auth_preflight() is None

    def test_oauth_token_passes(self, no_auth_evidence, monkeypatch):
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "tok")  # pragma: allowlist secret
        assert _auth_preflight() is None

    def test_claude_dir_passes(self, no_auth_evidence, tmp_path):
        """A ~/.claude directory is evidence Claude Code has been run.

        Existence only — the directory contents are never read (macOS
        keeps credentials in the Keychain, not in a file).
        """
        (tmp_path / ".claude").mkdir()
        assert _auth_preflight() is None


class TestPreflightOrdering:
    """The pre-flight fires BEFORE the spend gate (F4: never warn a
    keyless machine about spend it cannot incur)."""

    def _args(self) -> types.SimpleNamespace:
        return types.SimpleNamespace(name="wf", input=None, path=None, target=None, json=False)

    def test_preflight_blocks_before_spend_gate(self, no_auth_evidence, monkeypatch, capsys):
        gate_evaluated = {"called": False}

        def _gate(*a, **k):
            gate_evaluated["called"] = True
            raise AssertionError("spend gate must not be reached")

        monkeypatch.setattr("attune.gates.spend_gate.evaluate_spend_gate", _gate)
        monkeypatch.setattr("attune.workflows.get_workflow", lambda name: object)

        rc = workflow_commands.cmd_workflow_run(self._args())

        assert rc == 3  # EXIT_CLI_ERROR
        assert gate_evaluated["called"] is False
        out = capsys.readouterr().out
        assert "No auth found" in out
        assert "$" not in out  # no spend framing on the no-auth path

    def test_no_llm_run_skips_preflight(self, no_auth_evidence, monkeypatch):
        """--no-llm makes no billable call; a fresh machine may run it."""
        ran = {"called": False}

        def _runner(*a, **k):
            ran["called"] = True
            return 0

        monkeypatch.setattr("attune.cli_commands._exit_codes.run_workflow_with_exit_code", _runner)
        monkeypatch.setattr("attune.workflows.get_workflow", lambda name: object)
        monkeypatch.setenv("ATTUNE_SPEND_GATE", "off")

        args = self._args()
        args.no_llm = True
        rc = workflow_commands.cmd_workflow_run(args)

        assert rc == 0
        assert ran["called"] is True
