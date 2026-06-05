"""Tests for the spend-gate meter resolution (T2).

Auth modes are constructed directly (never reading real on-disk
auth state) so the tests are deterministic across environments.
"""

from __future__ import annotations

from attune.gates.meter import (
    METER_API,
    METER_SUBSCRIPTION,
    Meter,
    resolve,
)
from attune.models.auth_strategy import AuthMode, AuthStrategy, SubscriptionTier

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
