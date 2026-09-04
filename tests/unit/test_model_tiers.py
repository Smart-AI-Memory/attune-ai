"""Unit tests for attune.model_tiers (task 1, docs/specs/fable-premium-tier).

``attune.model_tiers`` re-exports the canonical ``attune_rag.model_tiers``
(the mirror + drift guard were retired 2026-09-04), so these tests
exercise the contract through the path attune-ai's call sites use; log
records come from the canonical module's logger.
"""

from __future__ import annotations

import logging

import pytest

from attune.model_tiers import (
    _DEFAULTS,
    _ENV,
    _KNOWN_MODELS,
    ModelRefusalError,
    fable_extras,
    resolve_model,
)

_TIERS = sorted(_DEFAULTS)


class TestResolveModel:
    @pytest.mark.parametrize("tier", _TIERS)
    def test_default_when_env_unset(self, monkeypatch, tier):
        monkeypatch.delenv(_ENV[tier], raising=False)
        assert resolve_model(tier) == _DEFAULTS[tier]

    def test_defaults_are_the_spec_tiers(self):
        assert _DEFAULTS == {
            "premium": "claude-fable-5-1",
            "capable": "claude-sonnet-5",
            "cheap": "claude-haiku-4-5",
        }

    @pytest.mark.parametrize("tier", _TIERS)
    def test_env_override_wins(self, monkeypatch, tier):
        monkeypatch.setenv(_ENV[tier], "claude-opus-4-8")
        assert resolve_model(tier) == "claude-opus-4-8"

    @pytest.mark.parametrize("value", ["", "   ", "\t"])
    def test_blank_override_falls_through(self, monkeypatch, value):
        monkeypatch.setenv(_ENV["premium"], value)
        assert resolve_model("premium") == _DEFAULTS["premium"]

    def test_override_is_stripped(self, monkeypatch):
        monkeypatch.setenv(_ENV["capable"], "  claude-sonnet-4-6  ")
        assert resolve_model("capable") == "claude-sonnet-4-6"

    def test_resolution_is_per_call_not_import_time(self, monkeypatch):
        assert resolve_model("cheap") == _DEFAULTS["cheap"]
        monkeypatch.setenv(_ENV["cheap"], "claude-haiku-4-5-20251001")
        assert resolve_model("cheap") == "claude-haiku-4-5-20251001"

    def test_unknown_override_warns_but_is_honored(self, monkeypatch, caplog):
        monkeypatch.setenv(_ENV["premium"], "claude-tpyo-9")
        with caplog.at_level(logging.WARNING, logger="attune_rag.model_tiers"):
            assert resolve_model("premium") == "claude-tpyo-9"
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "claude-tpyo-9" in warnings[0].getMessage()
        assert "tier=premium" in warnings[0].getMessage()
        assert _ENV["premium"] in warnings[0].getMessage()

    def test_known_override_does_not_warn(self, monkeypatch, caplog):
        monkeypatch.setenv(_ENV["premium"], "claude-sonnet-5")
        with caplog.at_level(logging.WARNING, logger="attune_rag.model_tiers"):
            assert resolve_model("premium") == "claude-sonnet-5"
        assert not [r for r in caplog.records if r.levelno == logging.WARNING]

    def test_unknown_tier_raises_value_error(self):
        with pytest.raises(ValueError, match="unknown model tier 'turbo'"):
            resolve_model("turbo")

    def test_defaults_are_known_models(self):
        assert set(_DEFAULTS.values()) <= _KNOWN_MODELS

    def test_both_fable_generations_are_known_overrides(self, monkeypatch, caplog):
        """Fable 5 is still served: pinning it must not trip the typo warning."""
        assert {"claude-fable-5-1", "claude-fable-5"} <= _KNOWN_MODELS
        monkeypatch.setenv(_ENV["premium"], "claude-fable-5")
        with caplog.at_level(logging.WARNING, logger="attune_rag.model_tiers"):
            assert resolve_model("premium") == "claude-fable-5"
        assert not [r for r in caplog.records if r.levelno == logging.WARNING]


class TestFableExtras:
    def test_fable_gets_betas_and_fallbacks(self):
        extras = fable_extras("claude-fable-5")
        assert extras == {
            "betas": ["server-side-fallback-2026-06-01"],
            # fallbacks rides in extra_body: no shipped SDK types it as a
            # named param yet (verified through 0.96).
            "extra_body": {"fallbacks": [{"model": "claude-opus-4-8"}]},
        }

    def test_prefix_gating_covers_future_fable_ids(self):
        assert fable_extras("claude-fable-5-20260601") != {}

    def test_fable_5_1_gets_the_same_extras(self):
        assert fable_extras("claude-fable-5-1") == fable_extras("claude-fable-5")

    @pytest.mark.parametrize(
        "model",
        ["claude-sonnet-5", "claude-haiku-4-5", "claude-opus-4-8", "gemini-2.5-pro"],
    )
    def test_non_fable_models_get_empty_dict(self, model):
        assert fable_extras(model) == {}

    def test_returns_fresh_objects_each_call(self):
        first = fable_extras("claude-fable-5")
        first["betas"].append("mutated")
        first["extra_body"]["fallbacks"][0]["model"] = "mutated"
        assert fable_extras("claude-fable-5") == {
            "betas": ["server-side-fallback-2026-06-01"],
            "extra_body": {"fallbacks": [{"model": "claude-opus-4-8"}]},
        }


class TestModelRefusalError:
    def test_carries_category_and_explanation(self):
        err = ModelRefusalError(
            "premium call refused",
            category="harmful_content",
            explanation="the request was declined",
        )
        assert str(err) == "premium call refused"
        assert err.category == "harmful_content"
        assert err.explanation == "the request was declined"

    def test_stop_details_fields_default_to_none(self):
        err = ModelRefusalError("refused")
        assert err.category is None
        assert err.explanation is None

    def test_is_a_runtime_error(self):
        with pytest.raises(RuntimeError):
            raise ModelRefusalError("refused")
