---
description: Caching Quick Reference API reference: One-page reference for common caching scenarios. ## TL;DR # Default (recommended for most users) wor
---

# Caching Quick Reference

One-page reference for common caching scenarios.

## TL;DR

```python
# Default (recommended for most users)
workflow = CodeReviewWorkflow(enable_cache=True)

# That's it! Framework handles everything else.
```

## Common Scenarios

### Scenario 1: CI/CD Pipeline

**Goal:** Cache test runs, zero dependencies

```python
from attune.cache import create_cache

cache = create_cache(cache_type="hash", ttl_hours=1)
workflow = TestGenerationWorkflow(cache=cache, enable_cache=True)

# First run: $0.05 (cache miss)
# Second run: $0.025 (cache hit - 50% savings)
```

### Scenario 2: Development Workflow

**Goal:** Cache similar prompts, maximize savings

```bash
# Install ML dependencies once
pip install attune-ai[cache]
```

```python
from attune.cache import create_cache

cache = create_cache(cache_type="hybrid", similarity_threshold=0.95)
workflow = SecurityAuditWorkflow(cache=cache, enable_cache=True)

# "Add auth middleware": $0.10 (miss)
# "Add logging middleware": $0.05 (semantic hit - 50% savings)
```

### Scenario 3: Batch Processing

**Goal:** Process 100 similar files efficiently

```python
from attune.cache import create_cache

cache = create_cache(cache_type="hybrid")
workflow = DocumentGenerationWorkflow(cache=cache, enable_cache=True)

for file in files:
    result = await workflow.execute(source_code=file.read())
    # First file: Full cost
    # Similar files: 70%+ savings from semantic caching
```

### Scenario 4: Disable Caching

**Goal:** Always get fresh results

```python
workflow = CodeReviewWorkflow(enable_cache=False)

# No caching - fresh analysis every time
```

### Scenario 5: Testing/Debugging

**Goal:** Isolated cache, easy cleanup

```python
from attune.cache import HashOnlyCache

test_cache = HashOnlyCache(ttl_hours=1)
workflow = BugPredictionWorkflow(cache=test_cache, enable_cache=True)

# Run tests...
result = await workflow.execute(path="./test_data")

# Cleanup
test_cache.clear()
```

## Cache Types at a Glance

| Feature | Hash-Only | Hybrid |
|---------|-----------|--------|
| **Hit rate (identical)** | 100% | 100% |
| **Hit rate (similar)** | 0% | 70-90% |
| **Lookup speed** | ~5μs | ~100ms |
| **Memory** | <1MB | ~500MB |
| **Dependencies** | None | sentence-transformers |
| **Install** | Built-in | `pip install attune-ai[cache]` |
| **Best for** | CI/CD, testing | Development, production |

## Configuration Cheat Sheet

```python
from attune.cache import create_cache

# Hash-only (default)
cache = create_cache(cache_type="hash")

# Hybrid with custom threshold
cache = create_cache(
    cache_type="hybrid",
    similarity_threshold=0.95  # 90-98 range
)

# Custom TTL
cache = create_cache(
    cache_type="hash",
    ttl_hours=24  # Default: 24 hours
)

# Use with workflow
workflow = YourWorkflow(cache=cache, enable_cache=True)
```

## Monitoring Cache Effectiveness

```python
result = await workflow.execute(...)

# Check cache performance
print(f"Hit rate: {result.cost_report.cache_hit_rate:.1f}%")
print(f"Savings: ${result.cost_report.savings_from_cache:.4f}")
```

## When to Use Each Type

### Use Hash-Only When:
- ✅ Running CI/CD pipelines (same tests repeatedly)
- ✅ Batch processing identical items
- ✅ Testing with fixed inputs
- ✅ Zero dependencies required
- ✅ Memory-constrained environments

### Use Hybrid When:
- ✅ Interactive development (similar prompts)
- ✅ Processing related code sections
- ✅ Willing to install ML dependencies
- ✅ Cost optimization is priority
- ✅ Have 500MB+ memory available

### Disable Caching When:
- ✅ Want fresh analysis every time
- ✅ Inputs change rapidly
- ✅ One-time operations
- ✅ Debugging cache issues

## TTL Guidelines

| TTL | Use Case |
|-----|----------|
| 1 hour | CI/CD pipelines |
| 6 hours | Active development |
| 24 hours (default) | General purpose |
| 7 days | Stable projects |
| 30 days | Documentation, rarely changing code |

## Cost Savings Examples

### Example 1: Development Workflow (Daily Use)

```
Without cache:
- 20 security audits/day × $0.12 = $2.40/day
- Monthly: $72

With hash-only cache (30% hit rate):
- Monthly: $50.40 (30% savings)

With hybrid cache (70% hit rate):
- Monthly: $21.60 (70% savings) ✅
```

### Example 2: CI/CD Pipeline

```
Without cache:
- 50 test runs/day × $0.05 = $2.50/day
- Monthly: $75

With hash-only cache (100% hit rate after first run):
- Monthly: $37.50 (50% savings) ✅
```

## Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| 0% hit rate | Verify `enable_cache=True`, prompts are identical/similar |
| Low hit rate (<50%) | Lower similarity threshold to 0.90, or use hash-only |
| High memory | Switch to hash-only cache |
| ImportError | Install ML dependencies: `pip install attune-ai[cache]` |
| Stale results | Lower TTL, or clear cache: `cache.clear()` |

## File Locations

```bash
# Cache storage
~/.empathy/cache/responses.json

# View cache size
du -h ~/.empathy/cache/responses.json

# Clear cache (will recreate on next use)
rm ~/.empathy/cache/responses.json
```

## API Quick Reference

```python
# Create cache
from attune.cache import create_cache
cache = create_cache(cache_type="hash")  # or "hybrid"

# Use with workflow
workflow = YourWorkflow(cache=cache, enable_cache=True)

# Check stats
stats = cache.get_stats()
print(f"Hit rate: {stats.hit_rate:.1f}%")

# Clear cache
cache.clear()

# Get size info
info = cache.size_info()
print(f"Entries: {info['entries']}, Size: {info['estimated_mb']:.2f} MB")
```

## Decision Tree

```
┌─ Need caching?
│
├─ NO → enable_cache=False
│
└─ YES
    │
    ├─ Run identical prompts repeatedly? (CI/CD, testing)
    │   └─ YES → cache_type="hash"
    │
    └─ Run similar prompts? (development, batch)
        └─ YES → cache_type="hybrid"
            │
            ├─ Want aggressive caching?
            │   └─ similarity_threshold=0.90
            │
            └─ Want conservative caching?
                └─ similarity_threshold=0.98
```

## Performance Numbers (v3.8.0)

**Hash-only cache:**
- Lookup: ~5μs
- Memory: <1MB
- Hit rate: 100% (identical), 0% (different)

**Hybrid cache:**
- Lookup: ~100ms
- Memory: ~500MB
- Hit rate: 100% (identical), 70-90% (similar)

**Cost savings (12 workflows):**
- Without cache: $0.856/run
- With cache (Run 2): $0.428/run (50% savings)

## Next Steps

1. **Quick test:** Run `python benchmark_caching_simple.py` (2-3 min)
2. **Full benchmark:** Run `python benchmark_caching.py` (15-20 min)
3. **Read detailed guide:** [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
4. **Understand adaptive workflows:** [ADAPTIVE_WORKFLOWS.md](ADAPTIVE_WORKFLOWS.md)

## Need Help?

- 📖 Full docs: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- 🧪 Examples: `tests/integration/test_cache_integration.py`
- 🐛 Issues: [GitHub](https://github.com/empathy-ai/attune-ai/issues)
