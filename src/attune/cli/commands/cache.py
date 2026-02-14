"""Cache monitoring and statistics commands for the CLI.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def cmd_cache_stats(args):
    """Display prompt caching statistics and savings.

    Analyzes logs and telemetry to show cache performance metrics:
    - Cache hit rate
    - Total cost savings
    - Cache read/write tokens
    - Recommendations for optimization

    Args:
        args: Namespace object from argparse with attributes:
            - days (int): Number of days to analyze (default: 7)
            - format (str): Output format ('table' or 'json')
            - verbose (bool): Show detailed breakdown

    Returns:
        None: Prints cache statistics report or JSON output
    """
    print(f"\n🔍 Analyzing cache performance (last {args.days} days)...\n")

    # Collect cache metrics from logs
    stats = _collect_cache_stats(days=args.days)

    if args.format == "json":
        print(json.dumps(stats, indent=2))
        return

    # Display formatted report
    _display_cache_report(stats, verbose=args.verbose)


def _collect_cache_stats(days: int = 7) -> dict[str, Any]:
    """Collect cache statistics from logs and telemetry.

    Args:
        days: Number of days to analyze

    Returns:
        Dictionary with cache statistics
    """
    # Try to find log files
    log_paths = [
        Path.cwd() / "attune.log",
        Path.home() / ".attune" / "logs" / "attune.log",
        Path("/tmp/attune.log"),  # nosec B108 - temp log file location
    ]

    log_file = None
    for path in log_paths:
        if path.exists():
            log_file = path
            break

    if not log_file:
        return {
            "error": "No log file found",
            "message": "Enable logging to track cache performance",
            "total_requests": 0,
            "cache_hits": 0,
            "cache_writes": 0,
            "total_savings": 0.0,
        }

    # Parse log file for cache metrics
    cutoff_date = datetime.now() - timedelta(days=days)

    cache_hits = 0
    cache_writes = 0
    total_cache_read_tokens = 0
    total_cache_write_tokens = 0
    total_savings = 0.0
    total_requests = 0

    # Regex patterns for log parsing
    cache_hit_pattern = re.compile(r"Cache HIT: ([\d,]+) tokens read.*saved \$([\d.]+)")
    cache_write_pattern = re.compile(r"Cache WRITE: ([\d,]+) tokens written.*cost \$([\d.]+)")

    try:
        with open(log_file) as f:
            for line in f:
                # Try to extract timestamp
                # Common format: 2026-01-27 21:30:45,123
                timestamp_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                if timestamp_match:
                    try:
                        log_time = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S")
                        if log_time < cutoff_date:
                            continue  # Skip old entries
                    except ValueError:
                        pass  # Continue if timestamp parsing fails

                # Count API requests (approximate)
                if "anthropic.AsyncAnthropic" in line or "messages.create" in line:
                    total_requests += 1

                # Parse cache hit
                hit_match = cache_hit_pattern.search(line)
                if hit_match:
                    tokens_str = hit_match.group(1).replace(",", "")
                    tokens = int(tokens_str)
                    savings = float(hit_match.group(2))

                    cache_hits += 1
                    total_cache_read_tokens += tokens
                    total_savings += savings

                # Parse cache write
                write_match = cache_write_pattern.search(line)
                if write_match:
                    tokens_str = write_match.group(1).replace(",", "")
                    tokens = int(tokens_str)

                    cache_writes += 1
                    total_cache_write_tokens += tokens

    except Exception as e:
        return {
            "error": f"Failed to parse log file: {e}",
            "total_requests": 0,
            "cache_hits": 0,
            "cache_writes": 0,
            "total_savings": 0.0,
        }

    # Calculate metrics
    cache_hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0.0

    return {
        "days_analyzed": days,
        "log_file": str(log_file),
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_writes": cache_writes,
        "cache_hit_rate": round(cache_hit_rate, 1),
        "total_cache_read_tokens": total_cache_read_tokens,
        "total_cache_write_tokens": total_cache_write_tokens,
        "total_savings": round(total_savings, 4),
        "avg_savings_per_hit": (round(total_savings / cache_hits, 4) if cache_hits > 0 else 0.0),
    }


def _display_cache_report(stats: dict[str, Any], verbose: bool = False):
    """Display formatted cache statistics report.

    Args:
        stats: Cache statistics dictionary
        verbose: Show detailed breakdown
    """
    # Handle error cases
    if "error" in stats:
        print(f"⚠️  {stats['error']}")
        if "message" in stats:
            print(f"   {stats['message']}")
        return

    # Summary section
    print("=" * 60)
    print("PROMPT CACHING PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Analysis Period: Last {stats['days_analyzed']} days")
    print(f"Log File: {stats['log_file']}")
    print()

    # Key metrics
    print("📊 Key Metrics:")
    print(f"  Total API Requests: {stats['total_requests']:,}")
    print(f"  Cache Hits: {stats['cache_hits']:,}")
    print(f"  Cache Writes: {stats['cache_writes']:,}")
    print(f"  Cache Hit Rate: {stats['cache_hit_rate']}%")
    print()

    # Cost savings
    print("💰 Cost Savings:")
    print(f"  Total Saved: ${stats['total_savings']:.4f}")
    if stats["cache_hits"] > 0:
        print(f"  Avg Savings per Hit: ${stats['avg_savings_per_hit']:.4f}")
    print()

    # Token metrics (verbose mode)
    if verbose:
        print("🔢 Token Metrics:")
        print(f"  Cache Read Tokens: {stats['total_cache_read_tokens']:,}")
        print(f"  Cache Write Tokens: {stats['total_cache_write_tokens']:,}")
        print()

    # Performance assessment
    hit_rate = stats["cache_hit_rate"]
    print("📈 Performance Assessment:")
    if hit_rate >= 50:
        print("  ✅ EXCELLENT - Cache is working effectively")
        print("     Your workflows are benefiting from prompt caching")
    elif hit_rate >= 30:
        print("  ✓ GOOD - Cache is providing moderate benefits")
        print("     Consider structuring prompts for better cache reuse")
    elif hit_rate >= 10:
        print("  ⚠️  LOW - Cache hit rate could be improved")
        print("     Review your workflow patterns for optimization")
    else:
        print("  ❌ VERY LOW - Cache is not being utilized effectively")
        print("     Consider enabling prompt caching or restructuring prompts")
    print()

    # Recommendations
    if stats["total_requests"] < 10:
        print("ℹ️  Note: Limited data available. Run more workflows for accurate stats.")
    elif hit_rate < 30:
        print("💡 Recommendations:")
        print("  1. Reuse system prompts across workflow steps")
        print("  2. Structure large context (docs, code) for caching")
        print("  3. Cache TTL is 5 minutes - batch related requests")
        print("  4. Enable use_prompt_caching=True in AnthropicProvider")

    print("=" * 60)


def cmd_cache_clear(args):
    """Clear cached data (placeholder for future implementation).

    Args:
        args: Namespace object from argparse

    Returns:
        None: Prints status message
    """
    print("\n⚠️  Cache clearing not implemented.")
    print("Anthropic's cache has a 5-minute TTL and is server-side.")
    print("Wait 5 minutes for cache to expire naturally.\n")
