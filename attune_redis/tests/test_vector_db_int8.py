"""Tests for the int8 vector backend (attune_redis.vector_db_int8).

Three layers:
- pure quantization math (numpy only)
- proxy behavior against a fake index (no Redis)
- drift guards against agent-memory-server internals the proxy
  relies on (skipped when agent_memory_server isn't installed)

The live round-trip (factory -> proxy -> RedisVLMemoryVectorDatabase
-> Redis 8) is validated manually in
docs/specs/ams-int8-quantization/ — it needs a Redis 8 Query Engine
plus Ollama, which CI does not provide.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio

import pytest

np = pytest.importorskip("numpy")

from attune_redis.vector_db_int8 import (  # noqa: E402
    Int8VectorIndexProxy,
    _build_int8_schema,
    quantize_int8,
)

# --------------------------------------------------------------------------
# Quantization math
# --------------------------------------------------------------------------


def test_quantize_within_int8_range():
    out = quantize_int8([0.13, -0.42, 0.05, -0.9, 0.9])
    assert all(-127 <= v <= 127 for v in out)
    assert all(isinstance(v, int) for v in out)


def test_quantize_max_abs_maps_to_127():
    # The largest-magnitude component maps to the int8 extreme.
    out = quantize_int8([0.5, -1.0, 0.25])
    assert out[1] == -127
    assert out == [64, -127, 32]


def test_quantize_handles_all_zero_vector():
    # peak falls back to 1.0; no division by zero.
    assert quantize_int8([0.0, 0.0, 0.0]) == [0, 0, 0]


# --------------------------------------------------------------------------
# Proxy behavior (fake index, no Redis)
# --------------------------------------------------------------------------


class _FakeIndex:
    def __init__(self):
        self.loaded = None
        self.queried = None
        self.create_calls = 0

    async def load(self, data, *a, **k):
        self.loaded = data
        return ["x"]

    async def query(self, q, *a, **k):
        self.queried = q
        return []

    async def create(self, *a, **k):
        self.create_calls += 1
        return "created"

    name = "fake-index"


class _FakeQuery:
    def __init__(self, vec):
        self._vector = vec
        self._dtype = "float32"


def test_proxy_load_reencodes_float32_bytes_to_int8():
    idx = _FakeIndex()
    proxy = Int8VectorIndexProxy(idx)
    blob = np.array([0.5, -1.0, 0.25], dtype=np.float32).tobytes()  # 12 bytes
    asyncio.run(proxy.load([{"vector": blob, "id_": "m1"}]))
    out = idx.loaded[0]["vector"]
    assert isinstance(out, bytes)
    assert len(out) == 3  # 3 int8 bytes, not 12 float32 bytes
    assert list(np.frombuffer(out, dtype=np.int8)) == [64, -127, 32]


def test_proxy_load_ignores_records_without_bytes_vector():
    idx = _FakeIndex()
    proxy = Int8VectorIndexProxy(idx)
    asyncio.run(proxy.load([{"id_": "m1"}]))  # no vector key
    assert idx.loaded == [{"id_": "m1"}]


def test_proxy_query_quantizes_and_sets_int8_dtype():
    idx = _FakeIndex()
    proxy = Int8VectorIndexProxy(idx)
    q = _FakeQuery([0.5, -1.0, 0.25])
    asyncio.run(proxy.query(q))
    assert q._dtype == "int8"
    assert q._vector == [64, -127, 32]
    assert idx.queried is q


def test_proxy_aggregate_raises_to_force_fallback():
    proxy = Int8VectorIndexProxy(_FakeIndex())
    with pytest.raises(NotImplementedError):
        asyncio.run(proxy.aggregate())


def test_proxy_delegates_unknown_attrs():
    proxy = Int8VectorIndexProxy(_FakeIndex())
    assert proxy.name == "fake-index"


def test_proxy_create_translates_int8_unsupported_error():
    class _Rejecting(_FakeIndex):
        async def create(self, *a, **k):
            raise ValueError(
                "Bad arguments for vector similarity HNSW index `TYPE`: " "Unknown argument"
            )

    proxy = Int8VectorIndexProxy(_Rejecting())
    with pytest.raises(RuntimeError, match="Redis 8 Query Engine"):
        asyncio.run(proxy.create())


def test_proxy_create_passes_through_unrelated_errors():
    class _Boom(_FakeIndex):
        async def create(self, *a, **k):
            raise ValueError("connection refused")

    proxy = Int8VectorIndexProxy(_Boom())
    with pytest.raises(ValueError, match="connection refused"):
        asyncio.run(proxy.create())


def test_proxy_create_success_delegates():
    idx = _FakeIndex()
    proxy = Int8VectorIndexProxy(idx)
    assert asyncio.run(proxy.create()) == "created"
    assert idx.create_calls == 1


# --------------------------------------------------------------------------
# Drift guards against agent-memory-server internals
# --------------------------------------------------------------------------


def test_build_int8_schema_sets_vector_datatype():
    pytest.importorskip("agent_memory_server")
    schema = _build_int8_schema()
    vec = [f for f in schema["fields"] if f.get("type") == "vector"]
    assert len(vec) == 1
    assert vec[0]["attrs"]["datatype"] == "int8"


def test_ams_add_memories_still_encodes_float32():
    """proxy.load assumes AMS hands it float32 vector bytes."""
    pytest.importorskip("agent_memory_server")
    import inspect

    from agent_memory_server.memory_vector_db import RedisVLMemoryVectorDatabase

    src = inspect.getsource(RedisVLMemoryVectorDatabase.add_memories)
    assert "dtype=np.float32" in src, (
        "AMS add_memories no longer encodes float32; "
        "Int8VectorIndexProxy.load assumptions need review"
    )


def test_redisvl_vectorquery_exposes_vector_and_dtype():
    """proxy.query mutates VectorQuery._vector and ._dtype."""
    pytest.importorskip("redisvl")
    from redisvl.query import VectorQuery

    vq = VectorQuery(vector=[0.1, 0.2], vector_field_name="vector")
    assert hasattr(vq, "_vector")
    assert hasattr(vq, "_dtype")
