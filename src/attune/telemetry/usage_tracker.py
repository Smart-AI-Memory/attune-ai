"""Usage Tracker for Empathy Framework Telemetry.

Privacy-first, local-only tracking of LLM calls to measure actual cost savings.
All data stored locally in ~/.attune/telemetry/ as JSON Lines format.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import hashlib
import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class UsageTracker:
    """Privacy-first local telemetry tracker.

    Tracks LLM calls to JSON Lines format with automatic rotation
    and 90-day retention. Thread-safe with atomic writes.

    All user identifiers are SHA256 hashed for privacy.
    No prompts, responses, file paths, or PII are ever tracked.
    """

    # Class-level lock for thread safety across all instances
    _lock = threading.Lock()
    # Monotonic sequence counter for deterministic ordering
    # (datetime may have low resolution on some platforms)
    _seq_counter: int = 0
    # Singleton instance
    _instance: "UsageTracker | None" = None

    def __init__(
        self,
        telemetry_dir: Path | None = None,
        retention_days: int = 90,
        max_file_size_mb: int = 10,
    ):
        """Initialize UsageTracker.

        Args:
            telemetry_dir: Directory for telemetry files.
                          Defaults to ~/.attune/telemetry/
            retention_days: Days to retain telemetry data (default: 90)
            max_file_size_mb: Max size in MB before rotation (default: 10)

        """
        self.telemetry_dir = telemetry_dir or Path.home() / ".empathy" / "telemetry"
        self.retention_days = retention_days
        self.max_file_size_mb = max_file_size_mb
        self.usage_file = self.telemetry_dir / "usage.jsonl"

        # Create directory if needed (gracefully handle permission errors)
        try:
            self.telemetry_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Can't create directory - telemetry will be disabled
            logger.debug(f"Failed to create telemetry directory: {self.telemetry_dir}")

    @classmethod
    def get_instance(cls, **kwargs: Any) -> "UsageTracker":
        """Get singleton instance of UsageTracker.

        Args:
            **kwargs: Arguments passed to __init__ if creating new instance

        Returns:
            Singleton UsageTracker instance

        """
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    def track_llm_call(
        self,
        workflow: str,
        stage: str | None,
        tier: str,
        model: str,
        provider: str,
        cost: float,
        tokens: dict[str, int],
        cache_hit: bool,
        cache_type: str | None,
        duration_ms: int,
        user_id: str | None = None,
        prompt_cache_hit: bool = False,
        prompt_cache_creation_tokens: int = 0,
        prompt_cache_read_tokens: int = 0,
    ) -> None:
        """Track a single LLM call with prompt caching metrics.

        Args:
            workflow: Workflow name (e.g., "code-review")
            stage: Stage name (e.g., "analysis"), optional
            tier: Model tier (CHEAP, CAPABLE, PREMIUM)
            model: Model ID (e.g., "claude-sonnet-4.5")
            provider: Provider name (anthropic, openai, etc.)
            cost: Cost in USD
            tokens: Dict with "input" and "output" keys
            cache_hit: Whether this was a local cache hit
            cache_type: Cache type if hit ("hash", "hybrid", etc.)
            duration_ms: Call duration in milliseconds
            user_id: Optional user identifier (will be hashed)
            prompt_cache_hit: Whether Anthropic prompt cache was used
            prompt_cache_creation_tokens: Tokens written to Anthropic cache
            prompt_cache_read_tokens: Tokens read from Anthropic cache

        """
        # Build entry
        UsageTracker._seq_counter += 1
        entry: dict[str, Any] = {
            "v": "1.0",
            "ts": datetime.utcnow().isoformat() + "Z",
            "seq": UsageTracker._seq_counter,
            "workflow": workflow,
            "tier": tier,
            "model": model,
            "provider": provider,
            "cost": round(cost, 6),
            "tokens": tokens,
            "cache": {"hit": cache_hit},
            "duration_ms": duration_ms,
            "user_id": self._hash_user_id(user_id or "default"),
        }

        # Add optional fields
        if stage:
            entry["stage"] = stage
        if cache_hit and cache_type:
            entry["cache"]["type"] = cache_type

        # Add prompt cache metrics (Anthropic-specific)
        if prompt_cache_hit or prompt_cache_creation_tokens > 0 or prompt_cache_read_tokens > 0:
            entry["prompt_cache"] = {
                "hit": prompt_cache_hit,
                "creation_tokens": prompt_cache_creation_tokens,
                "read_tokens": prompt_cache_read_tokens,
            }

        # Write entry (thread-safe, atomic)
        try:
            self._write_entry(entry)
            # Check if rotation needed
            self._rotate_if_needed()
        except OSError as e:
            # File system errors - log but don't crash
            logger.debug(f"Failed to write telemetry entry: {e}")
        except Exception as ex:
            # INTENTIONAL: Telemetry failures should never crash the workflow
            logger.debug(f"Unexpected error writing telemetry entry: {ex}")

    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID with SHA256 for privacy.

        Args:
            user_id: User identifier to hash

        Returns:
            First 16 characters of SHA256 hash

        """
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    def _write_entry(self, entry: dict[str, Any]) -> None:
        """Write entry to JSON Lines file atomically.

        Uses atomic write pattern: write to temp file, then rename.
        This ensures no partial writes even with concurrent access.

        Args:
            entry: Dictionary entry to write

        """
        with self._lock:
            # Write to temp file
            temp_file = self.usage_file.with_suffix(".tmp")
            try:
                # Append to temp file
                with open(temp_file, "a", encoding="utf-8") as f:
                    json.dump(entry, f, separators=(",", ":"))
                    f.write("\n")

                # Atomic rename: temp -> usage.jsonl
                # If usage.jsonl exists, we need to append
                if self.usage_file.exists():
                    # Read temp file content
                    with open(temp_file, encoding="utf-8") as f:
                        new_line = f.read()
                    # Append to main file
                    with open(self.usage_file, "a", encoding="utf-8") as f:
                        f.write(new_line)
                    # Clean up temp file
                    temp_file.unlink()
                else:
                    # Just rename temp to main
                    temp_file.replace(self.usage_file)
            except OSError:
                # Clean up temp file if it exists
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except OSError:
                        pass
                raise

    def _rotate_if_needed(self) -> None:
        """Rotate log file if size exceeds max_file_size_mb.

        Rotates usage.jsonl -> usage.YYYY-MM-DD.jsonl
        Also cleans up files older than retention_days.
        """
        if not self.usage_file.exists():
            return

        # Check file size
        size_mb = self.usage_file.stat().st_size / (1024 * 1024)
        if size_mb < self.max_file_size_mb:
            return

        with self._lock:
            # Rotate: usage.jsonl -> usage.YYYY-MM-DD.jsonl
            timestamp = datetime.now().strftime("%Y-%m-%d")
            rotated_file = self.telemetry_dir / f"usage.{timestamp}.jsonl"

            # If rotated file already exists, append a counter
            counter = 1
            while rotated_file.exists():
                rotated_file = self.telemetry_dir / f"usage.{timestamp}.{counter}.jsonl"
                counter += 1

            # Rename current file
            self.usage_file.rename(rotated_file)

            # Clean up old files
            self._cleanup_old_files()

    def _cleanup_old_files(self) -> None:
        """Remove files older than retention_days."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for file in self.telemetry_dir.glob("usage.*.jsonl"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if mtime < cutoff:
                    file.unlink()
                    logger.debug(f"Deleted old telemetry file: {file.name}")
            except (OSError, ValueError):
                # File system errors - log but continue
                logger.debug(f"Failed to clean up telemetry file: {file.name}")

    def get_recent_entries(
        self,
        limit: int = 20,
        days: int | None = None,
    ) -> list[dict[str, Any]]:
        """Read recent telemetry entries.

        Args:
            limit: Maximum number of entries to return (default: 20)
            days: Only return entries from last N days (optional)

        Returns:
            List of telemetry entries (most recent first)

        """
        entries: list[dict[str, Any]] = []
        cutoff_time = datetime.utcnow() - timedelta(days=days) if days else None

        # Read all relevant files
        files = sorted(self.telemetry_dir.glob("usage*.jsonl"), reverse=True)

        for file in files:
            if not file.exists():
                continue

            try:
                with open(file, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            # Check timestamp if filtering by days
                            if cutoff_time:
                                ts = datetime.fromisoformat(entry["ts"].rstrip("Z"))
                                if ts < cutoff_time:
                                    continue
                            entries.append(entry)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            # Skip invalid entries
                            continue
            except OSError:
                # File read errors - log but continue
                logger.debug(f"Failed to read telemetry file: {file.name}")
                continue

        # Sort by timestamp (most recent first), using sequence number as
        # tiebreaker when timestamps are identical (can happen on platforms
        # with low datetime resolution, e.g. ~15ms on some Windows systems)
        entries.sort(key=lambda e: (e.get("ts", ""), e.get("seq", 0)), reverse=True)
        return entries[:limit]

    def get_stats(self, days: int = 30) -> dict[str, Any]:
        """Calculate telemetry statistics.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            Dictionary with statistics including:
            - total_calls: Total number of LLM calls
            - total_cost: Total cost in USD
            - total_tokens_input: Total input tokens
            - total_tokens_output: Total output tokens
            - cache_hits: Number of cache hits
            - cache_misses: Number of cache misses
            - cache_hit_rate: Cache hit rate as percentage
            - by_tier: Cost breakdown by tier
            - by_workflow: Cost breakdown by workflow
            - by_provider: Cost breakdown by provider

        """
        entries = self.get_recent_entries(limit=100000, days=days)

        if not entries:
            return {
                "total_calls": 0,
                "total_cost": 0.0,
                "total_tokens_input": 0,
                "total_tokens_output": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "cache_hit_rate": 0.0,
                "by_tier": {},
                "by_workflow": {},
                "by_provider": {},
            }

        # Aggregate stats
        total_cost = 0.0
        total_tokens_input = 0
        total_tokens_output = 0
        cache_hits = 0
        cache_misses = 0
        by_tier: dict[str, float] = {}
        by_workflow: dict[str, float] = {}
        by_provider: dict[str, float] = {}

        for entry in entries:
            cost = entry.get("cost", 0.0)
            tokens = entry.get("tokens", {})
            cache = entry.get("cache", {})
            tier = entry.get("tier", "unknown")
            workflow = entry.get("workflow", "unknown")
            provider = entry.get("provider", "unknown")

            total_cost += cost
            total_tokens_input += tokens.get("input", 0)
            total_tokens_output += tokens.get("output", 0)

            if cache.get("hit"):
                cache_hits += 1
            else:
                cache_misses += 1

            by_tier[tier] = by_tier.get(tier, 0.0) + cost
            by_workflow[workflow] = by_workflow.get(workflow, 0.0) + cost
            by_provider[provider] = by_provider.get(provider, 0.0) + cost

        total_calls = len(entries)
        cache_hit_rate = (cache_hits / total_calls * 100) if total_calls > 0 else 0.0

        return {
            "total_calls": total_calls,
            "total_cost": round(total_cost, 2),
            "total_tokens_input": total_tokens_input,
            "total_tokens_output": total_tokens_output,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_hit_rate": round(cache_hit_rate, 1),
            "by_tier": by_tier,
            "by_workflow": by_workflow,
            "by_provider": by_provider,
        }

    def calculate_savings(self, days: int = 30) -> dict[str, Any]:
        """Calculate actual savings vs all-PREMIUM baseline.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            Dictionary with savings calculation:
            - actual_cost: Actual cost with tier routing
            - baseline_cost: Cost if all calls used PREMIUM tier
            - savings: Dollar amount saved
            - savings_percent: Percentage saved
            - tier_distribution: Percentage of calls by tier
            - cache_savings: Additional savings from cache hits

        """
        entries = self.get_recent_entries(limit=100000, days=days)

        if not entries:
            return {
                "actual_cost": 0.0,
                "baseline_cost": 0.0,
                "savings": 0.0,
                "savings_percent": 0.0,
                "tier_distribution": {},
                "cache_savings": 0.0,
                "total_calls": 0,
            }

        # Calculate actual cost
        actual_cost = sum(e.get("cost", 0.0) for e in entries)

        # Calculate baseline cost (all PREMIUM)
        # Get average PREMIUM cost from actual data, or use standard rate
        premium_costs = [e.get("cost", 0.0) for e in entries if e.get("tier") == "PREMIUM"]
        avg_premium_cost = (sum(premium_costs) / len(premium_costs)) if premium_costs else 0.05
        baseline_cost = len(entries) * avg_premium_cost

        # Tier distribution
        tier_counts: dict[str, int] = {}
        for entry in entries:
            tier = entry.get("tier", "unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        total_calls = len(entries)
        tier_distribution = {
            tier: round(count / total_calls * 100, 1) for tier, count in tier_counts.items()
        }

        # Cache savings estimation
        cache_hits = sum(1 for e in entries if e.get("cache", {}).get("hit"))
        avg_cost_per_call = actual_cost / total_calls if total_calls > 0 else 0.0
        cache_savings = cache_hits * avg_cost_per_call

        savings = baseline_cost - actual_cost
        savings_percent = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

        return {
            "actual_cost": round(actual_cost, 2),
            "baseline_cost": round(baseline_cost, 2),
            "savings": round(savings, 2),
            "savings_percent": round(savings_percent, 1),
            "tier_distribution": tier_distribution,
            "cache_savings": round(cache_savings, 2),
            "total_calls": total_calls,
        }

    def reset(self) -> int:
        """Clear all telemetry data.

        Returns:
            Number of entries deleted

        """
        count = 0
        with self._lock:
            for file in self.telemetry_dir.glob("usage*.jsonl"):
                try:
                    # Count entries before deleting
                    with open(file, encoding="utf-8") as f:
                        count += sum(1 for line in f if line.strip())
                    file.unlink()
                except OSError:
                    # File system errors - log but continue
                    logger.debug(f"Failed to delete telemetry file: {file.name}")

        return count

    def get_cache_stats(self, days: int = 7) -> dict[str, Any]:
        """Get prompt caching statistics.

        Analyzes Anthropic prompt cache usage including:
        - Cache hit rate
        - Total cache reads and writes
        - Estimated cost savings from caching
        - Top workflows benefiting from cache

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            Dictionary with caching statistics:
            - hit_rate: Percentage of requests that used cache
            - total_reads: Total tokens read from cache
            - total_writes: Total tokens written to cache
            - savings: Estimated USD saved by caching
            - hit_count: Number of requests with cache hits
            - total_requests: Total requests analyzed
            - by_workflow: Cache stats by workflow

        Example:
            >>> tracker = UsageTracker.get_instance()
            >>> stats = tracker.get_cache_stats(days=7)
            >>> print(f"Cache hit rate: {stats['hit_rate']:.1%}")
            Cache hit rate: 65.3%
            >>> print(f"Savings: ${stats['savings']:.2f}")
            Savings: $12.45

        """
        entries = self.get_recent_entries(limit=100000, days=days)

        if not entries:
            return {
                "hit_rate": 0.0,
                "total_reads": 0,
                "total_writes": 0,
                "savings": 0.0,
                "hit_count": 0,
                "total_requests": 0,
                "by_workflow": {},
            }

        # Aggregate prompt cache stats
        hit_count = 0
        total_reads = 0
        total_writes = 0
        total_requests = len(entries)
        by_workflow: dict[str, dict[str, Any]] = {}

        for entry in entries:
            prompt_cache = entry.get("prompt_cache", {})

            # Check if entry has prompt cache data
            if prompt_cache.get("hit"):
                hit_count += 1

            # Accumulate tokens
            total_reads += prompt_cache.get("read_tokens", 0)
            total_writes += prompt_cache.get("creation_tokens", 0)

            # Per-workflow stats
            workflow = entry.get("workflow", "unknown")
            if workflow not in by_workflow:
                by_workflow[workflow] = {
                    "hits": 0,
                    "reads": 0,
                    "writes": 0,
                    "requests": 0,
                }

            wf_stats = by_workflow[workflow]
            wf_stats["requests"] += 1
            if prompt_cache.get("hit"):
                wf_stats["hits"] += 1
            wf_stats["reads"] += prompt_cache.get("read_tokens", 0)
            wf_stats["writes"] += prompt_cache.get("creation_tokens", 0)

        # Calculate hit rate
        hit_rate = (hit_count / total_requests) if total_requests > 0 else 0.0

        # Estimate savings (cache reads cost 90% less)
        # Assume Sonnet 4.5 pricing: $3.00/M input tokens
        # Cache reads: $0.30/M (90% discount)
        # Full price would be: $3.00/M
        # Savings per token: $2.70/M
        savings_per_token = 0.0000027  # $2.70 / 1M tokens
        savings = total_reads * savings_per_token

        # Calculate hit rates for workflows
        for wf_stats in by_workflow.values():
            wf_requests = wf_stats["requests"]
            wf_stats["hit_rate"] = (wf_stats["hits"] / wf_requests) if wf_requests > 0 else 0.0

        return {
            "hit_rate": round(hit_rate, 4),
            "total_reads": total_reads,
            "total_writes": total_writes,
            "savings": round(savings, 2),
            "hit_count": hit_count,
            "total_requests": total_requests,
            "by_workflow": by_workflow,
        }

    def export_to_dict(self, days: int | None = None) -> list[dict[str, Any]]:
        """Export all entries as list of dicts.

        Args:
            days: Only export entries from last N days (optional)

        Returns:
            List of telemetry entries

        """
        return self.get_recent_entries(limit=1000000, days=days)
