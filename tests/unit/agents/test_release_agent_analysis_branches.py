"""Branch coverage for the release agents' analysis seams (#1569).

The three modules' uncovered regions were all the same shapes: the
LLM-enhancement branch (guarded by ``llm_client`` + ``LLM_MODE ==
"real"`` — stubbed here, no real provider), the ruff score ladder,
and the defensive paths (unparseable source files, analysis
exceptions). No subprocess runs: ``_run_command`` is patched at
each module seam.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.agents.release import documentation_agent as doc_mod
from attune.agents.release import quality_agent as q_mod
from attune.agents.release import security_agent as sec_mod
from attune.agents.release.release_models import Tier


def ruff_stats(n: int) -> str:
    """Ruff --statistics stdout reporting exactly ``n`` violations."""
    return f"{n} E501 Line too long"


class TestQualityScoreLadder:
    @pytest.mark.parametrize(
        ("violations", "expected"),
        [(0, 10.0), (5, 9.0), (20, 8.0), (50, 7.0), (150, 5.0), (400, 3.0)],
    )
    def test_score_tiers(self, violations, expected):
        agent = q_mod.CodeQualityAgent(redis_client=None)
        stdout = ruff_stats(violations) if violations else ""
        findings = agent._parse_ruff_output(stdout, returncode=0)
        assert findings["quality_score"] == expected
        assert findings["total_violations"] == violations


class TestQualityLlmEnhancement:
    def _agent(self, monkeypatch, llm_reply: str):
        agent = q_mod.CodeQualityAgent(redis_client=None)
        monkeypatch.setattr(q_mod, "_run_command", lambda *a, **k: (0, ruff_stats(5), ""))
        monkeypatch.setattr(q_mod, "LLM_MODE", "real")
        agent.llm_client = object()
        monkeypatch.setattr(agent, "_call_llm", lambda *a, **k: (llm_reply, {}))
        return agent

    def test_llm_quality_score_overrides_rule_based(self, monkeypatch):
        agent = self._agent(monkeypatch, '{"quality_score": 9.5}')
        success, findings = agent._execute_tier(".", Tier.CHEAP)
        assert findings["quality_score"] == 9.5
        assert findings["score"] == 9.5
        assert findings["mode"] == "llm"
        assert success is True  # 9.5 >= min_quality_score

    def test_empty_llm_reply_keeps_rule_based_score(self, monkeypatch):
        agent = self._agent(monkeypatch, "")
        _, findings = agent._execute_tier(".", Tier.CHEAP)
        assert findings["quality_score"] == 9.0  # 5 violations -> rule-based tier
        assert findings["mode"] == "llm"  # client present, mode reflects it

    def test_llm_reply_without_score_keeps_rule_based(self, monkeypatch):
        agent = self._agent(monkeypatch, '{"notes": "looks fine"}')
        _, findings = agent._execute_tier(".", Tier.CHEAP)
        assert findings["quality_score"] == 9.0


class TestSecurityLlmEnhancement:
    def test_llm_findings_merge_into_bandit_results(self, monkeypatch):
        agent = sec_mod.SecurityAuditorAgent(redis_client=None)
        monkeypatch.setattr(sec_mod, "_run_command", lambda *a, **k: (0, '{"results": []}', ""))
        monkeypatch.setattr(sec_mod, "LLM_MODE", "real")
        agent.llm_client = object()
        monkeypatch.setattr(
            agent,
            "_call_llm",
            lambda *a, **k: ('{"critical_issues": 2, "confidence": 0.8, "notes": "x"}', {}),
        )
        _, findings = agent._execute_tier(".", Tier.CHEAP)
        # Non-gate fields merge; a stricter LLM count ratchets the bandit
        # value upward (fail-closed) — it can never lower it. confidence
        # and score are parser-owned: score tracks the ratcheted count.
        assert findings["notes"] == "x"
        assert findings["confidence"] == 0.9
        assert findings["critical_issues"] == 2
        assert findings["score"] == 40.0
        assert findings["mode"] == "llm"
        assert findings["tier"] == "cheap"

    def test_empty_llm_reply_keeps_bandit_findings(self, monkeypatch):
        agent = sec_mod.SecurityAuditorAgent(redis_client=None)
        monkeypatch.setattr(sec_mod, "_run_command", lambda *a, **k: (0, '{"results": []}', ""))
        monkeypatch.setattr(sec_mod, "LLM_MODE", "real")
        agent.llm_client = object()
        monkeypatch.setattr(agent, "_call_llm", lambda *a, **k: ("", {}))
        _, findings = agent._execute_tier(".", Tier.CHEAP)
        assert findings["critical_issues"] == 0
        assert findings["mode"] == "llm"


class TestDocumentationDefensivePaths:
    def test_unparseable_file_skipped_not_fatal(self, tmp_path):
        (tmp_path / "good.py").write_text('def documented():\n    """Doc."""\n')
        (tmp_path / "broken.py").write_text("def broken(:\n")
        agent = doc_mod.DocumentationAgent(redis_client=None)
        success, findings = agent._execute_tier(str(tmp_path), Tier.CHEAP)
        # the broken file is skipped; the good one fully documented
        assert findings["total_functions"] == 1
        assert findings["coverage_percent"] == 100.0
        assert success is True

    def test_analysis_exception_returns_error_findings(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("fs exploded")

        monkeypatch.setattr(doc_mod, "Path", boom)
        agent = doc_mod.DocumentationAgent(redis_client=None)
        success, findings = agent._execute_tier(".", Tier.CHEAP)
        assert success is False
        assert findings["error"] == "fs exploded"
        assert findings["coverage_percent"] == 0.0


def test_llm_ratchet_never_lifts_the_did_not_run_sentinel(monkeypatch):
    """bug-predict dogfood 2026-08-23: bandit output unreadable -> -1; the LLM
    says 0; 0 > -1 lifted the sentinel and the gate passed blind again."""
    agent = sec_mod.SecurityAuditorAgent(redis_client=None)
    monkeypatch.setattr(sec_mod, "_run_command", lambda *a, **k: (0, "Working... 100%\n{}", ""))
    monkeypatch.setattr(sec_mod, "LLM_MODE", "real")
    agent.llm_client = object()
    monkeypatch.setattr(
        agent,
        "_call_llm",
        lambda *a, **k: ('{"critical_issues": 0, "high_issues": 0, "score": 95}', {}),
    )
    success, findings = agent._execute_tier(".", Tier.CHEAP)
    assert success is False
    assert findings["critical_issues"] == -1
    assert findings["note"] == "Could not parse bandit output"


def test_llm_ratchet_still_raises_a_real_count(monkeypatch):
    agent = sec_mod.SecurityAuditorAgent(redis_client=None)
    monkeypatch.setattr(sec_mod, "_run_command", lambda *a, **k: (0, '{"results": []}', ""))
    monkeypatch.setattr(sec_mod, "LLM_MODE", "real")
    agent.llm_client = object()
    monkeypatch.setattr(agent, "_call_llm", lambda *a, **k: ('{"critical_issues": 2}', {}))
    success, findings = agent._execute_tier(".", Tier.CHEAP)
    assert success is False
    assert findings["critical_issues"] == 2
