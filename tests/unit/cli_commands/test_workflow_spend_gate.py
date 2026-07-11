"""Tests for the spend gate wired into ``cmd_workflow_run`` (T4).

The gate *core* is covered in ``tests/unit/gates/test_spend_gate.py``;
these tests cover the CLI surface: how ``cmd_workflow_run`` handles
each ``GateDecision`` action (block / confirm / proceed), the confirm
I/O, envelope authorization on yes, the post-run cost record (R4), and
that ``--no-llm`` never reaches the gate (R8).

The envelope file is redirected to ``tmp_path`` so no test touches the
real ``~/.attune`` store.
"""

from __future__ import annotations

import time
import types

import pytest

from attune.cli_commands import workflow_commands
from attune.gates.envelope import Envelope, load_envelope, save_envelope
from attune.gates.spend_gate import (
    ACTION_BLOCK,
    ACTION_CONFIRM,
    ACTION_PROCEED,
    GateDecision,
)


def _make_args(**kwargs) -> types.SimpleNamespace:
    base = {
        "name": "security-audit",
        "input": None,
        "path": None,
        "target": None,
        "json": False,
        "no_llm": False,
        "depth": None,
        "cheap": False,
        "verbose": False,
        "source": None,
    }
    base.update(kwargs)
    return types.SimpleNamespace(**base)


def _decision(action, *, envelope=None, breach=0.0) -> GateDecision:
    env = envelope or Envelope.new(time.time(), cap_usd=10.0)
    return GateDecision(
        action=action,
        estimate_usd=10.0,
        framing="≈ up to $10.00 for this run — counts against your Anthropic API spend.",
        envelope=env,
        reason="test",
        breach_usd=breach,
    )


@pytest.fixture(autouse=True)
def env_file(tmp_path, monkeypatch):
    """Redirect the envelope store to tmp_path for every test here."""
    path = tmp_path / "spend_gate" / "envelope.json"
    monkeypatch.setattr("attune.gates.envelope._default_envelope_path", lambda: path)
    return path


@pytest.fixture(autouse=True)
def auth_preflight_passes(monkeypatch):
    """These tests target the SPEND GATE, which sits behind the auth
    pre-flight (setup-friction F1/F4). Neutralize the pre-flight so the
    gate is reachable regardless of the runner's auth evidence (CI has
    no ``~/.claude`` and an empty ``ANTHROPIC_API_KEY``)."""
    monkeypatch.setattr(workflow_commands, "_auth_preflight", lambda: None)


@pytest.fixture
def fake_runner(monkeypatch):
    """Patch the workflow runner; capture whether it ran + its on_result."""
    captured = {"called": False, "on_result": "unset"}

    def _runner(*_args, **kwargs):
        captured["called"] = True
        captured["on_result"] = kwargs.get("on_result")
        return 0

    monkeypatch.setattr("attune.cli_commands._exit_codes.run_workflow_with_exit_code", _runner)
    # Avoid real workflow resolution (runner is stubbed anyway).
    monkeypatch.setattr("attune.workflows.get_workflow", lambda name: object)
    return captured


def _patch_decision(monkeypatch, decision):
    monkeypatch.setattr(
        "attune.gates.spend_gate.evaluate_spend_gate",
        lambda *a, **k: decision,
    )


# --- block ---------------------------------------------------------------


def test_block_does_not_run_and_exits_clean(monkeypatch, fake_runner, capsys):
    _patch_decision(monkeypatch, _decision(ACTION_BLOCK))
    rc = workflow_commands.cmd_workflow_run(_make_args())
    assert rc == 0
    assert fake_runner["called"] is False
    out = capsys.readouterr().out
    assert "ATTUNE_SPEND_GATE_AUTHORIZED" in out


# --- confirm -------------------------------------------------------------


def test_confirm_decline_does_not_run(monkeypatch, fake_runner, capsys):
    _patch_decision(monkeypatch, _decision(ACTION_CONFIRM))
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    rc = workflow_commands.cmd_workflow_run(_make_args())
    assert rc == 0
    assert fake_runner["called"] is False
    assert "no charge" in capsys.readouterr().out.lower()


def test_confirm_yes_runs_and_authorizes_envelope(monkeypatch, fake_runner, env_file):
    _patch_decision(monkeypatch, _decision(ACTION_CONFIRM))
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    rc = workflow_commands.cmd_workflow_run(_make_args())
    assert rc == 0
    assert fake_runner["called"] is True
    # Envelope persisted + authorized by the yes.
    persisted = load_envelope(env_file)
    assert persisted is not None
    assert persisted.authorized is True
    # Enforced (non-disabled) window → cost recorder wired in.
    assert fake_runner["on_result"] is not None


# --- proceed -------------------------------------------------------------


def test_proceed_runs_without_prompt(monkeypatch, fake_runner):
    _patch_decision(monkeypatch, _decision(ACTION_PROCEED))

    def _no_input(_prompt):  # pragma: no cover - must not be called
        raise AssertionError("proceed must not prompt")

    monkeypatch.setattr("builtins.input", _no_input)
    rc = workflow_commands.cmd_workflow_run(_make_args())
    assert rc == 0
    assert fake_runner["called"] is True
    assert fake_runner["on_result"] is not None


def test_off_switch_envelope_skips_cost_record(monkeypatch, fake_runner):
    # A disabled envelope (gate off) → proceed, but no cost recorder.
    disabled_env = Envelope.new(time.time(), cap_usd=0.0)
    _patch_decision(monkeypatch, _decision(ACTION_PROCEED, envelope=disabled_env))
    rc = workflow_commands.cmd_workflow_run(_make_args())
    assert rc == 0
    assert fake_runner["called"] is True
    assert fake_runner["on_result"] is None


# --- R8: --no-llm never reaches the gate ---------------------------------


def test_no_llm_skips_gate_entirely(monkeypatch, fake_runner):
    def _boom(*_a, **_k):  # pragma: no cover - must not be called
        raise AssertionError("--no-llm must not reach the spend gate")

    monkeypatch.setattr("attune.gates.spend_gate.evaluate_spend_gate", _boom)
    rc = workflow_commands.cmd_workflow_run(_make_args(no_llm=True))
    assert rc == 0
    assert fake_runner["called"] is True
    assert fake_runner["on_result"] is None


# --- R4: post-run cost record --------------------------------------------


def test_record_envelope_cost_adds_actual_cost(env_file):
    save_envelope(
        Envelope(
            window_start=time.time(), authorized=True, cap_usd=10.0, spent_usd=1.0, meter="api"
        ),
        env_file,
    )
    result = types.SimpleNamespace(cost_report=types.SimpleNamespace(total_cost=2.5))
    workflow_commands._record_envelope_cost(result)
    assert load_envelope(env_file).spent_usd == pytest.approx(3.5)


def test_record_envelope_cost_zero_is_noop(env_file):
    save_envelope(
        Envelope(
            window_start=time.time(),
            authorized=True,
            cap_usd=10.0,
            spent_usd=1.0,
            meter="subscription",
        ),
        env_file,
    )
    result = types.SimpleNamespace(cost_report=types.SimpleNamespace(total_cost=0.0))
    workflow_commands._record_envelope_cost(result)
    assert load_envelope(env_file).spent_usd == pytest.approx(1.0)


# --- confirm-prompt helper branches --------------------------------------


def test_confirm_spend_exhausted_branch_frames_overage(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    assert workflow_commands._confirm_spend(_decision(ACTION_CONFIRM, breach=3.25)) is True
    out = capsys.readouterr().out
    assert "used up" in out
    assert "over by $3.25" in out


def test_confirm_spend_eof_returns_false(monkeypatch):
    def _eof(_prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", _eof)
    assert workflow_commands._confirm_spend(_decision(ACTION_CONFIRM)) is False


def test_authorize_envelope_with_no_envelope_is_noop():
    # A decision carrying no envelope must not crash or persist anything.
    workflow_commands._authorize_envelope(types.SimpleNamespace(envelope=None))


def test_record_envelope_cost_no_live_envelope_is_noop(env_file):
    # cost > 0 but no envelope on disk (off-switch/proceed path never
    # wrote one) → no crash, nothing persisted.
    result = types.SimpleNamespace(cost_report=types.SimpleNamespace(total_cost=2.5))
    workflow_commands._record_envelope_cost(result)
    assert load_envelope(env_file) is None
