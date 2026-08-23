"""Tests for the spend-gate meter resolution (T2).

Auth modes are constructed directly (never reading real on-disk
auth state) so the tests are deterministic across environments.
"""

from __future__ import annotations

import pytest

from attune.gates.meter import (
    METER_API,
    METER_SUBSCRIPTION,
    Meter,
    resolve,
)
from attune.models.auth_strategy import AuthMode, AuthStrategy, SubscriptionTier


@pytest.fixture(autouse=True)
def _no_ambient_api_key(monkeypatch):
    """Meter resolution reads the RUNTIME key first (2026-08-23); these
    tests exercise the preference path, so a developer's ambient key must
    not leak in — keyless CI sets the var to "" and so do we."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")


# --- framing -------------------------------------------------------------


def test_api_framing_shows_dollar_band() -> None:
    framing = Meter(mode=METER_API).framing(2.5)
    assert "$2.50" in framing
    assert "Anthropic API spend" in framing


def test_subscription_framing_shows_headroom_never_dollars() -> None:
    framing = Meter(mode=METER_SUBSCRIPTION).framing(2.5)
    assert "subscription quota" in framing
    assert "usage window" in framing
    assert "$" not in framing


def test_subscription_framing_never_shows_zero_even_at_zero_estimate() -> None:
    # R5: a subscription user must never see a misleading $0.
    framing = Meter(mode=METER_SUBSCRIPTION).framing(0.0)
    assert "$0" not in framing
    assert "$" not in framing


def test_is_dollars_property() -> None:
    assert Meter(mode=METER_API).is_dollars is True
    assert Meter(mode=METER_SUBSCRIPTION).is_dollars is False


# --- resolution ----------------------------------------------------------


def test_resolve_explicit_api_mode() -> None:
    strategy = AuthStrategy(default_mode=AuthMode.API)
    assert resolve(strategy).mode == METER_API


def test_resolve_explicit_subscription_mode() -> None:
    strategy = AuthStrategy(default_mode=AuthMode.SUBSCRIPTION)
    assert resolve(strategy).mode == METER_SUBSCRIPTION


def test_resolve_auto_pro_user_is_api() -> None:
    # Pro on AUTO → API (pay-per-token is more economical for low usage).
    strategy = AuthStrategy(
        default_mode=AuthMode.AUTO,
        subscription_tier=SubscriptionTier.PRO,
    )
    assert resolve(strategy).mode == METER_API


def test_resolve_auto_api_only_user_is_api() -> None:
    strategy = AuthStrategy(
        default_mode=AuthMode.AUTO,
        subscription_tier=SubscriptionTier.API_ONLY,
    )
    assert resolve(strategy).mode == METER_API


def test_resolve_auto_max_user_unknown_size_is_subscription() -> None:
    # Max/Enterprise on AUTO with unknown size (module_lines=0) resolves
    # the way a small run would → subscription, keeping the user off a
    # misleading $0 (D3).
    strategy = AuthStrategy(
        default_mode=AuthMode.AUTO,
        subscription_tier=SubscriptionTier.MAX,
    )
    assert resolve(strategy).mode == METER_SUBSCRIPTION


def test_resolve_auto_max_user_large_module_is_api() -> None:
    # A large target overrides AUTO toward API (1M context window).
    strategy = AuthStrategy(
        default_mode=AuthMode.AUTO,
        subscription_tier=SubscriptionTier.MAX,
    )
    assert resolve(strategy, module_lines=5000).mode == METER_API


def test_resolve_defaults_to_loaded_strategy(monkeypatch) -> None:
    # When no strategy is passed, resolve loads one — patched here so
    # the test never touches real on-disk auth state.
    sentinel = AuthStrategy(default_mode=AuthMode.SUBSCRIPTION)
    monkeypatch.setattr(
        "attune.gates.meter.AuthStrategy.load",
        classmethod(lambda cls, path=None: sentinel),
    )
    assert resolve().mode == METER_SUBSCRIPTION


# --- runtime basis beats preference (2026-08-23) --------------------------


def test_api_key_in_env_forces_api_meter_over_subscription_preference(monkeypatch) -> None:
    """The gate said "subscription quota" while the run billed the key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")  # pragma: allowlist secret
    strategy = AuthStrategy(default_mode=AuthMode.SUBSCRIPTION)
    meter = resolve(strategy)
    assert meter.mode == METER_API
    assert "ANTHROPIC_API_KEY" in meter.basis
    framing = meter.framing(1.0)
    assert "Anthropic API spend" in framing
    assert "subscription quota" not in framing
    assert "[basis:" in framing


def test_empty_api_key_falls_back_to_preference(monkeypatch) -> None:
    """Keyless CI sets the var to "" — that is NOT a key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    strategy = AuthStrategy(default_mode=AuthMode.SUBSCRIPTION)
    meter = resolve(strategy)
    assert meter.mode == METER_SUBSCRIPTION
    assert "no API key in env" in meter.basis


def test_framing_states_its_basis(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    meter = resolve(AuthStrategy(default_mode=AuthMode.API))
    assert meter.framing(0.5).endswith("[basis: auth-strategy preference]")
