"""Configuration for the attune-redis plugin.

Loads settings from environment variables with sensible
defaults for local development.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class RedisPluginConfig:
    """Configuration for the attune-redis plugin.

    Attributes:
        ams_base_url: Base URL for the Redis Agent Memory
            Server (env: ``AMS_BASE_URL``).
        ams_namespace: Namespace for AMS operations.
        redis_url: Direct Redis URL for pub/sub signaling
            (env: ``REDIS_URL``). None disables signaling.
        default_session_id: Session ID when none is provided.
        default_user_id: User ID when none is provided.
    """

    ams_base_url: str = "http://localhost:8000"
    ams_namespace: str = "attune"
    redis_url: str | None = None
    default_session_id: str = "default"
    default_user_id: str = "system"

    @classmethod
    def from_env(cls) -> RedisPluginConfig:
        """Load configuration from environment variables.

        Reads:
            - ``AMS_BASE_URL`` — Agent Memory Server URL
            - ``REDIS_URL`` — Direct Redis for pub/sub
            - ``AMS_NAMESPACE`` — AMS namespace

        Returns:
            Configured RedisPluginConfig instance.
        """
        # rct-4: the connection URL comes from the canonical resolver
        # (credentials merged). It stays None unless a URL var supplied
        # it — ``redis_url is not None`` gates pub/sub availability.
        try:
            from attune.memory.config import URL_VARS, resolve_redis_connection

            resolved = resolve_redis_connection()
            redis_url = resolved.url if resolved.source_map.get("url") in URL_VARS else None
        except (ImportError, ValueError):
            # attune core absent or malformed config — preserve the
            # legacy None default rather than failing plugin config.
            redis_url = None

        return cls(
            ams_base_url=os.environ.get("AMS_BASE_URL", cls.ams_base_url),
            ams_namespace=os.environ.get("AMS_NAMESPACE", cls.ams_namespace),
            redis_url=redis_url,
        )


__all__ = ["RedisPluginConfig"]
