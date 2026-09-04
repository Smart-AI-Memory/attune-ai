"""Model tier resolution — lazy re-export of the canonical ``attune_rag.model_tiers``.

attune-rag owns the attune tier contract and has been a core dependency
of attune-ai since 2026-04-30, so this module re-exports it instead of
carrying a byte-for-byte mirror. The mirror and its drift guard
(``tests/unit/test_model_tiers_drift.py``) were retired 2026-09-04.

**Why the re-export is lazy.** ``attune.config`` imports this module,
and ``attune.config`` must import with optional deps missing (see
``tests/unit/config/test_config_init_fallbacks.py``) and without paying
for attune-rag's package init, which eagerly loads the pipeline, corpus,
and providers (yaml, jinja2, structlog, rich; ~350 modules). The
canonical module itself is stdlib-only, but importing it runs
``attune_rag/__init__``. So ``resolve_model`` and ``fable_extras`` are
thin wrappers that import on first call, and every other name resolves
through PEP 562 ``__getattr__`` — the heavy import happens at the first
*use*, never at ``import attune.config``. Consumers that import
``ModelRefusalError`` at module level (workflows, curator) already sit
on heavy paths; that is where the cost lands.

The ``attune.model_tiers`` import path and exported names are unchanged,
so the ~20 call sites are untouched. Change tier defaults in attune-rag
only. The ``attune-rag>=1.2.0`` floor in pyproject is the first release
whose defaults match what this package documents (premium =
``claude-fable-5-1``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # static types only — no runtime import of attune_rag here
    from attune_rag.model_tiers import (  # noqa: F401
        _DEFAULTS,
        _ENV,
        _FABLE_BETAS,
        _FABLE_FALLBACKS,
        _KNOWN_MODELS,
        ModelRefusalError,
    )

__all__ = ["ModelRefusalError", "fable_extras", "resolve_model"]

_LAZY_NAMES = frozenset(
    {
        "ModelRefusalError",
        "_DEFAULTS",
        "_ENV",
        "_KNOWN_MODELS",
        "_FABLE_BETAS",
        "_FABLE_FALLBACKS",
    }
)


def resolve_model(tier: str) -> str:
    """Resolve a tier name to a model ID (see ``attune_rag.model_tiers.resolve_model``)."""
    from attune_rag.model_tiers import resolve_model as _resolve_model  # noqa: PLC0415

    return _resolve_model(tier)


def fable_extras(model: str) -> dict[str, Any]:
    """Extra request kwargs for fable models (see ``attune_rag.model_tiers.fable_extras``)."""
    from attune_rag.model_tiers import fable_extras as _fable_extras  # noqa: PLC0415

    return _fable_extras(model)


def __getattr__(name: str) -> Any:
    if name in _LAZY_NAMES:
        from attune_rag import model_tiers as _canonical  # noqa: PLC0415

        return getattr(_canonical, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | _LAZY_NAMES)
