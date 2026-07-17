"""Attune Redis Plugin.

Provides Redis Agent Memory Server integration for the
Attune AI framework. Implements the MemoryBackend protocol
via AMS working memory and adds semantic search via AMS
long-term memory.

Bundled with attune-ai — ``pip install attune-ai`` includes this plugin
and its dependencies (redis, agent-memory-client are core deps).

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from .config import RedisPluginConfig
from .memory import AMSMemoryBackend

__version__ = "0.1.0"
__all__ = ["AMSMemoryBackend", "RedisPlugin", "RedisPluginConfig"]


def __getattr__(name: str):
    """Lazily expose RedisPlugin without forcing an ``attune`` import.

    ``RedisPlugin`` imports the attune plugin framework, which is not
    present in every consumer's environment (e.g. the agent-memory-server
    venv that imports ``attune_redis.vector_db_int8`` via
    ``MEMORY_VECTOR_DB_FACTORY``). Deferring the import keeps submodule
    imports free of the ``attune`` dependency while
    ``from attune_redis import RedisPlugin`` still works.
    """
    if name == "RedisPlugin":
        from .plugin import RedisPlugin

        return RedisPlugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
