"""Tests for the spend-gate core (T3).

Clock is pinned for all window logic, the envelope file lives under
``tmp_path``, and the auth strategy is injected (never reads real
on-disk auth state). Gate env vars are cleared per-test so the host
environment can't leak in.
"""

from __future__ import annotations

import pytest

from attune.gates.envelope import (
    DEFAULT_TTL_SECONDS,
    Envelope,
    load_envelope,
    save_envelope,
)
from attune.gates.spend_gate import (
    ACTION_BLOCK,
    ACTION_CONFIRM,
    ACTION_PROCEED,
    evaluate_spend_gate,
)
from attune.models.auth_strategy import AuthMode, AuthStrategy, SubscriptionTier


@pytest.fixture(autouse=True)
def _no_ambient_api_key(monkeypatch):
    """Meter resolution reads the RUNTIME key first (2026-08-23); these
    tests exercise the preference path, so a developer's ambient key must
    not leak in — keyless CI sets the var to "" and so do we."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")


# Pinned clock — deterministic window math.
NOW = 1_700_000_000.0

# Deterministic API-mode strategy → dollar framing without disk reads.
API_STRATEGY = AuthStrategy(default_mode=AuthMode.API)
SUB_STRATEGY = AuthStrategy(
    default_mode=AuthMode.SUBSCRIPTION,
    subscription_tier=SubscriptionTier.MAX,
)


@pytest.fixture(autouse=True)
def _clear_gate_env(monkeypatch):
    """Clear gate env vars so the host environment never leaks in."""
    for var in (
        "ATTUNE_SPEND_GATE",
        "ATTUNE_SPEND_GATE_AUTHORIZED",
        "ATTUNE_MAX_BUDGET_USD",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def env_path(tmp_path):
    return tmp_path / "spend_gate" / "envelope.json"


def _authorized_envelope(path, *, cap_usd, spent_usd, window_start=NOW):
    save_envelope(
        Envelope(
            window_start=window_start,
            authorized=True,
            cap_usd=cap_usd,
            spent_usd=spent_usd,
            meter="api",
        ),
        path,
    )


# --- core decisions ------------------------------------------------------


def test_fresh_window_confirms(env_path):
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_CONFIRM
    assert decision.estimate_usd == 10.0  # standard depth default


def test_authorized_within_envelope_proceeds(env_path):
    _authorized_envelope(env_path, cap_usd=100.0, spent_usd=5.0)
    decision = evaluate_spend_gate(
        "code-review",
        "standard",
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_PROCEED


def test_partial_spend_proceeds_silently(env_path):
    # Dogfood regression: cap == one run's band ($2 quick), one run
    # spent $0.16 → the next run must PROCEED, not re-prompt.
    _authorized_envelope(env_path, cap_usd=2.0, spent_usd=0.16)
    decision = evaluate_spend_gate(
        "simplify-code",
        "quick",
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_PROCEED


def test_exhausted_window_confirms_with_overage(env_path):
    # cap 10, cumulative spend 10.5 → window used up → re-gate.
    _authorized_envelope(env_path, cap_usd=10.0, spent_usd=10.5)
    decision = evaluate_spend_gate(
        "deep-review",
        "standard",
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_CONFIRM
    assert decision.breach_usd == pytest.approx(0.5)  # 10.5 - 10


def test_expired_window_regates(env_path):
    _authorized_envelope(env_path, cap_usd=100.0, spent_usd=5.0)
    later = NOW + DEFAULT_TTL_SECONDS + 1
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        now=later,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_CONFIRM


# --- off switch (R6) -----------------------------------------------------


def test_off_switch_spend_gate_env_proceeds(env_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_SPEND_GATE", "off")
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_PROCEED
    assert decision.reason == "spend gate disabled"


def test_off_switch_max_budget_zero_proceeds(env_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_MAX_BUDGET_USD", "0")
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_PROCEED


# --- non-interactive fail-safe (D10) -------------------------------------


def test_non_interactive_without_preauth_blocks(env_path):
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        interactive=False,
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_BLOCK
    assert "ATTUNE_SPEND_GATE_AUTHORIZED" in decision.reason


def test_non_interactive_with_preauth_proceeds(env_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_SPEND_GATE_AUTHORIZED", "1")
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        interactive=False,
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_PROCEED


def test_non_interactive_preauth_exhausted_blocks(env_path, monkeypatch):
    # Pre-auth lets a non-interactive run proceed, but an exhausted
    # window can't be re-confirmed without a TTY → block (fail-safe).
    monkeypatch.setenv("ATTUNE_SPEND_GATE_AUTHORIZED", "1")
    _authorized_envelope(env_path, cap_usd=10.0, spent_usd=10.5)
    decision = evaluate_spend_gate(
        "deep-review",
        "standard",
        interactive=False,
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.action == ACTION_BLOCK


# --- estimate band + meter framing (D7, D8) ------------------------------


@pytest.mark.parametrize(
    ("depth", "expected"),
    [("quick", 2.0), ("standard", 10.0), ("deep", 25.0)],
)
def test_estimate_band_matches_depth_default(env_path, depth, expected):
    decision = evaluate_spend_gate(
        "security-audit",
        depth,
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.estimate_usd == expected


def test_max_budget_override_sets_estimate(env_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_MAX_BUDGET_USD", "3.5")
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert decision.estimate_usd == 3.5


def test_api_meter_framing_shows_dollars(env_path):
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert "$10.00" in decision.framing


def test_subscription_meter_framing_never_shows_dollars(env_path):
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        now=NOW,
        strategy=SUB_STRATEGY,
        envelope_path=env_path,
    )
    assert "$" not in decision.framing
    assert decision.envelope.meter == "subscription"


def test_decision_carries_envelope_state(env_path):
    decision = evaluate_spend_gate(
        "security-audit",
        "standard",
        now=NOW,
        strategy=API_STRATEGY,
        envelope_path=env_path,
    )
    assert isinstance(decision.envelope, Envelope)
    # Fresh window persisted nothing yet — file absent until the surface
    # authorizes and saves.
    assert load_envelope(env_path) is None
