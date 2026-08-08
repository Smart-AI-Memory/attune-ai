"""Redis Configuration for Attune AI.

Canonical home of :func:`resolve_redis_connection` — THE single
resolver for Redis connection settings (redis-config-truth R1,
rct-1 chair ruling 2026-08-08). Every component that needs a Redis
connection derives it from here; direct ``REDIS_*`` env reads
elsewhere are being retired (rct-4 drift guard).

.. deprecated::
    Only the legacy dict helpers below (``get_redis_config`` and
    friends) are deprecated — use
    ``attune_redis.config.RedisPluginConfig`` for plugin-level
    config objects. The resolver above this note is CANONICAL, not
    deprecated.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import ParseResult, quote, unquote, urlparse

from .short_term import RedisShortTermMemory

_URL_VARS = ("REDIS_URL", "REDIS_PRIVATE_URL", "REDIS_PUBLIC_URL")
#: Public alias for consumers that gate on "did a URL var supply the
#: connection" via ``source_map["url"] in URL_VARS`` (rct-4).
URL_VARS = _URL_VARS
_DEFAULT_URL = "redis://127.0.0.1:6379/0"
_VALID_SCHEMES = ("redis", "rediss", "unix")


@dataclass(frozen=True)
class ResolvedRedisConnection:
    """Result of :func:`resolve_redis_connection`.

    Attributes:
        url: The connection URL, credentials included when known.
        redacted_url: Same URL with any password replaced by ``***``
            — safe for logs, doctor output, and transcripts.
        source_map: Which env var supplied each component
            (``url``, ``password``, ``user``) — ``"default"`` when
            nothing did.
        overrides: Human-readable records of set-but-overridden
            variables whose values DISAGREED with the winner
            (redis-config-truth R1 conflict rule: precedence always
            decides, disagreements are recorded, never raised).
    """

    url: str
    redacted_url: str
    source_map: dict[str, str] = field(default_factory=dict)
    overrides: tuple[str, ...] = ()

    @property
    def password(self) -> str | None:
        """The effective password, parsed from ``url`` (None when bare).

        UNQUOTED: userinfo in the URL is percent-encoded, and
        ``urlparse`` does not decode it. Direct clients passing
        ``password=`` need the original credential (redis-py's
        ``from_url`` unquotes on its own — this property must match).
        """
        raw = urlparse(self.url).password
        return unquote(raw) if raw is not None else None


def _parse_url_or_raise(url: str, var: str) -> ParseResult:
    """Parse a Redis URL, raising an actionable ValueError if malformed."""
    parsed = urlparse(url)
    if parsed.scheme not in _VALID_SCHEMES:
        raise ValueError(
            f"{var} is not a Redis URL (scheme {parsed.scheme!r}); "
            f"expected one of: {', '.join(s + '://' for s in _VALID_SCHEMES)}"
        )
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"{var} has a non-numeric port — fix the URL's host:port section") from exc
    if parsed.scheme != "unix":
        db = (parsed.path or "").lstrip("/")
        if db and not db.isdigit():
            raise ValueError(f"{var} has a non-numeric db path {db!r} — use /<int> (e.g. /0)")
    return parsed


def _bracket_ipv6(host: str) -> str:
    """Re-bracket an IPv6 literal (urlparse strips the brackets)."""
    return f"[{host}]" if ":" in host else host


def _rebuild_with_credentials(parsed: ParseResult, user: str | None, password: str) -> str:
    """Rebuild a URL embedding the given credentials (password quoted)."""
    userpart = quote(user, safe="") if user else ""
    cred = f"{userpart}:{quote(password, safe='')}@"
    path = parsed.path or ""
    query = f"?{parsed.query}" if parsed.query else ""
    if parsed.scheme == "unix":
        return f"unix://{cred}{path}{query}"
    host = _bracket_ipv6(parsed.hostname or "127.0.0.1")
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{cred}{host}{port}{path}{query}"


def _redact(url: str) -> str:
    """Replace any embedded password with *** for safe display."""
    parsed = urlparse(url)
    if not parsed.password:
        return url
    userpart = quote(parsed.username, safe="") if parsed.username else ""
    path = parsed.path or ""
    query = f"?{parsed.query}" if parsed.query else ""
    if parsed.scheme == "unix":
        return f"unix://{userpart}:***@{path}{query}"
    host = _bracket_ipv6(parsed.hostname or "")
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{userpart}:***@{host}{port}{path}{query}"


def resolve_redis_connection(
    env: Mapping[str, str] | None = None,
) -> ResolvedRedisConnection:
    """Resolve THE Redis connection spec from environment variables.

    Precedence (redis-config-truth R1):

    1. A URL variable already carrying credentials.
    2. A URL variable merged with ``REDIS_PASSWORD`` / ``REDIS_USER``.
    3. URL variables are considered in order ``REDIS_URL``,
       ``REDIS_PRIVATE_URL``, ``REDIS_PUBLIC_URL``.
    4. Component variables ``REDIS_HOST`` / ``REDIS_PORT`` /
       ``REDIS_DB`` / ``REDIS_PASSWORD`` / ``REDIS_USER``.
    5. Default ``redis://127.0.0.1:6379/0`` (still merging
       ``REDIS_PASSWORD`` when set — the requirepass-localhost case).

    Conflict rule: precedence always decides. A set-but-overridden
    variable whose value disagrees with the winner is recorded in
    ``overrides`` (surfaced by the doctor diagnostic and the
    loud-once degradation path), never raised. Only malformed
    values raise ``ValueError`` with an actionable message.

    Args:
        env: Environment mapping (defaults to ``os.environ``;
            injectable for tests).

    Returns:
        A :class:`ResolvedRedisConnection` with the URL, its
        redacted twin, the per-component source map, and any
        recorded overrides.

    Raises:
        ValueError: On an unparseable URL, invalid scheme, or
            non-numeric port/db — never on redundant settings.
    """
    env = os.environ if env is None else env
    password = env.get("REDIS_PASSWORD") or None
    user = env.get("REDIS_USER") or None

    chosen_var = _choose_url_var(env)
    if chosen_var:
        return _resolve_from_url_var(env, chosen_var, password, user)
    if env.get("REDIS_HOST"):
        return _resolve_from_components(env, password, user)
    return _resolve_default(password, user)


def _choose_url_var(env: Mapping[str, str]) -> str | None:
    """Pick the winning URL variable.

    A URL already carrying credentials outranks a passwordless one
    (R1 tier 1); otherwise the first set variable wins in
    ``_URL_VARS`` order.
    """
    set_vars = [v for v in _URL_VARS if env.get(v)]
    for var in set_vars:
        if urlparse(env[var]).password:
            return var
    return set_vars[0] if set_vars else None


def _resolve_from_url_var(
    env: Mapping[str, str],
    chosen_var: str,
    password: str | None,
    user: str | None,
) -> ResolvedRedisConnection:
    """Resolve from the winning URL variable (precedence tiers 1-3)."""
    chosen_url = env[chosen_var]
    parsed = _parse_url_or_raise(chosen_url, chosen_var)
    overrides = [
        f"{other} ignored: {chosen_var} takes precedence"
        for other in _URL_VARS
        if other != chosen_var and env.get(other) and env[other] != chosen_url
    ]
    source_map = {"url": chosen_var, "password": "none", "user": "none"}
    if parsed.password:
        source_map["password"] = chosen_var
        if parsed.username:
            source_map["user"] = chosen_var
        if password and password != parsed.password:
            overrides.append(
                f"REDIS_PASSWORD ignored: {chosen_var} already carries "
                "credentials (values differ)"
            )
        url = chosen_url
    elif password:
        merge_user = user or parsed.username or None
        url = _rebuild_with_credentials(parsed, merge_user, password)
        source_map["password"] = "REDIS_PASSWORD"
        if user:
            source_map["user"] = "REDIS_USER"
        elif parsed.username:
            source_map["user"] = chosen_var
    else:
        url = chosen_url
    return ResolvedRedisConnection(url, _redact(url), source_map, tuple(overrides))


def _resolve_from_components(
    env: Mapping[str, str],
    password: str | None,
    user: str | None,
) -> ResolvedRedisConnection:
    """Resolve from REDIS_HOST / REDIS_PORT / REDIS_DB (tier 4)."""
    host = env["REDIS_HOST"]
    port_raw = env.get("REDIS_PORT", "6379")
    db_raw = env.get("REDIS_DB", "0")
    if not port_raw.isdigit():
        raise ValueError(f"REDIS_PORT must be numeric, got {port_raw!r}")
    if not db_raw.isdigit():
        raise ValueError(f"REDIS_DB must be numeric, got {db_raw!r}")
    cred = ""
    source_map = {"url": "REDIS_HOST", "password": "none", "user": "none"}
    if password:
        userpart = quote(user, safe="") if user else ""
        cred = f"{userpart}:{quote(password, safe='')}@"
        source_map["password"] = "REDIS_PASSWORD"
        source_map["user"] = "REDIS_USER" if user else "none"
    url = f"redis://{cred}{host}:{port_raw}/{db_raw}"
    return ResolvedRedisConnection(url, _redact(url), source_map, ())


def _resolve_default(password: str | None, user: str | None) -> ResolvedRedisConnection:
    """Resolve the localhost default, merging REDIS_PASSWORD (tier 5)."""
    source_map = {"url": "default", "password": "none", "user": "none"}
    if password:
        parsed = _parse_url_or_raise(_DEFAULT_URL, "default")
        url = _rebuild_with_credentials(parsed, user, password)
        source_map["password"] = "REDIS_PASSWORD"
        source_map["user"] = "REDIS_USER" if user else "none"
    else:
        url = _DEFAULT_URL
    return ResolvedRedisConnection(url, _redact(url), source_map, ())


def parse_redis_url(url: str) -> dict:
    """Parse Redis URL into connection parameters.

    Args:
        url: Redis URL (redis://user:pass@host:port/db)  # pragma: allowlist secret

    Returns:
        Dict with host, port, password, db

    """
    parsed = urlparse(url)

    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 6379,
        "password": parsed.password,
        "db": int(parsed.path.lstrip("/") or 0) if parsed.path else 0,
    }


def get_redis_config() -> dict:
    """Get Redis configuration from environment variables (legacy dict API).

    Delegates to attune.redis_config.get_redis_config() and converts
    to dict format for backward compatibility.

    Returns:
        Dict with connection parameters or {"use_mock": True}

    """
    from attune.redis_config import get_redis_config as _canonical_get_redis_config

    config = _canonical_get_redis_config()

    if config.use_mock:
        return {"use_mock": True}

    return {
        "host": config.host,
        "port": config.port,
        "password": config.password,
        "db": config.db,
        "use_mock": False,
    }


def get_redis_memory(
    url: str | None = None,
    use_mock: bool | None = None,
) -> RedisShortTermMemory:
    """Create a RedisShortTermMemory instance with environment-based config.

    Args:
        url: Optional explicit Redis URL (overrides env vars)
        use_mock: Optional explicit mock mode (overrides env vars)

    Returns:
        Configured RedisShortTermMemory instance

    Examples:
        # Auto-configure from environment
        memory = get_redis_memory()

        # Explicit URL
        memory = get_redis_memory(url="redis://127.0.0.1:6379")

        # Force mock mode
        memory = get_redis_memory(use_mock=True)

    """
    # Explicit mock mode
    if use_mock is True:
        return RedisShortTermMemory(use_mock=True)

    # Explicit URL
    if url:
        config = parse_redis_url(url)
        return RedisShortTermMemory(
            host=config["host"],
            port=config["port"],
            password=config["password"],
            db=config["db"],
            use_mock=False,
        )

    # Environment-based config
    config = get_redis_config()

    if config.get("use_mock"):
        return RedisShortTermMemory(use_mock=True)

    return RedisShortTermMemory(
        host=config["host"],
        port=config["port"],
        password=config.get("password"),
        db=config.get("db", 0),
        use_mock=False,
    )


def check_redis_connection() -> dict:
    """Check Redis connection and return status.

    Returns:
        Dict with connection status and info

    Example:
        >>> status = check_redis_connection()
        >>> if status["connected"]:
        ...     print(f"Connected to {status['host']}:{status['port']}")

    """
    config = get_redis_config()

    result = {
        "config_source": "environment",
        "use_mock": config.get("use_mock", False),
        "host": config.get("host"),
        "port": config.get("port"),
        "has_password": bool(config.get("password")),
        "db": config.get("db", 0),
        "connected": False,
        "error": None,
    }

    # Determine config source from the resolver's source-map (rct-4:
    # no direct connection-env reads outside the resolver).
    url_source = resolve_redis_connection().source_map.get("url", "default")
    if url_source != "default":
        result["config_source"] = url_source

    if result["use_mock"]:
        result["connected"] = True
        result["config_source"] = "mock_mode"
        return result

    try:
        memory = get_redis_memory()
        result["connected"] = memory.ping()
        if result["connected"]:
            stats = memory.get_stats()
            result["memory_used"] = stats.get("used_memory")
            result["total_keys"] = stats.get("total_keys")
    except Exception as e:  # noqa: BLE001
        result["error"] = str(e)

    return result


# Convenience function for managed Redis deployments
def get_managed_redis() -> RedisShortTermMemory:
    """Get Redis configured from a managed-platform URL.

    Managed Redis platforms (Upstash/Vercel, Heroku, Railway, ...) set
    REDIS_URL automatically; some also set REDIS_PUBLIC_URL (external
    access) or REDIS_PRIVATE_URL.

    Returns:
        RedisShortTermMemory configured from the managed Redis URL

    Raises:
        EnvironmentError: If no Redis URL is set

    """
    resolved = resolve_redis_connection()
    if resolved.source_map.get("url") not in URL_VARS:
        raise OSError(
            "REDIS_URL not found. Set REDIS_URL (or REDIS_PUBLIC_URL / "
            "REDIS_PRIVATE_URL) to your managed Redis URL "
            "(Upstash/Vercel, Heroku, Railway, ...).",
        )

    return get_redis_memory(url=resolved.url)


def get_railway_redis() -> RedisShortTermMemory:
    """Deprecated alias for :func:`get_managed_redis`.

    .. deprecated::
        The mechanism is platform-neutral; use ``get_managed_redis()``.

    """
    import warnings

    warnings.warn(
        "get_railway_redis() is deprecated; use get_managed_redis() — "
        "the URL detection is platform-neutral, not Railway-specific.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_managed_redis()
