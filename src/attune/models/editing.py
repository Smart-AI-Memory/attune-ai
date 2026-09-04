"""Editing-pass model resolution.

Writing tasks draft on the CAPABLE tier (Sonnet); editing/polish
passes run on a stronger editor model. This is deliberately NOT a
new tier: ``attune.model_tiers`` re-exports the contract owned
by attune-rag, while the editing pass is an attune-ai-local concern
— so it gets its own resolver (ruled 2026-07-29, recorded in
docs/specs/fable-premium-tier/decisions.md).
"""

from __future__ import annotations

import os

#: Env var overriding the editing-pass model.
EDITING_MODEL_ENV = "ATTUNE_MODEL_EDITING"

_DEFAULT_EDITING_MODEL = "claude-opus-5"


def resolve_editing_model() -> str:
    """Model ID for editing/polish passes (env override wins).

    A blank or whitespace-only override falls through to the
    default. Resolved per call (``os.getenv`` each time) so tests
    can flip it with ``monkeypatch.setenv``.
    """
    override = os.getenv(EDITING_MODEL_ENV, "").strip()
    return override or _DEFAULT_EDITING_MODEL
