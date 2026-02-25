"""Attune Redis Plugin.

Provides Redis Agent Memory Server integration for the
Attune AI framework. Implements the MemoryBackend protocol
via AMS working memory and adds semantic search via AMS
long-term memory.

Install: ``pip install attune-ai[redis]``

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from .config import RedisPluginConfig
from .memory import AMSMemoryBackend
from .plugin import RedisPlugin

__version__ = "0.1.0"
__all__ = ["AMSMemoryBackend", "RedisPlugin", "RedisPluginConfig"]
