"""Usage Tracker for Attune AI Telemetry.

Privacy-first, local-only tracking of LLM calls to measure actual cost savings.
All data stored locally in ~/.attune/telemetry/ as JSON Lines format.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import hashlib
import hmac
import json
import logging
import threading
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Magic limit sentinel — callers that need "all entries" use this
_ALL_ENTRIES = 1_000_000


class UsageTracker:
    """Privacy-first local telemetry tracker.

    Tracks LLM calls to JSON Lines format with automatic rotation
    and 90-day retention. Thread-safe with buffered writes.

    Write buffering: entries are held in memory and flushed to disk in
    batches (default: 50 entries), reducing per-call I/O overhead by ~50x.
    A pre-aggregated daily summary file enables O(days) stats queries
    instead of O(all-entries) full scans.

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
        buffer_size: int = 50,
    ):
        """Initialize UsageTracker.

        Args:
            telemetry_dir: Directory for telemetry files.
                          Defaults to ~/.attune/telemetry/
            retention_days: Days to retain telemetry data (default: 90)
            max_file_size_mb: Max size in MB before rotation (default: 10)
            buffer_size: Number of entries to buffer before flushing to
                        disk (default: 50). Higher values reduce I/O at
                        the cost of potentially losing buffered entries
                        on unexpected process termination.

        """
        self.telemetry_dir = telemetry_dir or Path.home() / ".attune" / "telemetry"
        self.retention_days = retention_days
        self.max_file_size_mb = max_file_size_mb
        self.buffer_size = buffer_size
        self.usage_file = self.telemetry_dir / "usage.jsonl"
        self._summary_file = self.telemetry_dir / "usage_summary.json"

        # In-memory write buffer — reduces disk I/O by batching writes
        self._buffer: list[dict[str, Any]] = []
        # Pre-aggregated daily stats keyed by "YYYY-MM-DD"
        self._daily_summary: dict[str, dict[str, Any]] = {}

        # Create directory if needed (gracefully handle permission errors)
        try:
            self.telemetry_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Can't create directory - telemetry will be disabled
            logger.debug("Failed to create telemetry directory: %s", self.telemetry_dir)

        # Load or build the daily summary (enables fast get_stats() queries)
        self._load_summary()

    @classmethod
    def get_instance(cls, **kwargs: Any) -> "UsageTracker":
        """Get singleton instance of UsageTracker.

        Args:
            **kwargs: Arguments passed to __init__ if creating new instance

        Returns:
            Singleton UsageTracker instance

        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(**kwargs)
        return cls._instance

    # =========================================================================
    # Shared helpers
    # =========================================================================

    @staticmethod
    def _empty_day() -> dict[str, Any]:
        """Return a zero-valued day-summary bucket."""
        return {
            "calls": 0,
            "cost": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "by_tier": {},
            "by_workflow": {},
            "by_provider": {},
        }

    @staticmethod
    def _accumulate_entry(acc: dict[str, Any], entry: dict[str, Any]) -> None:
        """Add one raw entry's metrics into an accumulator dict.

        Works with both day-summary buckets (short keys like ``calls``)
        and public stats dicts (long keys like ``total_calls``).  Callers
        must ensure the accumulator uses short keys matching ``_empty_day``.
        """
        cost = entry.get("cost", 0.0)
        acc["calls"] += 1
        acc["cost"] += cost
        tokens = entry.get("tokens", {})
        acc["tokens_in"] += tokens.get("input", 0)
        acc["tokens_out"] += tokens.get("output", 0)
        if entry.get("cache", {}).get("hit"):
            acc["cache_hits"] += 1
        else:
            acc["cache_misses"] += 1
        tier = entry.get("tier", "unknown")
        acc["by_tier"][tier] = acc["by_tier"].get(tier, 0.0) + cost
        wf = entry.get("workflow", "unknown")
        acc["by_workflow"][wf] = acc["by_workflow"].get(wf, 0.0) + cost
        prov = entry.get("provider", "unknown")
        acc["by_provider"][prov] = acc["by_provider"].get(prov, 0.0) + cost

    def _iter_jsonl(self, path: Path) -> Iterator[dict[str, Any]]:
        """Yield parsed dicts from a JSONL file, skipping invalid lines."""
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return

    @staticmethod
    def _utcnow() -> datetime:
        """Return current UTC time (timezone-aware)."""
        return datetime.now(timezone.utc)

    @staticmethod
    def _utcnow_iso() -> str:
        """Return current UTC time as ISO 8601 string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # =========================================================================
    # Summary file — fast stats without full JSONL scans
    # =========================================================================

    def _load_summary(self) -> None:
        """Load pre-aggregated daily summary from disk.

        If no summary file exists (e.g. first run after upgrade), rebuilds
        it from existing JSONL files. This is a one-time O(entries) cost;
        subsequent loads are O(days).
        """
        if self._summary_file.exists():
            try:
                with open(self._summary_file, encoding="utf-8") as f:
                    data = json.load(f)
                self._daily_summary = data.get("days", {})
                return
            except (OSError, json.JSONDecodeError):
                self._daily_summary = {}

        # No summary file — build from existing disk data (migration path)
        self._rebuild_summary_from_disk()

    def _rebuild_summary_from_disk(self) -> None:
        """Scan all JSONL files to build the daily summary.

        Called once when no summary file exists. Result is saved to disk
        so subsequent runs use the fast O(days) load path.
        """
        for file in sorted(self.telemetry_dir.glob("usage*.jsonl")):
            for entry in self._iter_jsonl(file):
                self._update_summary_entry(entry)

        if self._daily_summary:
            self._save_summary()

    def _save_summary(self) -> None:
        """Persist daily summary to disk atomically (best-effort)."""
        try:
            data = {
                "v": "1.0",
                "updated": self._utcnow_iso(),
                "days": self._daily_summary,
            }
            tmp = self._summary_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, separators=(",", ":"))
            tmp.replace(self._summary_file)
        except OSError:
            pass  # Best effort — stats still work via slow path

    def _update_summary_entry(self, entry: dict[str, Any]) -> None:
        """Aggregate a single entry into the in-memory daily summary."""
        date = entry.get("ts", "")[:10]  # "YYYY-MM-DD"
        if not date or len(date) != 10:
            return
        day = self._daily_summary.setdefault(date, self._empty_day())
        self._accumulate_entry(day, entry)

    def _update_summary(self, entries: list[dict[str, Any]]) -> None:
        """Aggregate multiple entries into the in-memory daily summary.

        Args:
            entries: Entries to aggregate (already flushed to disk)

        """
        for entry in entries:
            self._update_summary_entry(entry)

    # =========================================================================
    # Write path — buffered, batch I/O
    # =========================================================================

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

        Entries are buffered in memory and flushed to disk in batches
        (see buffer_size). This eliminates per-call disk I/O overhead.

        Args:
            workflow: Workflow name (e.g., "code-review")
            stage: Stage name (e.g., "analysis"), optional
            tier: Model tier (CHEAP, CAPABLE, PREMIUM)
            model: Model ID (e.g., "claude-sonnet-4.5")
            provider: Provider name (anthropic)
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
            "ts": self._utcnow_iso(),
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

        # Buffer entry (no disk I/O per-call)
        should_flush = False
        with self._lock:
            self._buffer.append(entry)
            should_flush = len(self._buffer) >= self.buffer_size

        if should_flush:
            try:
                self.flush()
                self._rotate_if_needed()
            except OSError as e:
                # File system errors - log but don't crash the workflow
                logger.debug("Failed to flush telemetry buffer: %s", e)
            except Exception as ex:  # noqa: BLE001
                # INTENTIONAL: Telemetry failures should never crash the workflow
                logger.debug("Unexpected error flushing telemetry: %s", ex)

    def flush(self) -> int:
        """Flush buffered entries to disk and update the daily summary.

        Returns:
            Number of entries written to disk. Zero if buffer was empty.

        Raises:
            OSError: If writing to disk fails. Entries are returned to the
                    buffer so no data is lost.

        """
        with self._lock:
            if not self._buffer:
                return 0
            entries = self._buffer[:]
            self._buffer.clear()

        try:
            with open(self.usage_file, "a", encoding="utf-8") as f:
                for entry in entries:
                    json.dump(entry, f, separators=(",", ":"))
                    f.write("\n")
        except OSError:
            # Restore entries to buffer so they are not lost
            with self._lock:
                self._buffer = entries + self._buffer
            raise

        # Update in-memory summary and persist it (after successful disk write)
        with self._lock:
            self._update_summary(entries)
            self._save_summary()

        return len(entries)

    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID with HMAC-SHA256 for privacy.

        Uses a deployment-specific secret to prevent rainbow table
        attacks. Falls back to a default key if no secret is configured.

        Args:
            user_id: User identifier to hash

        Returns:
            First 16 characters of HMAC-SHA256 hex digest

        """
        from attune.config.env_compat import get_attune_env

        secret = (get_attune_env("TELEMETRY_SECRET") or "attune-default-telemetry-key").encode()
        return hmac.new(secret, user_id.encode(), hashlib.sha256).hexdigest()[:16]

    def _write_entry(self, entry: dict[str, Any]) -> None:
        """Write a single entry directly to disk (bypasses buffer).

        Prefer track_llm_call() for normal usage; use this only when
        you need guaranteed immediate persistence (e.g. tests).

        Args:
            entry: Dictionary entry to write

        """
        with self._lock:
            with open(self.usage_file, "a", encoding="utf-8") as f:
                json.dump(entry, f, separators=(",", ":"))
                f.write("\n")

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
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            rotated_file = self.telemetry_dir / f"usage.{timestamp}.jsonl"

            # If rotated file already exists, append a counter
            counter = 1
            while rotated_file.exists():
                rotated_file = self.telemetry_dir / f"usage.{timestamp}.{counter}.jsonl"
                counter += 1

            # Rename current file
            self.usage_file.replace(rotated_file)

            # Clean up old files
            self._cleanup_old_files()

    def _cleanup_old_files(self) -> None:
        """Remove files older than retention_days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        for file in self.telemetry_dir.glob("usage.*.jsonl"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    file.unlink()
                    logger.debug("Deleted old telemetry file: %s", file.name)
            except (OSError, ValueError):
                logger.debug("Failed to clean up telemetry file: %s", file.name)

    # =========================================================================
    # Read path
    # =========================================================================

    def get_recent_entries(
        self,
        limit: int = 20,
        days: int | None = None,
    ) -> list[dict[str, Any]]:
        """Read recent telemetry entries (disk + in-memory buffer).

        Args:
            limit: Maximum number of entries to return (default: 20)
            days: Only return entries from last N days (optional)

        Returns:
            List of telemetry entries (most recent first)

        """
        entries: list[dict[str, Any]] = []
        cutoff_time = self._utcnow() - timedelta(days=days) if days else None

        # Read all relevant files from disk
        files = sorted(self.telemetry_dir.glob("usage*.jsonl"), reverse=True)

        for file in files:
            for entry in self._iter_jsonl(file):
                if cutoff_time:
                    try:
                        ts = datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
                        if ts < cutoff_time:
                            continue
                    except (KeyError, ValueError):
                        continue
                entries.append(entry)

        # Include in-memory buffer (not yet flushed to disk)
        with self._lock:
            buffer_snapshot = list(self._buffer)

        for entry in buffer_snapshot:
            if cutoff_time:
                try:
                    ts = datetime.fromisoformat(entry["ts"].rstrip("Z")).replace(
                        tzinfo=timezone.utc
                    )
                    if ts < cutoff_time:
                        continue
                except (KeyError, ValueError):
                    continue
            entries.append(entry)

        # Sort by timestamp (most recent first), using sequence number as
        # tiebreaker when timestamps are identical (can happen on platforms
        # with low datetime resolution, e.g. ~15ms on some Windows systems)
        entries.sort(key=lambda e: (e.get("ts", ""), e.get("seq", 0)), reverse=True)
        return entries[:limit]

    def get_stats(self, days: int = 30) -> dict[str, Any]:
        """Calculate telemetry statistics.

        Uses the pre-aggregated daily summary for O(days) performance
        when available. Falls back to a full JSONL scan on first run.

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
        cutoff_dt = self._utcnow() - timedelta(days=days)
        cutoff_date = cutoff_dt.strftime("%Y-%m-%d")

        # Internal accumulator uses short keys matching _empty_day()
        acc = self._empty_day()

        with self._lock:
            summary_snapshot = dict(self._daily_summary)
            buffer_snapshot = list(self._buffer)

        if summary_snapshot:
            # Fast path: O(days) aggregation from pre-built daily summary
            for date, day in summary_snapshot.items():
                if date >= cutoff_date:
                    acc["calls"] += day["calls"]
                    acc["cost"] += day["cost"]
                    acc["tokens_in"] += day["tokens_in"]
                    acc["tokens_out"] += day["tokens_out"]
                    acc["cache_hits"] += day["cache_hits"]
                    acc["cache_misses"] += day["cache_misses"]
                    for sub in ("by_tier", "by_workflow", "by_provider"):
                        for k, v in day[sub].items():
                            acc[sub][k] = acc[sub].get(k, 0.0) + v
        else:
            # Slow path: full JSONL scan (first run before summary is built)
            disk_entries = self.get_recent_entries(limit=_ALL_ENTRIES, days=days)
            # get_recent_entries already includes buffer, skip buffer below
            buffer_snapshot = []
            for entry in disk_entries:
                self._accumulate_entry(acc, entry)

        # Include buffered entries not yet reflected in the summary
        for entry in buffer_snapshot:
            try:
                ts = datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if ts < cutoff_dt:
                continue
            self._accumulate_entry(acc, entry)

        # Build public-facing result with long key names
        result: dict[str, Any] = {
            "total_calls": acc["calls"],
            "total_cost": acc["cost"],
            "total_tokens_input": acc["tokens_in"],
            "total_tokens_output": acc["tokens_out"],
            "cache_hits": acc["cache_hits"],
            "cache_misses": acc["cache_misses"],
            "cache_hit_rate": 0.0,
            "by_tier": acc["by_tier"],
            "by_workflow": acc["by_workflow"],
            "by_provider": acc["by_provider"],
        }

        if not result["total_calls"]:
            return result

        result["cache_hit_rate"] = round(result["cache_hits"] / result["total_calls"] * 100, 1)
        result["total_cost"] = round(result["total_cost"], 2)
        return result

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
        entries = self.get_recent_entries(limit=_ALL_ENTRIES, days=days)

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
        """Clear all telemetry data (buffer + disk files).

        Returns:
            Number of entries deleted

        """
        count = 0
        with self._lock:
            # Count and clear the in-memory buffer first
            count += len(self._buffer)
            self._buffer.clear()
            self._daily_summary.clear()

        # Delete disk files
        for file in self.telemetry_dir.glob("usage*.jsonl"):
            try:
                # Count entries before deleting
                with open(file, encoding="utf-8") as f:
                    count += sum(1 for line in f if line.strip())
                file.unlink()
            except OSError:
                logger.debug("Failed to delete telemetry file: %s", file.name)

        # Remove summary file
        if self._summary_file.exists():
            try:
                self._summary_file.unlink()
            except OSError:
                pass

        return count

    def get_cache_stats(self, days: int = 7) -> dict[str, Any]:
        """Get prompt caching statistics.

        Analyzes Anthropic prompt cache usage including cache hit rate,
        total cache reads/writes, estimated cost savings, and top
        workflows benefiting from cache.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            Dictionary with caching statistics

        """
        entries = self.get_recent_entries(limit=_ALL_ENTRIES, days=days)

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

        # Single-pass aggregation of prompt cache stats + savings
        from attune.models.registry import get_pricing_for_model

        hit_count = 0
        total_reads = 0
        total_writes = 0
        total_requests = len(entries)
        total_savings = 0.0
        by_workflow: dict[str, dict[str, Any]] = {}
        # Cache pricing lookups by model to avoid repeated calls
        pricing_cache: dict[str, dict[str, float] | None] = {}

        for entry in entries:
            prompt_cache = entry.get("prompt_cache", {})

            if prompt_cache.get("hit"):
                hit_count += 1

            read_tokens = prompt_cache.get("read_tokens", 0)
            total_reads += read_tokens
            total_writes += prompt_cache.get("creation_tokens", 0)

            # Compute savings inline (avoids second pass)
            if read_tokens > 0:
                model_id = entry.get("model", "")
                if model_id not in pricing_cache:
                    pricing_cache[model_id] = get_pricing_for_model(model_id) if model_id else None
                pricing = pricing_cache[model_id]
                cost_per_token = (pricing["input"] if pricing else 3.00) / 1_000_000
                total_savings += read_tokens * cost_per_token * 0.9

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

        # Calculate hit rates for workflows
        for wf_stats in by_workflow.values():
            wf_requests = wf_stats["requests"]
            wf_stats["hit_rate"] = (wf_stats["hits"] / wf_requests) if wf_requests > 0 else 0.0

        hit_rate = (hit_count / total_requests) if total_requests > 0 else 0.0

        return {
            "hit_rate": round(hit_rate, 4),
            "total_reads": total_reads,
            "total_writes": total_writes,
            "savings": round(total_savings, 2),
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
        return self.get_recent_entries(limit=_ALL_ENTRIES, days=days)
