"""Model tier resolution — MIRROR of ``attune_rag.model_tiers``.

attune-rag owns the canonical copy of the attune tier contract
(ADR-001 spirit), but attune-ai does not depend on attune-rag at all —
the plugin must install standalone — so the resolution logic and
constants are duplicated byte-for-byte instead of imported.
``tests/unit/test_model_tiers_drift.py`` asserts ``_DEFAULTS`` and
``_ENV`` stay identical to the canonical copy (guarded by
``pytest.importorskip``; CI installs ``attune-rag>=0.8`` in a dedicated
test step). Change attune-rag first, then re-mirror here.

Resolution is per-call (``os.getenv`` on every ``resolve_model``), not
import-time, so tests can flip tiers with ``monkeypatch.setenv`` and CI
pins take effect without re-import ordering concerns.

Stdlib only (logging, not structlog): keeps the module dependency-free
at import time and byte-comparable with the sibling mirrors. No
anthropic import, no network I/O.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "premium": "claude-fable-5",
    "capable": "claude-sonnet-5",
    "cheap": "claude-haiku-4-5",
}
_ENV = {
    "premium": "ATTUNE_MODEL_PREMIUM",
    "capable": "ATTUNE_MODEL_CAPABLE",
    "cheap": "ATTUNE_MODEL_CHEAP",
}
# Models we expect to see in overrides: the tier defaults, the fable
# server-side fallback target, and the pre-tier defaults still pinned in
# some environments. An override outside this set is honored but logged —
# it usually means a typo, not a deliberate pin.
_KNOWN_MODELS = frozenset(
    {
        "claude-fable-5",
        "claude-sonnet-5",
        "claude-haiku-4-5",
        "claude-opus-4-8",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    }
)

# The server-side fallback beta: when the fable pool is saturated or a
# safety classifier rejects the request, Anthropic retries the listed
# fallback models server-side before returning. Beta-namespace only.
_FABLE_BETAS = ["server-side-fallback-2026-06-01"]
_FABLE_FALLBACKS = [{"model": "claude-opus-4-8"}]


class ModelRefusalError(RuntimeError):
    """A premium-tier call ended with ``stop_reason == "refusal"``.

    Reaching this means the whole server-side fallback chain
    (fable → opus-4-8) refused the request. ``category`` and
    ``explanation`` come from the response's ``stop_details``; either
    may be ``None`` when the API omits them. Eval harnesses must record
    the item as errored — never silently skip it.
    """

    def __init__(
        self,
        message: str,
        *,
        category: str | None = None,
        explanation: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.explanation = explanation


def resolve_model(tier: str) -> str:
    """Resolve a tier name to a model ID (env override wins).

    A blank or whitespace-only override falls through to the default.
    An override not in ``_KNOWN_MODELS`` is honored with a warning.

    Raises:
        ValueError: if ``tier`` is not one of ``premium``/``capable``/``cheap``.
    """
    if tier not in _DEFAULTS:
        raise ValueError(f"unknown model tier {tier!r}; expected one of {sorted(_DEFAULTS)}")
    override = os.getenv(_ENV[tier], "").strip()
    if override:
        if override not in _KNOWN_MODELS:
            logger.warning(
                "unknown model override: tier=%s env_var=%s model=%s",
                tier,
                _ENV[tier],
                override,
            )
        return override
    return _DEFAULTS[tier]


def fable_extras(model: str) -> dict[str, Any]:
    """Extra request kwargs for premium-tier calls; ``{}`` for non-fable models.

    Non-empty means the caller must switch from ``client.messages.create``
    to ``client.beta.messages.create`` — the ``fallbacks`` param is
    beta-namespace only. ``fallbacks`` rides in ``extra_body`` because no
    shipped anthropic SDK types it as a named param yet (verified through
    0.96); ``extra_body`` merges into the request JSON on every SDK
    version. Fresh objects are returned each call so callers can mutate
    the kwargs safely.
    """
    if not model.startswith("claude-fable"):
        return {}
    return {
        "betas": list(_FABLE_BETAS),
        "extra_body": {"fallbacks": [dict(f) for f in _FABLE_FALLBACKS]},
    }
