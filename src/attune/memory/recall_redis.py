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

from typing import Any
from urllib.parse import urlparse

#: The canonical local default — loopback, matching the disposable-cache posture.
DEFAULT_RECALL_URL = "redis://127.0.0.1:6379/0"


def resolve_url(url: str | None = None) -> str:
    """Return the recall Redis URL: explicit arg, else the canonical resolver.

    rct-4: the resolver's URL already carries merged credentials, so
    ``requirepass`` works without a separate password injection.
    """
    if url:
        return url
    from attune.memory.config import resolve_redis_connection

    return resolve_redis_connection().url


#: Seconds to wait for the TCP connect. A recall reader that cannot
#: reach Redis promptly must degrade, not stall the caller.
DEFAULT_CONNECT_TIMEOUT = 2.0

#: Seconds to wait for a reply once connected.
DEFAULT_SOCKET_TIMEOUT = 5.0


def connect_recall_redis(url: str | None = None, **kwargs: Any) -> Any:
    """Construct an auth-aware ``redis.Redis`` for a recall/ops reader.

    With no explicit ``url``, the canonical resolver supplies the URL —
    credentials already merged (R3/D4). An explicit bare ``url`` still
    gets the resolver's effective password injected, and never overrides
    an explicit kwarg. ``decode_responses`` defaults to True (the
    readers expect ``str``). Extra ``kwargs`` (e.g.
    ``socket_connect_timeout``) pass straight through to ``from_url``.

    Connect and read timeouts default to
    :data:`DEFAULT_CONNECT_TIMEOUT` / :data:`DEFAULT_SOCKET_TIMEOUT`
    rather than to whatever the installed redis-py happens to use.

    Raises:
        ImportError: If the ``redis`` package is not installed — the caller
            handles its own degradation (return None / degraded result).
    """
    import redis  # noqa: PLC0415 — optional dependency, import at use

    from attune.memory.config import resolve_redis_connection

    resolved = resolve_url(url)
    # A password already embedded in the URL wins; inject the resolver's
    # effective secret into an explicit URL that lacks one. Parsed, not
    # an "@" substring test — ``redis://user@host`` carries a username
    # but NO password and still needs the injection (codex D11 lane).
    if url and urlparse(resolved).password is None:
        password = resolve_redis_connection().password
        if password:
            kwargs.setdefault("password", password)
    kwargs.setdefault("decode_responses", True)
    # Bound the connect and the read HERE, not in each caller. Every
    # consumer of this factory is on a documented never-block path, and
    # without an explicit value the contract is decided by whichever
    # redis-py happens to be installed: on the project's declared pin
    # floor (redis 5.0.1) there is no default at all, and a blackholed
    # endpoint blocks ~75s (library-review H5). A caller needing tighter
    # bounds still passes its own — setdefault never overrides.
    kwargs.setdefault("socket_connect_timeout", DEFAULT_CONNECT_TIMEOUT)
    kwargs.setdefault("socket_timeout", DEFAULT_SOCKET_TIMEOUT)
    return redis.Redis.from_url(resolved, **kwargs)
