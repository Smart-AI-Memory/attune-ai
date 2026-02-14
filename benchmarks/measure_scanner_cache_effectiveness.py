#!/usr/bin/env python3
"""Measure actual cache effectiveness for scanner operations.

This script validates the performance of the scanner's existing LRU caches:
- File hash caching (@lru_cache on _hash_file)
- AST parse caching (@lru_cache on _parse_python_cached)

Usage:
    python benchmarks/measure_scanner_cache_effectiveness.py

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

from attune.project_index.scanner import ProjectScanner


def measure_cache_effectiveness():
    """Run scanner twice to measure cache hit rates."""
    scanner = ProjectScanner(project_root=".")

    print("=" * 60)
    print("SCANNER CACHE EFFECTIVENESS MEASUREMENT")
    print("=" * 60)

    # Run 1: Cold cache
    print("\n🥶 Run 1: Cold Cache")
    scanner._hash_file.cache_clear()
    scanner._parse_python_cached.cache_clear()

    start1 = time.perf_counter()
    records1, summary1 = scanner.scan()
    duration1 = time.perf_counter() - start1

    hash_stats1 = scanner._hash_file.cache_info()
    parse_stats1 = scanner._parse_python_cached.cache_info()

    print(f"Duration: {duration1:.2f}s")
    print(f"Files: {summary1.total_files}")
    print(f"Hash cache: {hash_stats1.hits} hits, {hash_stats1.misses} misses")
    print(f"Parse cache: {parse_stats1.hits} hits, {parse_stats1.misses} misses")

    # Run 2: Warm cache
    print("\n🔥 Run 2: Warm Cache (repeat scan)")
    start2 = time.perf_counter()
    records2, summary2 = scanner.scan()
    duration2 = time.perf_counter() - start2

    hash_stats2 = scanner._hash_file.cache_info()
    parse_stats2 = scanner._parse_python_cached.cache_info()

    # Calculate deltas
    hash_hits_2 = hash_stats2.hits - hash_stats1.hits
    hash_misses_2 = hash_stats2.misses - hash_stats1.misses
    parse_hits_2 = parse_stats2.hits - parse_stats1.hits
    parse_misses_2 = parse_stats2.misses - parse_stats1.misses

    hash_hit_rate_2 = (
        (hash_hits_2 / (hash_hits_2 + hash_misses_2) * 100)
        if (hash_hits_2 + hash_misses_2) > 0
        else 0
    )
    parse_hit_rate_2 = (
        (parse_hits_2 / (parse_hits_2 + parse_misses_2) * 100)
        if (parse_hits_2 + parse_misses_2) > 0
        else 0
    )

    print(f"Duration: {duration2:.2f}s")
    print(f"Files: {summary2.total_files}")
    print(
        f"Hash cache (Run 2): {hash_hits_2} hits, {hash_misses_2} misses ({hash_hit_rate_2:.1f}% hit rate)"
    )
    print(
        f"Parse cache (Run 2): {parse_hits_2} hits, {parse_misses_2} misses ({parse_hit_rate_2:.1f}% hit rate)"
    )

    # Analysis
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    speedup = (duration1 / duration2) if duration2 > 0 else 0
    time_saved = duration1 - duration2

    print(f"Speedup: {speedup:.2f}x")
    print(f"Time saved: {time_saved:.2f}s ({time_saved/duration1*100:.1f}%)")

    print("\n✅ Cache Status:")
    if parse_hit_rate_2 >= 90:
        print(f"  Parse cache: EXCELLENT ({parse_hit_rate_2:.1f}% hit rate)")
    elif parse_hit_rate_2 >= 70:
        print(f"  Parse cache: GOOD ({parse_hit_rate_2:.1f}% hit rate)")
    else:
        print(f"  Parse cache: NEEDS IMPROVEMENT ({parse_hit_rate_2:.1f}% hit rate)")

    if hash_hit_rate_2 >= 80:
        print(f"  Hash cache: EXCELLENT ({hash_hit_rate_2:.1f}% hit rate)")
    elif hash_hit_rate_2 >= 60:
        print(f"  Hash cache: GOOD ({hash_hit_rate_2:.1f}% hit rate)")
    else:
        print(f"  Hash cache: NEEDS IMPROVEMENT ({hash_hit_rate_2:.1f}% hit rate)")

    print("\n📊 Cache Sizes:")
    print(f"  Hash: {hash_stats2.currsize}/{hash_stats2.maxsize} entries")
    print(f"  Parse: {parse_stats2.currsize}/{parse_stats2.maxsize} entries")

    return {
        "run1_duration": duration1,
        "run2_duration": duration2,
        "speedup": speedup,
        "hash_hit_rate": hash_hit_rate_2,
        "parse_hit_rate": parse_hit_rate_2,
    }


if __name__ == "__main__":
    results = measure_cache_effectiveness()
