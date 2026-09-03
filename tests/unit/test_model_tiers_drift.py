"""Drift guard: attune.model_tiers must mirror attune_rag.model_tiers.

The tier module is duplicated by design — attune-ai does not depend on
attune-rag at all (the plugin installs standalone; see
docs/specs/fable-premium-tier design §1). Duplication is acceptable
only with an automated drift alarm — the lesson from the sibling-hooks
drift problem. This test IS that alarm: it fails the moment the two
copies' contract constants diverge.

Skips (not fails) when attune-rag is absent locally or the installed
version predates model_tiers; the tests workflow installs
``attune-rag>=0.8`` in a dedicated step, so drift cannot ship
unnoticed.
"""

from __future__ import annotations

import pytest

rag_tiers = pytest.importorskip(
    "attune_rag.model_tiers",
    reason="attune-rag absent or predates model_tiers; CI installs it and runs this",
)

from attune import model_tiers as ai_tiers  # noqa: E402


def test_defaults_match_canonical() -> None:
    assert ai_tiers._DEFAULTS == rag_tiers._DEFAULTS


def test_env_vars_match_canonical() -> None:
    assert ai_tiers._ENV == rag_tiers._ENV


def test_known_models_match_canonical() -> None:
    assert ai_tiers._KNOWN_MODELS == rag_tiers._KNOWN_MODELS


def test_fable_extras_match_canonical() -> None:
    for model in ("claude-fable-5-1", "claude-fable-5", "claude-sonnet-5", "claude-haiku-4-5"):
        assert ai_tiers.fable_extras(model) == rag_tiers.fable_extras(model)


def test_resolution_matches_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    for tier in ai_tiers._DEFAULTS:
        monkeypatch.delenv(ai_tiers._ENV[tier], raising=False)
        assert ai_tiers.resolve_model(tier) == rag_tiers.resolve_model(tier)
        monkeypatch.setenv(ai_tiers._ENV[tier], "claude-opus-4-8")
        assert ai_tiers.resolve_model(tier) == rag_tiers.resolve_model(tier)
