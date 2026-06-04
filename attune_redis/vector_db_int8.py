"""int8-quantized vector backend for the Redis Agent Memory Server.

Plugs into agent-memory-server via its ``MEMORY_VECTOR_DB_FACTORY``
extension seam (no fork of agent-memory-server required)::

    MEMORY_VECTOR_DB_FACTORY=attune_redis.vector_db_int8.create_int8_memory_db

Stores long-term-memory embeddings as int8 instead of float32,
cutting index memory ~75% and speeding vector search ~30% with no
measurable recall loss on our corpus (Phase-0 benchmark: int8 vs
float32 P@1 delta 0.0, recall@5 delta 0.0 — see
docs/specs/ams-int8-quantization/).

Design — index proxy, not method override
-----------------------------------------
Rather than subclass ``RedisVLMemoryVectorDatabase`` and duplicate
its ~200 lines of add/search logic (high drift risk across AMS
versions), this wraps the RedisVL ``AsyncSearchIndex`` in a thin
proxy that re-encodes vectors to int8 at the index boundary:

- **write** (``load``): AMS hands the index float32 vector bytes;
  the proxy decodes and re-encodes them as int8.
- **query** (``query``): the proxy quantizes the query vector and
  flips the ``VectorQuery``/``RangeQuery`` dtype to int8 before
  execution.
- **server-side recency** (``aggregate``): not supported on int8;
  the proxy raises so AMS falls back to its standard query path
  (which the proxy handles) plus client-side recency reranking.

Quantization is per-vector max-abs scaling to ``[-127, 127]``.
nomic-embed-text vectors are not unit-normalized, so a per-vector
scale uses the full int8 range; COSINE distance is invariant to
positive per-vector scaling, so this is safe.

Requires a **Redis 8 Query Engine** (``TYPE INT8`` vector fields).
The proxy fails loudly if the server rejects int8 rather than
silently falling back to float32.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

#: Field name AMS uses for the embedding vector in its RedisVL schema.
_VECTOR_FIELD = "vector"


def quantize_int8(vec: Any) -> list[int]:
    """Per-vector max-abs quantize a float embedding to int8 range.

    Args:
        vec: Sequence of floats (or anything ``np.asarray`` accepts).

    Returns:
        List of ints in ``[-127, 127]``. COSINE is invariant to the
        positive per-vector scale, so query and document vectors may
        be scaled independently.
    """
    a = np.asarray(vec, dtype=np.float32)
    peak = float(np.max(np.abs(a))) or 1.0
    q = np.clip(np.round(a * (127.0 / peak)), -127, 127)
    return q.astype(np.int8).tolist()


class Int8VectorIndexProxy:
    """Wrap a RedisVL ``AsyncSearchIndex`` to store/query int8 vectors.

    Delegates everything to the wrapped index except the three
    vector-touching paths (``load`` / ``query`` / ``aggregate``).
    """

    def __init__(self, index: Any) -> None:
        self._index = index

    def __getattr__(self, name: str) -> Any:
        # Everything not overridden below (exists, create's siblings,
        # name, schema, etc.) delegates to the real index.
        return getattr(self._index, name)

    async def create(self, *args: Any, **kwargs: Any) -> Any:
        """Create the index; translate int8-unsupported into a clear error."""
        try:
            return await self._index.create(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            msg = str(e).lower()
            if "type" in msg and ("int8" in msg or "unknown argument" in msg):
                raise RuntimeError(
                    "int8 vector fields require the Redis 8 Query Engine; the "
                    "configured Redis rejected TYPE INT8. Use a Redis 8 CE "
                    "backend, or unset MEMORY_VECTOR_DB_FACTORY to use float32."
                ) from e
            raise

    async def load(self, data: list[dict], *args: Any, **kwargs: Any) -> Any:
        """Re-encode each record's float32 vector bytes as int8 before load."""
        for rec in data:
            v = rec.get(_VECTOR_FIELD)
            if isinstance(v, bytes | bytearray):
                floats = np.frombuffer(v, dtype=np.float32)
                rec[_VECTOR_FIELD] = np.array(quantize_int8(floats), dtype=np.int8).tobytes()
        return await self._index.load(data, *args, **kwargs)

    async def query(self, query: Any, *args: Any, **kwargs: Any) -> Any:
        """Quantize the query vector and flip dtype to int8 before executing."""
        vec = getattr(query, "_vector", None)
        if vec is not None:
            query._vector = quantize_int8(vec)
            query._dtype = "int8"
        return await self._index.query(query, *args, **kwargs)

    async def aggregate(self, *args: Any, **kwargs: Any) -> Any:
        """Server-side recency aggregation is unsupported on int8.

        Raising forces AMS's built-in fallback to the standard query
        path (handled by ``query`` above) plus client-side recency.
        """
        raise NotImplementedError(
            "int8 backend does not support server-side recency aggregation; "
            "falling back to standard vector query"
        )


def _build_int8_schema() -> dict:
    """AMS's RedisVL schema with the vector field's datatype set to int8."""
    from agent_memory_server.memory_vector_db_factory import _build_redis_schema

    schema = _build_redis_schema()
    for field in schema.get("fields", []):
        if field.get("type") == "vector":
            field.setdefault("attrs", {})["datatype"] = "int8"
    return schema


def create_int8_memory_db(embeddings: Any) -> Any:
    """Factory for ``MEMORY_VECTOR_DB_FACTORY``: int8 Redis vector DB.

    Args:
        embeddings: AMS embeddings instance (passed by the server).

    Returns:
        A ``RedisVLMemoryVectorDatabase`` whose index stores/queries
        int8 vectors via :class:`Int8VectorIndexProxy`.
    """
    from agent_memory_server.config import settings
    from agent_memory_server.memory_vector_db import RedisVLMemoryVectorDatabase
    from agent_memory_server.utils.redis import redis_url_for_redisvl
    from redisvl.index import AsyncSearchIndex

    schema = _build_int8_schema()
    index = AsyncSearchIndex.from_dict(schema, redis_url=redis_url_for_redisvl(settings.redis_url))
    proxy = Int8VectorIndexProxy(index)
    logger.info("int8 memory vector DB created (index=%s)", schema["index"]["name"])
    return RedisVLMemoryVectorDatabase(proxy, embeddings)


__all__ = ["create_int8_memory_db", "quantize_int8", "Int8VectorIndexProxy"]
