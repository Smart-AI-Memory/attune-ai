"""Tests for the editing-pass model resolver.

Ruled 2026-07-29 (fable-premium-tier decisions.md): initial writing
drafts on the CAPABLE tier (Sonnet); editing/polish passes run on
the editing model, default claude-opus-5. The editing model is NOT
a tier — ``attune.model_tiers`` is a byte-mirrored contract owned
by attune-rag and must not grow attune-ai-local keys.
"""

from __future__ import annotations

import pytest

from attune.models.editing import (
    EDITING_MODEL_ENV,
    resolve_editing_model,
)
from attune.models.registry import ADDITIONAL_MODELS


def test_default_is_opus_5(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(EDITING_MODEL_ENV, raising=False)
    assert resolve_editing_model() == "claude-opus-5"


def test_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(EDITING_MODEL_ENV, "claude-sonnet-5")
    assert resolve_editing_model() == "claude-sonnet-5"


def test_blank_override_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(EDITING_MODEL_ENV, "   ")
    assert resolve_editing_model() == "claude-opus-5"


def test_editing_default_is_priced(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default editing model must resolve in the pricing registry.

    Cost tracking would silently misprice polish calls otherwise.
    """
    monkeypatch.delenv(EDITING_MODEL_ENV, raising=False)
    model = resolve_editing_model()
    assert model in ADDITIONAL_MODELS
    info = ADDITIONAL_MODELS[model]
    assert info.input_cost_per_million == 5.00
    assert info.output_cost_per_million == 25.00
