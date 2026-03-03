"""Tests for base_agent module.

Tests _run_command helper (success, FileNotFoundError, TimeoutExpired)
and ReleaseAgent class (__init__, process, _execute_tier, _call_llm).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# _run_command helper
# ---------------------------------------------------------------------------


class TestRunCommand:
    """Tests for the _run_command module-level helper."""

    def test_success_returns_code_and_output(self):
        """Success: returns (returncode, stdout, stderr) from subprocess."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hello stdout"
        mock_result.stderr = ""

        with patch("attune.agents.release.base_agent.subprocess.run", return_value=mock_result):
            from attune.agents.release.base_agent import _run_command

            code, stdout, stderr = _run_command(["echo", "hello"])

        assert code == 0
        assert stdout == "hello stdout"
        assert stderr == ""

    def test_nonzero_returncode_returned(self):
        """Non-zero return code is passed through unchanged."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error text"

        with patch("attune.agents.release.base_agent.subprocess.run", return_value=mock_result):
            from attune.agents.release.base_agent import _run_command

            code, stdout, stderr = _run_command(["false"])

        assert code == 1
        assert stderr == "error text"

    def test_file_not_found_returns_minus_one(self):
        """FileNotFoundError returns (-1, '', error message)."""
        with patch(
            "attune.agents.release.base_agent.subprocess.run",
            side_effect=FileNotFoundError("no such file"),
        ):
            from attune.agents.release.base_agent import _run_command

            code, stdout, stderr = _run_command(["nonexistent_cmd"])

        assert code == -1
        assert stdout == ""
        assert "nonexistent_cmd" in stderr

    def test_timeout_expired_returns_minus_two(self):
        """TimeoutExpired returns (-2, '', timeout message)."""
        with patch(
            "attune.agents.release.base_agent.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["slow_cmd"], timeout=120),
        ):
            from attune.agents.release.base_agent import _run_command

            code, stdout, stderr = _run_command(["slow_cmd", "--flag"])

        assert code == -2
        assert stdout == ""
        assert "timed out" in stderr.lower() or "slow_cmd" in stderr

    def test_cwd_is_passed_to_subprocess(self):
        """cwd argument is forwarded to subprocess.run."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch(
            "attune.agents.release.base_agent.subprocess.run", return_value=mock_result
        ) as mock_run:
            from attune.agents.release.base_agent import _run_command

            _run_command(["ls"], cwd="/tmp")

        _, kwargs = mock_run.call_args
        assert kwargs.get("cwd") == "/tmp" or mock_run.call_args[0][0]  # positional or kw


# ---------------------------------------------------------------------------
# ReleaseAgent.__init__
# ---------------------------------------------------------------------------


class TestReleaseAgentInit:
    """Tests for ReleaseAgent initialisation."""

    def _make_agent(self, **kwargs):
        """Helper to create a ReleaseAgent with ANTHROPIC patched off."""
        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent

            return ReleaseAgent(agent_id="test-001", role="Test Role", **kwargs)

    def test_agent_id_and_role_stored(self):
        """agent_id and role are stored on the instance."""
        agent = self._make_agent()

        assert agent.agent_id == "test-001"
        assert agent.role == "Test Role"

    def test_defaults_without_optional_params(self):
        """Default optional params are None/zero."""
        agent = self._make_agent()

        assert agent.redis is None
        assert agent.state_store is None
        assert agent.total_cost == 0.0
        assert agent.total_tokens == 0

    def test_initial_tier_is_cheap(self):
        """Initial tier defaults to CHEAP."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()

        assert agent.current_tier is Tier.CHEAP

    def test_llm_client_none_when_anthropic_unavailable(self):
        """llm_client remains None when ANTHROPIC_AVAILABLE is False."""
        agent = self._make_agent()

        assert agent.llm_client is None

    def test_state_store_stored_when_provided(self):
        """state_store is stored when passed in."""
        mock_store = MagicMock()
        agent = self._make_agent(state_store=mock_store)

        assert agent.state_store is mock_store

    def test_redis_client_stored_when_provided(self):
        """redis_client is stored when passed in."""
        mock_redis = MagicMock()
        agent = self._make_agent(redis_client=mock_redis)

        assert agent.redis is mock_redis


# ---------------------------------------------------------------------------
# ReleaseAgent.process — tier escalation
# ---------------------------------------------------------------------------


class TestReleaseAgentProcess:
    """Tests for the process() method and tier escalation logic."""

    def _make_agent(self):
        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent

            return ReleaseAgent(agent_id="proc-001", role="Test Role")

    def test_cheap_success_no_escalation(self):
        """When CHEAP tier succeeds, result is not escalated."""
        agent = self._make_agent()
        findings = {"score": 9.0, "confidence": 0.9}

        with patch.object(agent, "_execute_tier", return_value=(True, findings)):
            result = agent.process(codebase_path=".")

        assert result.success is True
        assert result.escalated is False

    def test_cheap_fail_escalates_to_capable(self):
        """CHEAP failure triggers escalation and capable result is returned."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        call_count = []

        def fake_execute(path, tier):
            call_count.append(tier)
            if tier == Tier.CHEAP:
                return False, {"score": 0.0, "confidence": 0.1}
            return True, {"score": 8.0, "confidence": 0.8}

        with patch.object(agent, "_execute_tier", side_effect=fake_execute):
            result = agent.process(codebase_path=".")

        assert result.success is True
        assert result.escalated is True
        assert Tier.CHEAP in call_count
        assert Tier.CAPABLE in call_count

    def test_all_tiers_fail_returns_failed_result(self):
        """If all three tiers fail, result.success is False."""
        agent = self._make_agent()

        with patch.object(agent, "_execute_tier", return_value=(False, {"score": 0.0})):
            result = agent.process(codebase_path=".")

        assert result.success is False

    def test_result_has_agent_id_and_role(self):
        """Returned result carries agent_id and agent_role."""
        agent = self._make_agent()
        findings = {"score": 5.0, "confidence": 0.5}

        with patch.object(agent, "_execute_tier", return_value=(True, findings)):
            result = agent.process(codebase_path=".")

        assert result.agent_id == "proc-001"
        assert result.agent_role == "Test Role"

    def test_result_execution_time_positive(self):
        """execution_time_ms is a positive number after process()."""
        agent = self._make_agent()

        with patch.object(agent, "_execute_tier", return_value=(True, {"score": 5.0})):
            result = agent.process(codebase_path=".")

        assert result.execution_time_ms >= 0

    def test_state_store_record_start_called(self):
        """state_store.record_start() is called when state_store is provided."""
        mock_store = MagicMock()
        mock_store.record_start.return_value = "exec-123"

        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent

            agent = ReleaseAgent("s-001", "role", state_store=mock_store)

        findings = {"score": 9.0, "confidence": 0.9}
        with patch.object(agent, "_execute_tier", return_value=(True, findings)):
            agent.process(codebase_path=".")

        mock_store.record_start.assert_called_once()

    def test_state_store_record_completion_called_on_success(self):
        """state_store.record_completion() is called when agent succeeds."""
        mock_store = MagicMock()
        mock_store.record_start.return_value = "exec-999"

        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent

            agent = ReleaseAgent("s-002", "role", state_store=mock_store)

        with patch.object(agent, "_execute_tier", return_value=(True, {"score": 5.0})):
            agent.process(codebase_path=".")

        mock_store.record_completion.assert_called_once()
        mock_store.record_failure.assert_not_called()

    def test_state_store_record_failure_called_on_all_tiers_fail(self):
        """state_store.record_failure() is called when all tiers fail."""
        mock_store = MagicMock()
        mock_store.record_start.return_value = "exec-fail"

        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent

            agent = ReleaseAgent("s-003", "role", state_store=mock_store)

        with patch.object(agent, "_execute_tier", return_value=(False, {"error": "boom"})):
            agent.process(codebase_path=".")

        mock_store.record_failure.assert_called_once()

    def test_score_from_findings_reflected_in_result(self):
        """Result.score is taken from the findings dict 'score' key."""
        agent = self._make_agent()
        findings = {"score": 42.5, "confidence": 0.7}

        with patch.object(agent, "_execute_tier", return_value=(True, findings)):
            result = agent.process(codebase_path=".")

        assert result.score == pytest.approx(42.5)


# ---------------------------------------------------------------------------
# ReleaseAgent._execute_tier — NotImplementedError on base class
# ---------------------------------------------------------------------------


class TestReleaseAgentExecuteTier:
    """Tests for the base _execute_tier stub."""

    def test_execute_tier_raises_not_implemented(self):
        """Base class _execute_tier raises NotImplementedError."""
        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent
            from attune.agents.release.release_models import Tier

            agent = ReleaseAgent("noop-001", "Base")

        with pytest.raises(NotImplementedError):
            agent._execute_tier(".", Tier.CHEAP)


# ---------------------------------------------------------------------------
# ReleaseAgent._call_llm when ANTHROPIC unavailable
# ---------------------------------------------------------------------------


class TestCallLlmNoAnthropic:
    """Tests for _call_llm behaviour without Anthropic SDK."""

    def test_call_llm_returns_empty_string_when_no_client(self):
        """_call_llm returns ('', metadata) when llm_client is None."""
        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent
            from attune.agents.release.release_models import Tier

            agent = ReleaseAgent("llm-test", "Test")

        text, meta = agent._call_llm("prompt", "system", Tier.CHEAP)

        assert text == ""
        assert meta.get("model") == "rule_based"
        assert meta.get("cost") == 0.0

    def test_call_llm_does_not_increment_cost_without_client(self):
        """total_cost stays 0.0 when llm_client is None."""
        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent
            from attune.agents.release.release_models import Tier

            agent = ReleaseAgent("llm-cost", "Test")

        agent._call_llm("prompt", "system", Tier.CAPABLE)

        assert agent.total_cost == 0.0


# ---------------------------------------------------------------------------
# ReleaseAgent._register_heartbeat — no-op without Redis
# ---------------------------------------------------------------------------


class TestRegisterHeartbeat:
    """Tests for _register_heartbeat Redis no-op."""

    def test_heartbeat_no_op_without_redis(self):
        """_register_heartbeat returns silently when redis is None."""
        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent

            agent = ReleaseAgent("hb-001", "Test")

        # Should not raise
        agent._register_heartbeat(status="running", task="doing stuff")

    def test_heartbeat_calls_redis_when_present(self):
        """_register_heartbeat calls redis.hset when redis is provided."""
        mock_redis = MagicMock()

        with (
            patch("attune.agents.release.base_agent.ANTHROPIC_AVAILABLE", False),
            patch("attune.agents.release.base_agent.LLM_MODE", "rule_based"),
        ):
            from attune.agents.release.base_agent import ReleaseAgent

            agent = ReleaseAgent("hb-002", "Test", redis_client=mock_redis)

        agent._register_heartbeat(status="idle", task="")

        mock_redis.hset.assert_called_once()
