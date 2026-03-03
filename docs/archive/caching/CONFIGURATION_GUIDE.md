---
description: Caching Configuration Guide: Step-by-step tutorial with examples, best practices, and common patterns. Learn by doing with hands-on examples.
---

# Caching Configuration Guide

## Overview

Attune AI v3.8.0+ includes intelligent response caching to reduce API costs and improve performance. This guide helps you choose the right caching configuration for your needs.

## Quick Decision Tree

```
Do you want caching at all?
├─ NO → Set enable_cache=False
└─ YES → Continue...
    │
    Do you run identical prompts repeatedly?
    ├─ YES (testing, CI/CD, batch processing)
    │   └─ Use: Hash-only cache (default)
    │       • 100% hit rate on exact matches
    │       • ~5μs lookup time
    │       • Zero ML dependencies
    │
    └─ PARTIALLY (similar but not identical prompts)
        └─ Use: Hybrid cache
            • 70%+ hit rate on similar prompts
            • ~100ms lookup time (semantic search)
            • Requires sentence-transformers
```

## Cache Types Compared

### Hash-Only Cache (Default)

**Best for:**
- CI/CD pipelines running same tests
- Batch processing with identical inputs
- Development workflows with repeated operations
- Users who want zero ML dependencies

**Characteristics:**
- **Hit rate:** 100% on identical prompts, 0% otherwise
- **Lookup speed:** ~5μs per query
- **Memory:** <1MB for typical usage
- **Dependencies:** None (built-in Python only)
- **Storage:** `~/.empathy/cache/responses.json`

**Example:**
```python
from attune.cache import create_cache

# Explicit hash-only cache
cache = create_cache(cache_type="hash")

# Use with workflow
workflow = CodeReviewWorkflow(cache=cache, enable_cache=True)
```

**When it helps:**
```python
# Run 1: Review auth.py changes
result1 = await workflow.execute(diff=auth_diff)  # $0.0048 - Cache miss

# Run 2: Same diff (re-running test)
result2 = await workflow.execute(diff=auth_diff)  # $0.0024 - Cache hit! ✅

# Run 3: Different diff
result3 = await workflow.execute(diff=other_diff)  # $0.0048 - Cache miss
```

### Hybrid Cache (Hash + Semantic)

**Best for:**
- Interactive development with similar prompts
- Workflows analyzing related code sections
- Users willing to install ML dependencies
- Cost-sensitive production deployments

**Characteristics:**
- **Hit rate:** 70-90% on similar prompts
- **Lookup speed:** ~100ms (hash check + semantic search)
- **Memory:** ~500MB (sentence transformer model)
- **Dependencies:** `sentence-transformers`, `torch`
- **Storage:** `~/.empathy/cache/responses.json` + model cache

**Example:**
```python
from attune.cache import create_cache

# Hybrid cache with semantic matching
cache = create_cache(cache_type="hybrid", similarity_threshold=0.95)

workflow = SecurityAuditWorkflow(cache=cache, enable_cache=True)
```

**When it helps:**
```python
# Run 1: "Add authentication middleware"
result1 = await workflow.execute(prompt="Add authentication middleware")  # $0.10 - Miss

# Run 2: "Add logging middleware" (similar structure)
result2 = await workflow.execute(prompt="Add logging middleware")  # $0.05 - Semantic hit! ✅

# Run 3: "Implement OAuth flow" (different task)
result3 = await workflow.execute(prompt="Implement OAuth flow")  # $0.10 - Miss
```

**Installation:**
```bash
# Install with cache dependencies
pip install attune-ai[cache]

# Or install dependencies separately
pip install sentence-transformers torch
```

## When to Enable/Disable Caching

### ✅ Enable Caching (default)

**Good for:**
1. **Development workflows** - Repeated operations during debugging
2. **CI/CD pipelines** - Same tests run multiple times
3. **Batch processing** - Processing similar items in sequence
4. **Cost-sensitive production** - Reduce API costs significantly
5. **Time-sensitive operations** - Faster response on cache hits

**Example use case:**
```python
# Development: Running health checks repeatedly
workflow = HealthCheckWorkflow(enable_cache=True)  # default

# First check: Full analysis
result1 = await workflow.execute(project_path="./src")  # 45s, $0.15

# Second check (5 minutes later): Cached results
result2 = await workflow.execute(project_path="./src")  # 2s, $0.075 ✅
```

### ❌ Disable Caching

**Good for:**
1. **Non-deterministic outputs desired** - Want fresh analysis each time
2. **Rapidly changing inputs** - Code changes between runs
3. **One-time operations** - Never running same analysis twice
4. **Debugging cache issues** - Isolating cache-related bugs
5. **Memory-constrained environments** - Every MB counts

**Example use case:**
```python
# Production: Real-time code review on PR events
workflow = CodeReviewWorkflow(enable_cache=False)

# Each PR gets fresh analysis (no stale cached results)
for pr in new_pull_requests:
    result = await workflow.execute(diff=pr.diff)  # Always fresh
```

## Configuration Options

### TTL (Time-to-Live)

Controls how long cached responses remain valid.

**Default:** 24 hours

**When to adjust:**

| TTL | Use Case | Why |
|-----|----------|-----|
| 1 hour | CI/CD pipelines | Short-lived test runs |
| 24 hours (default) | Development | Balance freshness vs cost |
| 7 days | Stable codebases | Maximize cost savings |
| 30 days | Documentation gen | Docs rarely change |

**Example:**
```python
from attune.cache import create_cache

# Short TTL for CI/CD
cache = create_cache(cache_type="hash", ttl_hours=1)

# Long TTL for stable projects
cache = create_cache(cache_type="hash", ttl_hours=168)  # 7 days
```

### Similarity Threshold (Hybrid Only)

Controls how similar prompts must be for semantic cache hits.

**Default:** 0.95 (95% similarity required)

**When to adjust:**

| Threshold | Hit Rate | Risk | Use Case |
|-----------|----------|------|----------|
| 0.90 | Higher | More false positives | Exploratory development |
| 0.95 (default) | Balanced | Acceptable | General purpose |
| 0.98 | Lower | Very conservative | Production critical paths |

**Example:**
```python
# More aggressive caching (higher hit rate)
cache = create_cache(cache_type="hybrid", similarity_threshold=0.90)

# Conservative caching (lower hit rate, safer)
cache = create_cache(cache_type="hybrid", similarity_threshold=0.98)
```

**Similarity examples:**
```python
# 0.96 similarity (would hit with default 0.95 threshold)
"Add authentication middleware"
"Add logging middleware"

# 0.88 similarity (would miss with default 0.95 threshold)
"Add authentication"
"Implement OAuth flow"

# 1.0 similarity (exact match - both caches hit)
"def calculate_total(items):"
"def calculate_total(items):"
```

## Per-Workflow Configuration

You can enable/disable caching per workflow instance:

```python
from attune.cache import create_cache

# Shared cache instance
cache = create_cache(cache_type="hybrid")

# Workflow 1: Caching enabled
security = SecurityAuditWorkflow(cache=cache, enable_cache=True)

# Workflow 2: Caching disabled (always fresh)
code_review = CodeReviewWorkflow(cache=cache, enable_cache=False)

# Both use same cache, but code_review bypasses it
```

## Cache Statistics

Monitor cache effectiveness:

```python
workflow = HealthCheckWorkflow(cache=cache, enable_cache=True)
result = await workflow.execute(project_path="./src")

# Check cache metrics
print(f"Cache hit rate: {result.cost_report.cache_hit_rate:.1f}%")
print(f"Cache hits: {result.cost_report.cache_hits}")
print(f"Cache misses: {result.cost_report.cache_misses}")
print(f"Savings from cache: ${result.cost_report.savings_from_cache:.4f}")

# Check overall cache stats
stats = cache.get_stats()
print(f"Total hits: {stats.hits}")
print(f"Total misses: {stats.misses}")
print(f"Overall hit rate: {stats.hit_rate:.1f}%")
```

## Common Patterns

### Pattern 1: Development with Auto-Setup

```python
# Auto-creates cache on first use (prompts for ML dependencies)
workflow = CodeReviewWorkflow(enable_cache=True)  # No explicit cache

# Framework handles cache setup automatically
result = await workflow.execute(diff=my_diff)
```

### Pattern 2: Shared Cache Across Workflows

```python
from attune.cache import create_cache

# Create cache once
cache = create_cache(cache_type="hash")

# Share across all workflows (more efficient)
security = SecurityAuditWorkflow(cache=cache, enable_cache=True)
code_review = CodeReviewWorkflow(cache=cache, enable_cache=True)
health_check = HealthCheckWorkflow(cache=cache, enable_cache=True)

# All workflows benefit from shared cache
```

### Pattern 3: Testing with Isolated Cache

```python
from attune.cache import HashOnlyCache

# Create temporary cache for testing
test_cache = HashOnlyCache(ttl_hours=1)

workflow = BugPredictionWorkflow(cache=test_cache, enable_cache=True)

# Run test
result = await workflow.execute(path="./test_data")

# Clear cache after test
test_cache.clear()
```

### Pattern 4: Production with Hybrid Cache

```python
from attune.cache import create_cache

# Production setup with hybrid cache
cache = create_cache(
    cache_type="hybrid",
    similarity_threshold=0.95,
    ttl_hours=24
)

# Use with all production workflows
workflows = [
    SecurityAuditWorkflow(cache=cache, enable_cache=True),
    PerformanceAuditWorkflow(cache=cache, enable_cache=True),
    DependencyCheckWorkflow(cache=cache, enable_cache=True),
]

# Monitor cache effectiveness
for workflow in workflows:
    result = await workflow.execute(...)
    logger.info(f"{workflow.name}: {result.cost_report.cache_hit_rate:.1f}% hit rate")
```

## Cache Maintenance

### Clear Cache

```python
# Clear all cached responses
cache.clear()

# Useful for:
# - Testing (ensure cold cache)
# - After major code changes
# - Resetting cost benchmarks
```

### Cache Location

Default cache location: `~/.empathy/cache/responses.json`

```bash
# View cache size
du -h ~/.empathy/cache/responses.json

# Backup cache
cp ~/.empathy/cache/responses.json ~/.empathy/cache/responses.backup

# Delete cache (will recreate on next use)
rm ~/.empathy/cache/responses.json
```

### Expired Entry Cleanup

Cache automatically removes expired entries on load.

```python
# Manual cleanup (if needed)
from attune.cache.storage import CacheStorage

storage = CacheStorage()
storage.load()  # Automatically removes expired entries
```

## Troubleshooting

### Cache Not Working

**Symptom:** 0% cache hit rate on repeated runs

**Solutions:**
1. Verify caching is enabled: `enable_cache=True`
2. Check cache instance is provided: `cache=create_cache()`
3. Ensure prompts are identical (hash cache) or similar (hybrid cache)
4. Verify TTL hasn't expired: Check `ttl_hours` setting

### Low Hit Rate (Hybrid Cache)

**Symptom:** <50% hit rate with hybrid cache

**Solutions:**
1. Lower similarity threshold: `similarity_threshold=0.90`
2. Check if prompts are truly similar (semantic meaning)
3. Verify sentence-transformers is installed correctly
4. Consider if hash-only cache is better fit

### High Memory Usage

**Symptom:** Process using >500MB memory

**Solutions:**
1. Switch to hash-only cache: `cache_type="hash"`
2. Reduce TTL to evict entries faster: `ttl_hours=1`
3. Clear cache periodically: `cache.clear()`
4. Disable caching if not needed: `enable_cache=False`

## Performance Benchmarks

Based on v3.8.0 benchmarks:

| Cache Type | Lookup Time | Memory | Hit Rate (Identical) | Hit Rate (Similar) |
|------------|-------------|--------|----------------------|-------------------|
| Hash-only  | ~5μs        | <1MB   | 100%                 | 0%                |
| Hybrid     | ~100ms      | ~500MB | 100%                 | 70-90%            |

**Cost savings examples:**

```
Hash-only cache (12 workflows, repeated runs):
- Run 1: $0.856403 (cold cache)
- Run 2: $0.428202 (50% savings on identical prompts)

Hybrid cache (similar prompts):
- Without cache: $50/week
- With cache (70% hit rate): $15/week (70% savings)
```

## Best Practices

1. ✅ **Enable caching by default** - Significant cost savings with minimal overhead
2. ✅ **Use hash-only for CI/CD** - Fast, deterministic, zero dependencies
3. ✅ **Use hybrid for development** - Better hit rates on similar tasks
4. ✅ **Share cache instances** - More efficient than per-workflow caches
5. ✅ **Monitor hit rates** - Track effectiveness with `cost_report.cache_hit_rate`
6. ✅ **Clear cache when benchmarking** - Ensure accurate measurements
7. ⚠️ **Adjust TTL for your workflow** - Balance freshness vs cost
8. ⚠️ **Lower threshold cautiously** - More hits but risk of stale results

## Related Documentation

- [ADAPTIVE_WORKFLOWS.md](ADAPTIVE_WORKFLOWS.md) - Understanding deterministic vs adaptive workflows
- [../../CHANGELOG.md](../../CHANGELOG.md#380---2026-01-06) - v3.8.0 caching features
- [../../README.md](../../README.md) - Quick start guide

## Questions?

If you have questions about caching configuration:
1. Check benchmarks: `python benchmark_caching_simple.py`
2. Review examples: `tests/integration/test_cache_integration.py`
3. File issue: [GitHub Issues](https://github.com/empathy-ai/attune-ai/issues)
