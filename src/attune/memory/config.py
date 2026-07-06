"""Redis Configuration for Attune AI (deprecated).

.. deprecated::
    Use ``attune_redis.config.RedisPluginConfig`` for new code.
    This module will be removed in v4.0.0.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

# Superseded by attune_redis.AMSMemoryBackend (the Redis Agent Memory Server integration). Retained — attune is aligning on Redis + Anthropic Claude, so there is no planned removal. Migration path: docs/migration/redis-plugin-migration.md

import os
from urllib.parse import urlparse

from .short_term import RedisShortTermMemory


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

    # Determine config source
    if os.getenv("REDIS_URL"):
        result["config_source"] = "REDIS_URL"
    elif os.getenv("REDIS_PUBLIC_URL"):
        result["config_source"] = "REDIS_PUBLIC_URL (Railway)"
    elif os.getenv("REDIS_PRIVATE_URL"):
        result["config_source"] = "REDIS_PRIVATE_URL"
    elif os.getenv("REDIS_HOST"):
        result["config_source"] = "REDIS_HOST"

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


# Convenience function for Railway deployments
def get_railway_redis() -> RedisShortTermMemory:
    """Get Redis configured for Railway deployment.

    Railway automatically sets REDIS_URL when you add a Redis service.
    For external access (like from VSCode extension), use REDIS_PUBLIC_URL.

    Returns:
        RedisShortTermMemory configured for Railway

    Raises:
        EnvironmentError: If no Redis URL is set

    """
    redis_url = (
        os.getenv("REDIS_URL") or os.getenv("REDIS_PUBLIC_URL") or os.getenv("REDIS_PRIVATE_URL")
    )

    if not redis_url:
        raise OSError(
            "REDIS_URL not found. Make sure Redis is added to your Railway project.\n"
            "Run: railway add --database redis\n"
            "For external access, use REDIS_PUBLIC_URL",
        )

    return get_redis_memory(url=redis_url)
