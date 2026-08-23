"""Regression guards from the 2026-08-23 bug-predict dogfood triage.

Round table q-bug-predict-health-001 produced six hypotheses about
``security_agent.py``; the real ones are pinned here so they stay fixed.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from attune.agents.release import security_agent as sec_mod
from attune.agents.release.release_models import Tier
from attune.agents.release.security_agent import (
    _SEVERITY_COUNT_KEYS,
    SecurityAuditorAgent,
)

_RUN = "attune.agents.release.security_agent._run_command"


def _agent() -> SecurityAuditorAgent:
    return SecurityAuditorAgent(redis_client=None, state_store=None)


# --- (b) the -1 sentinel is not retryable: bandit runs ONCE ---------------


def test_missing_bandit_does_not_escalate_tiers():
    agent = _agent()
    with patch(_RUN, return_value=(-1, "", "Command not found: uv")) as run:
        result = agent.process(".")

    assert run.call_count == 1
    assert result.success is False
    assert result.escalated is False
    assert result.tier_used is Tier.CHEAP
    assert result.findings["critical_issues"] == -1


def test_unparseable_bandit_output_does_not_escalate_tiers():
    agent = _agent()
    with patch(_RUN, return_value=(0, "Working... 100%\n{}", "")) as run:
        result = agent.process(".")

    assert run.call_count == 1
    assert result.escalated is False
    assert result.findings["note"] == "Could not parse bandit output"


def test_real_findings_do_not_escalate_either():
    """A failing bandit count is final (deterministic tool, raise-only
    ratchet), so CAPABLE/PREMIUM retries cannot change the verdict."""
    agent = _agent()
    out = json.dumps({"results": [{"issue_severity": "HIGH"}]})
    with patch(_RUN, return_value=(1, out, "")) as run:
        result = agent.process(".")

    assert run.call_count == 1
    assert result.success is False
    assert result.escalated is False
    assert result.tier_used is Tier.CHEAP
    assert result.findings["critical_issues"] == 1


def test_exception_path_still_escalates():
    """An unknown error keeps the retry: a transient fault may clear."""
    agent = _agent()
    with patch(_RUN, side_effect=OSError("transient")) as run:
        result = agent.process(".")

    assert run.call_count == 3
    assert result.escalated is True
    assert result.tier_used is Tier.PREMIUM


# --- (a) a non-dict result element degrades to the sentinel ---------------


def test_non_dict_result_element_degrades_to_sentinel():
    """Malformed bandit output fails closed rather than undercounting."""
    agent = _agent()
    out = json.dumps({"results": ["not-a-dict", {"issue_severity": "HIGH"}]})
    with patch(_RUN, return_value=(1, out, "")):
        success, findings = agent._execute_tier(".", Tier.CHEAP)

    assert success is False
    assert findings["critical_issues"] == -1
    assert "error" in findings


# --- (e) every degrade dict carries every ratchet key ---------------------


def test_degrade_dicts_carry_every_severity_count_key():
    """The LLM ratchet indexes ``findings[key]`` directly; pin the shape."""
    agent = _agent()
    for findings in (
        agent._parse_bandit_output("", -1),
        agent._parse_bandit_output("not json", 1),
        agent._parse_bandit_output("[]", 0),
    ):
        for key in _SEVERITY_COUNT_KEYS:
            assert key in findings, key
        assert findings["critical_issues"] == -1
        assert findings["retryable"] is False


# --- (d) the exception path keeps the traceback ---------------------------


def test_execute_tier_exception_logs_with_traceback(caplog):
    agent = _agent()
    with (
        patch(_RUN, side_effect=OSError("cwd vanished")),
        caplog.at_level("ERROR", logger=sec_mod.__name__),
    ):
        success, findings = agent._execute_tier(".", Tier.CHEAP)

    assert success is False
    assert findings == {"error": "cwd vanished", "critical_issues": -1}
    record = next(r for r in caplog.records if "Security audit failed" in r.getMessage())
    assert record.exc_info is not None


# --- (f) bandit has no CRITICAL level; HIGH alone drives the gate ------


def test_high_alone_is_the_gate_count():
    """bandit's ranking is LOW/MEDIUM/HIGH — the CRITICAL bucket is 0 from
    the scanner (it exists for the LLM's separate count, see #2203)."""
    agent = _agent()
    out = json.dumps(
        {
            "results": [
                {"issue_severity": "HIGH"},
                {"issue_severity": "MEDIUM"},
                {"issue_severity": "LOW"},
                {"issue_severity": "UNDEFINED"},  # bandit's 4th level: ignored
            ]
        }
    )
    findings = agent._parse_bandit_output(out, 1)

    assert findings["critical_issues"] == 1
    assert findings["high_issues"] == 1
    assert findings["medium_issues"] == 1
    assert findings["low_issues"] == 1
    assert findings["total_findings"] == 3
    assert findings["score"] == 100.0 - 15 - 5 - 1


# --- cross-review on #2204: the LLM cannot steer escalation ---------------


def test_llm_reply_cannot_steer_tier_escalation():
    """``retryable`` is an escalation control signal owned by the parser;
    an LLM reply carrying ``retryable: true`` against a real finding must
    not buy CAPABLE/PREMIUM retries the parser has ruled out.
    """
    agent = _agent()
    agent.llm_client = object()
    out = json.dumps({"results": [{"issue_severity": "HIGH"}]})
    llm = json.dumps({"retryable": True, "notes": "x"})
    with (
        patch.object(sec_mod, "LLM_MODE", "real"),
        patch(_RUN, return_value=(1, out, "")) as run,
        patch.object(agent, "_call_llm", return_value=(llm, {})),
    ):
        result = agent.process(".")

    assert run.call_count == 1
    assert result.escalated is False
    assert result.findings["retryable"] is False
    assert result.findings["notes"] == "x"
