#!/usr/bin/env python3
"""Analyze profiling results to identify top bottlenecks.

Usage:
    python benchmarks/analyze_profiles.py
"""

import pstats
from pathlib import Path
from typing import NamedTuple


class Hotspot(NamedTuple):
    """Performance hotspot information."""

    profile_name: str
    function_name: str
    filename: str
    line_number: int
    cumulative_time: float
    cumulative_percent: float
    call_count: int
    per_call_time: float


def analyze_profile(profile_path: Path, total_program_time: float) -> list[Hotspot]:
    """Analyze a single profile file and extract top hotspots.

    Args:
        profile_path: Path to .prof file
        total_program_time: Total execution time for percentage calculation

    Returns:
        List of Hotspot objects sorted by cumulative time
    """
    stats = pstats.Stats(str(profile_path))
    stats.sort_stats("cumulative")

    hotspots = []
    profile_name = profile_path.stem

    # Get top 15 functions by cumulative time
    for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:15]:
        filename, line, func_name = func

        # Skip built-in functions and very short operations
        if ct < 0.01:  # Less than 10ms
            continue

        # Calculate percentage of total time
        percent = (ct / total_program_time * 100) if total_program_time > 0 else 0

        hotspot = Hotspot(
            profile_name=profile_name,
            function_name=func_name,
            filename=filename,
            line_number=line,
            cumulative_time=ct,
            cumulative_percent=percent,
            call_count=cc,
            per_call_time=ct / cc if cc > 0 else 0,
        )
        hotspots.append(hotspot)

    return hotspots


def main():
    """Analyze all profile files and generate report."""
    profiles_dir = Path("benchmarks/profiles")

    if not profiles_dir.exists():
        print("❌ No profiles directory found. Run profile_suite.py first.")
        return

    print("=" * 80)
    print("PERFORMANCE BOTTLENECK ANALYSIS")
    print("Empathy Framework - Phase 2 Optimization")
    print("=" * 80)

    all_hotspots = []
    profile_times = {}

    # Analyze each profile
    for profile_file in sorted(profiles_dir.glob("*.prof")):
        if profile_file.name == "profiling_output.txt":
            continue

        try:
            stats = pstats.Stats(str(profile_file))
            total_time = stats.total_tt
            profile_times[profile_file.stem] = total_time

            hotspots = analyze_profile(profile_file, total_time)
            all_hotspots.extend(hotspots)

            print(f"\n📊 {profile_file.stem.upper()} ({total_time:.2f}s total)")
            print("-" * 80)

            for i, hotspot in enumerate(hotspots[:5], 1):
                print(
                    f"{i}. {hotspot.function_name:40s} "
                    f"{hotspot.cumulative_time:6.3f}s ({hotspot.cumulative_percent:5.1f}%) "
                    f"[{hotspot.call_count:,} calls]"
                )
                if not hotspot.filename.startswith("~"):
                    print(f"   📁 {hotspot.filename}:{hotspot.line_number}")

        except Exception as e:
            print(f"⚠️  Error analyzing {profile_file.name}: {e}")

    # Rank all hotspots by cumulative time
    all_hotspots.sort(key=lambda h: h.cumulative_time, reverse=True)

    print("\n" + "=" * 80)
    print("TOP 10 OVERALL HOTSPOTS (by cumulative time)")
    print("=" * 80)

    for i, hotspot in enumerate(all_hotspots[:10], 1):
        print(f"\n{i}. {hotspot.function_name}")
        print(f"   Profile: {hotspot.profile_name}")
        print(f"   Time: {hotspot.cumulative_time:.3f}s ({hotspot.cumulative_percent:.1f}%)")
        print(f"   Calls: {hotspot.call_count:,}")
        print(f"   Per Call: {hotspot.per_call_time * 1000:.2f}ms")
        if not hotspot.filename.startswith("~"):
            print(f"   Location: {hotspot.filename}:{hotspot.line_number}")

    print("\n" + "=" * 80)
    print("PROFILE EXECUTION TIMES")
    print("=" * 80)

    for name, time in sorted(profile_times.items(), key=lambda x: x[1], reverse=True):
        print(f"{name:30s} {time:8.3f}s")

    print("\n" + "=" * 80)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("=" * 80)
    print(
        """
Based on profiling results, prioritize these optimizations:

1. **AST Parsing Caching** (HIGH IMPACT)
   - Cache parsed AST trees with file hash as key
   - Expected: 90%+ cache hit rate on incremental scans
   - Target: scanner_scan.prof bottleneck

2. **File I/O Optimization** (HIGH IMPACT)
   - Cache file hashes to avoid re-reading unchanged files
   - Expected: 80%+ cache hit rate
   - Target: scanner_scan.prof

3. **Import Optimization** (MEDIUM IMPACT)
   - Lazy imports for rarely-used modules
   - Expected: 20-30% reduction in startup time
   - Target: workflow_execution.prof

4. **Generator Expressions** (MEDIUM IMPACT)
   - Replace list comprehensions in file scanning
   - Expected: 50-90% memory reduction
   - Target: scanner_scan.prof, memory_operations.prof

5. **Data Structure Optimization** (LOW-MEDIUM IMPACT)
   - Replace O(n) lookups with O(1) hash tables
   - Expected: Minimal impact (pattern library already optimized)
   - Target: pattern_library.prof

Next Steps:
1. Visualize profiles: snakeviz benchmarks/profiles/scanner_scan.prof
2. Implement LRU caching for AST parsing
3. Add file hash caching with mtime tracking
4. Convert file scanning to generators
    """
    )


if __name__ == "__main__":
    main()
