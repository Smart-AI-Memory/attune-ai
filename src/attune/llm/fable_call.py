"""Premium-tier (fable) call helpers — the one place fable quirks live.

``claude-fable-*`` requests differ from every other Anthropic call in
four ways (docs/specs/fable-premium-tier/design.md §4): they must go
through the **beta** messages namespace with the server-side-fallback
opt-in (``fallbacks`` rides in ``extra_body`` — no shipped SDK types it
as a named param yet), a ``stop_reason == "refusal"`` is a *verdict*
that must surface as :class:`~attune.model_tiers.ModelRefusalError`
(never a silent empty result), and a 400 usually means the org's data
retention is below fable's ≥30-day requirement — worth saying out loud
before anyone debugs the payload.

Call sites swap ``client.messages.create(...)`` for
``create_with_fable(client, model=model, **kwargs)`` (or the async
twin) and change nothing else: non-fable models take the exact
pre-tier code path, byte-identical payload, no refusal check.

Response-consuming note for call sites: fable responses can lead with
a thinking block that has no ``.text`` — read the first TEXT block,
not ``content[0]`` (hit live 2026-07-10, attune-author).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

from attune.model_tiers import ModelRefusalError, fable_extras

_RETENTION_HINT = (
    "claude-fable-5 requires >=30-day org data retention - check the "
    "org's retention configuration before debugging the payload."
)


def _refusal(model: str, response: Any) -> ModelRefusalError:
    details = getattr(response, "stop_details", None)

    def _field(key: str) -> str | None:
        if isinstance(details, dict):
            return details.get(key)
        return getattr(details, key, None)

    return ModelRefusalError(
        f"model {model} refused the request " "(the entire server-side fallback chain refused)",
        category=_field("category"),
        explanation=_field("explanation"),
    )


def _hinted_400(exc: Exception) -> Exception:
    """Same-type reconstruction with the retention hint appended.

    Anthropic error classes need response/body kwargs and can't be
    rebuilt from a message alone — fall back to RuntimeError; the
    original exception stays chained as ``__cause__`` either way.
    """
    message = f"{exc}\n{_RETENTION_HINT}"
    try:
        return type(exc)(message)
    except TypeError:
        return RuntimeError(message)


def create_with_fable(client: Any, *, model: str, **kwargs: Any) -> Any:
    """Send one Messages request, routing fable models via the beta API.

    Returns the raw SDK response. Raises ModelRefusalError when a fable
    call's whole fallback chain refused; re-raises a fable 400 with the
    retention hint appended (original chained as ``__cause__``).
    """
    extras = fable_extras(model)
    if not extras:
        return client.messages.create(model=model, **kwargs)
    try:
        response = client.beta.messages.create(model=model, **kwargs, **extras)
    except Exception as exc:
        if getattr(exc, "status_code", None) == 400:
            raise _hinted_400(exc) from exc
        raise
    if getattr(response, "stop_reason", None) == "refusal":
        raise _refusal(model, response)
    return response


async def acreate_with_fable(client: Any, *, model: str, **kwargs: Any) -> Any:
    """Async twin of :func:`create_with_fable` (AsyncAnthropic clients)."""
    extras = fable_extras(model)
    if not extras:
        return await client.messages.create(model=model, **kwargs)
    try:
        response = await client.beta.messages.create(model=model, **kwargs, **extras)
    except Exception as exc:
        if getattr(exc, "status_code", None) == 400:
            raise _hinted_400(exc) from exc
        raise
    if getattr(response, "stop_reason", None) == "refusal":
        raise _refusal(model, response)
    return response
