"""Model tier resolution — re-export of the canonical ``attune_rag.model_tiers``.

attune-rag owns the attune tier contract and has been a core dependency
of attune-ai since 2026-04-30, so this module re-exports it instead of
carrying a byte-for-byte mirror. The mirror and its drift guard
(``tests/unit/test_model_tiers_drift.py``) were retired 2026-09-04: their
premise — "attune-ai does not depend on attune-rag; the plugin installs
standalone" — had been false since that promotion.

The ``attune.model_tiers`` import path stays so the ~20 call sites and
their docstrings remain valid. Change tier defaults in attune-rag only.
The ``attune-rag>=1.2.0`` floor in pyproject is the first release whose
defaults match what this package documents (premium =
``claude-fable-5-1``).
"""

from __future__ import annotations

from attune_rag.model_tiers import (  # noqa: F401
    _DEFAULTS,
    _ENV,
    _FABLE_BETAS,
    _FABLE_FALLBACKS,
    _KNOWN_MODELS,
    ModelRefusalError,
    fable_extras,
    resolve_model,
)

__all__ = ["ModelRefusalError", "fable_extras", "resolve_model"]
