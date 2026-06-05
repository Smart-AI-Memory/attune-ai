"""Regression guard — lock the spend gate's core invariant (T5).

The invariant: **with the gate on and no authorized envelope, the
first billable call is never reached as ``proceed``.** It can only
become ``proceed`` via an explicit human confirm (which authorizes the
envelope), an explicit machine opt-in
(``ATTUNE_SPEND_GATE_AUTHORIZED=1``), or the off switch
(``ATTUNE_SPEND_GATE=off`` / ``ATTUNE_MAX_BUDGET_USD=0``).

If a future change lets an unauthorized first run silently proceed,
these tests fail — that is the whole point.
"""

from __future__ import annotations

import pytest

from attune.gates.spend_gate import (
    ACTION_BLOCK,
    ACTION_CONFIRM,
    ACTION_PROCEED,
    evaluate_spend_gate,
)
from attune.models.auth_strategy import AuthMode, AuthStrategy

NOW = 1_700_000_000.0
API_STRATEGY = AuthStrategy(default_mode=AuthMode.API)
DEPTHS = ["quick", "standard", "deep"]


@pytest.fixture(autouse=True)
def _clear_gate_env(monkeypatch):
    for var in (
        "ATTUNE_SPEND_GATE",
        "ATTUNE_SPEND_GATE_AUTHORIZED",
        "ATTUNE_MAX_BUDGET_USD",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def fresh_env(tmp_path):
    # No file written → load_or_new yields a fresh, unauthorized window.
    return tmp_path / "envelope.json"


@pytest.mark.parametrize("depth", DEPTHS)
def test_interactive_first_run_never_proceeds_silently(fresh_env, depth):
    decision = evaluate_spend_gate(
        "security-audit",
        depth,
        interactive=True,
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=fresh_env,
    )
    # The locked invariant: an unauthorized first run must confirm,
    # never proceed.
    assert decision.action == ACTION_CONFIRM
    assert decision.action != ACTION_PROCEED


@pytest.mark.parametrize("depth", DEPTHS)
def test_non_interactive_first_run_blocks_never_proceeds(fresh_env, depth):
    decision = evaluate_spend_gate(
        "security-audit",
        depth,
        interactive=False,
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=fresh_env,
    )
    assert decision.action == ACTION_BLOCK
    assert decision.action != ACTION_PROCEED


@pytest.mark.parametrize("interactive", [True, False])
def test_only_explicit_optin_unlocks_proceed_on_first_run(fresh_env, monkeypatch, interactive):
    # Without any opt-in: must NOT proceed (confirm or block).
    before = evaluate_spend_gate(
        "security-audit",
        "standard",
        interactive=interactive,
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=fresh_env,
    )
    assert before.action != ACTION_PROCEED

    # The explicit machine opt-in is the ONLY env that turns a first
    # run into proceed (short of the off switch).
    monkeypatch.setenv("ATTUNE_SPEND_GATE_AUTHORIZED", "1")
    after = evaluate_spend_gate(
        "security-audit",
        "standard",
        interactive=interactive,
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=fresh_env,
    )
    assert after.action == ACTION_PROCEED


@pytest.mark.parametrize(
    ("var", "value"),
    [("ATTUNE_SPEND_GATE", "off"), ("ATTUNE_MAX_BUDGET_USD", "0")],
)
def test_off_switch_is_the_documented_bypass(fresh_env, monkeypatch, var, value):
    # The off switch is an intentional, documented bypass — proceed
    # with no envelope enforcement.
    monkeypatch.setenv(var, value)
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        interactive=True,
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=fresh_env,
    )
    assert decision.action == ACTION_PROCEED
    assert decision.envelope.disabled is True
