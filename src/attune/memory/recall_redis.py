"""Auth-aware Redis client factory for the recall/ops readers.

memory-security-hardening R3: the recall and ops-dashboard readers each
constructed ``redis.Redis.from_url(...)`` ad hoc with no authentication, so a
``requirepass`` set on the memory Redis (D4) would break them all. This one
factory injects the ``REDIS_PASSWORD`` secret so a single env var makes every
reader authenticate — without disturbing a URL that already embeds credentials
(``rediss://user:pass@host``). When no password is set the behaviour is
identical to the previous bare ``from_url``, so wiring this in is non-disruptive.

Kept deliberately thin: the readers want a raw ``redis.Redis`` (for ``FCALL`` /
``FT.SEARCH`` / ``scan_iter``), not the ``RedisShortTermMemory`` wrapper. Import
of ``redis`` is lazy and raises ``ImportError`` to the caller, preserving each
reader's own degrade-on-missing-package handling.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import os
from typing import Any

#: The canonical local default — loopback, matching the disposable-cache posture.
DEFAULT_RECALL_URL = "redis://127.0.0.1:6379/0"


def resolve_url(url: str | None = None) -> str:
    """Return the recall Redis URL: explicit arg, else ``REDIS_URL``, else default."""
    return url or os.environ.get("REDIS_URL") or DEFAULT_RECALL_URL


def connect_recall_redis(url: str | None = None, **kwargs: Any) -> Any:
    """Construct an auth-aware ``redis.Redis`` for a recall/ops reader.

    Injects ``REDIS_PASSWORD`` when it is set and the URL does not already carry
    credentials, so ``requirepass`` (R3/D4) works via one env var. ``decode_responses``
    defaults to True (the readers expect ``str``). Extra ``kwargs`` (e.g.
    ``socket_connect_timeout``) pass straight through to ``from_url``.

    Raises:
        ImportError: If the ``redis`` package is not installed — the caller
            handles its own degradation (return None / degraded result).
    """
    import redis  # noqa: PLC0415 — optional dependency, import at use

    resolved = resolve_url(url)
    password = os.environ.get("REDIS_PASSWORD")
    # A password already embedded in the URL (``@``) wins; only inject the env
    # secret into an otherwise-bare URL, and never override an explicit kwarg.
    if password and "@" not in resolved:
        kwargs.setdefault("password", password)
    kwargs.setdefault("decode_responses", True)
    return redis.Redis.from_url(resolved, **kwargs)
