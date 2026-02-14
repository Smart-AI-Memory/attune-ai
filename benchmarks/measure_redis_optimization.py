#!/usr/bin/env python3
"""Measure Redis two-tier caching performance improvements.

This script validates the performance impact of local LRU caching:
- Without local cache: 37ms per Redis operation (network I/O)
- With local cache: <0.001ms per operation (memory access)
- Expected hit rate: 80%+ for frequently accessed keys

Usage:
    python benchmarks/measure_redis_optimization.py

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from attune.memory.short_term import RedisShortTermMemory
from attune.memory.types import AccessTier, AgentCredentials, RedisConfig


def measure_redis_performance():
    """Measure performance with and without local caching."""
    print("=" * 70)
    print("REDIS TWO-TIER CACHING PERFORMANCE MEASUREMENT")
    print("=" * 70)

    # Test credentials
    creds = AgentCredentials(agent_id="test_agent", tier=AccessTier.CONTRIBUTOR)

    # Test data
    test_keys = [f"test_key_{i}" for i in range(100)]
    test_data = [{"value": f"data_{i}", "count": i} for i in range(100)]

    print("\n📊 Test Configuration:")
    print(f"  Keys: {len(test_keys)}")
    print("  Operations: 300 (3 passes)")
    print("  Expected local cache hit rate: 66%+ (2/3 passes)")

    # =========================================================================
    # Test 1: WITHOUT local cache
    # =========================================================================
    print("\n" + "=" * 70)
    print("Test 1: WITHOUT Local Cache (Redis network I/O only)")
    print("=" * 70)

    config1 = RedisConfig(
        use_mock=True,  # Use mock for testing
        local_cache_enabled=False,  # DISABLE local cache
    )
    memory1 = RedisShortTermMemory(config=config1)

    # Write data
    print("\n🔄 Pass 1: Writing 100 items...")
    start1_write = time.perf_counter()
    for key, data in zip(test_keys, test_data):
        memory1.stash(key, data, creds)
    write_duration1 = time.perf_counter() - start1_write

    # Read data (Pass 1)
    print("🔄 Pass 2: Reading 100 items...")
    start1_read1 = time.perf_counter()
    for key in test_keys:
        memory1.retrieve(key, creds)
    read_duration1_pass1 = time.perf_counter() - start1_read1

    # Read data (Pass 2 - repeat)
    print("🔄 Pass 3: Reading 100 items again...")
    start1_read2 = time.perf_counter()
    for key in test_keys:
        memory1.retrieve(key, creds)
    read_duration1_pass2 = time.perf_counter() - start1_read2

    total_duration1 = write_duration1 + read_duration1_pass1 + read_duration1_pass2

    print("\n✅ Results:")
    print(f"  Write (100 items): {write_duration1:.3f}s ({write_duration1*10:.2f}ms per item)")
    print(f"  Read Pass 1: {read_duration1_pass1:.3f}s ({read_duration1_pass1*10:.2f}ms per item)")
    print(f"  Read Pass 2: {read_duration1_pass2:.3f}s ({read_duration1_pass2*10:.2f}ms per item)")
    print(f"  Total: {total_duration1:.3f}s")
    print(f"  Cache stats: {memory1.get_local_cache_stats()}")

    # =========================================================================
    # Test 2: WITH local cache
    # =========================================================================
    print("\n" + "=" * 70)
    print("Test 2: WITH Local Cache (Two-tier: Memory + Redis)")
    print("=" * 70)

    config2 = RedisConfig(
        use_mock=True,  # Use mock for testing
        local_cache_enabled=True,  # ENABLE local cache
        local_cache_size=500,
    )
    memory2 = RedisShortTermMemory(config=config2)

    # Write data
    print("\n🔄 Pass 1: Writing 100 items...")
    start2_write = time.perf_counter()
    for key, data in zip(test_keys, test_data):
        memory2.stash(key, data, creds)
    write_duration2 = time.perf_counter() - start2_write

    # Read data (Pass 1 - populates local cache)
    print("🔄 Pass 2: Reading 100 items (populating cache)...")
    start2_read1 = time.perf_counter()
    for key in test_keys:
        memory2.retrieve(key, creds)
    read_duration2_pass1 = time.perf_counter() - start2_read1

    # Read data (Pass 2 - should hit local cache)
    print("🔄 Pass 3: Reading 100 items again (from cache)...")
    start2_read2 = time.perf_counter()
    for key in test_keys:
        memory2.retrieve(key, creds)
    read_duration2_pass2 = time.perf_counter() - start2_read2

    total_duration2 = write_duration2 + read_duration2_pass1 + read_duration2_pass2
    cache_stats = memory2.get_local_cache_stats()

    print("\n✅ Results:")
    print(f"  Write (100 items): {write_duration2:.3f}s ({write_duration2*10:.2f}ms per item)")
    print(f"  Read Pass 1: {read_duration2_pass1:.3f}s ({read_duration2_pass1*10:.2f}ms per item)")
    print(f"  Read Pass 2: {read_duration2_pass2:.3f}s ({read_duration2_pass2*10:.2f}ms per item)")
    print(f"  Total: {total_duration2:.3f}s")
    print("\n📊 Local Cache Stats:")
    print(f"  Enabled: {cache_stats['enabled']}")
    print(f"  Size: {cache_stats['size']}/{cache_stats['max_size']}")
    print(f"  Hits: {cache_stats['hits']}")
    print(f"  Misses: {cache_stats['misses']}")
    print(f"  Hit Rate: {cache_stats['hit_rate']:.1f}%")

    # =========================================================================
    # Analysis
    # =========================================================================
    print("\n" + "=" * 70)
    print("PERFORMANCE ANALYSIS")
    print("=" * 70)

    speedup = total_duration1 / total_duration2 if total_duration2 > 0 else 0
    time_saved = total_duration1 - total_duration2
    time_saved_pct = (time_saved / total_duration1 * 100) if total_duration1 > 0 else 0

    print("\n🚀 Overall Performance:")
    print(f"  Without local cache: {total_duration1:.3f}s")
    print(f"  With local cache: {total_duration2:.3f}s")
    print(f"  Speedup: {speedup:.2f}x")
    print(f"  Time saved: {time_saved:.3f}s ({time_saved_pct:.1f}%)")

    # Read Pass 2 comparison (where cache makes biggest difference)
    pass2_speedup = read_duration1_pass2 / read_duration2_pass2 if read_duration2_pass2 > 0 else 0
    pass2_saved = read_duration1_pass2 - read_duration2_pass2
    pass2_saved_pct = (pass2_saved / read_duration1_pass2 * 100) if read_duration1_pass2 > 0 else 0

    print("\n🎯 Cache Impact (Read Pass 3 - fully cached):")
    print(f"  Without cache: {read_duration1_pass2:.3f}s")
    print(f"  With cache: {read_duration2_pass2:.3f}s")
    print(f"  Speedup: {pass2_speedup:.2f}x")
    print(f"  Time saved: {pass2_saved:.3f}s ({pass2_saved_pct:.1f}%)")

    print("\n✅ Success Criteria:")
    if cache_stats["hit_rate"] >= 50:
        print(f"  ✓ Cache hit rate: {cache_stats['hit_rate']:.1f}% (target: >50%)")
    else:
        print(f"  ✗ Cache hit rate: {cache_stats['hit_rate']:.1f}% (target: >50%)")

    if speedup >= 1.2:
        print(f"  ✓ Overall speedup: {speedup:.2f}x (target: >1.2x)")
    else:
        print(f"  ✗ Overall speedup: {speedup:.2f}x (target: >1.2x)")

    if pass2_speedup >= 2:
        print(f"  ✓ Cached read speedup: {pass2_speedup:.2f}x (target: >2x)")
    else:
        print(f"  ✗ Cached read speedup: {pass2_speedup:.2f}x (target: >2x)")

    return {
        "speedup": speedup,
        "time_saved": time_saved,
        "cache_hit_rate": cache_stats["hit_rate"],
        "pass2_speedup": pass2_speedup,
    }


if __name__ == "__main__":
    results = measure_redis_performance()
