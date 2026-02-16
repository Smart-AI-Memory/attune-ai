---
description: Hybrid Caching Implementation Plan - v3.8.0: **Version:** 3.8.0 **Created:** 2026-01-06 **Status:** 📋 Planning Complete, Ready for Implementation --- ## Executi
---

# Hybrid Caching Implementation Plan - v3.8.0

**Version:** 3.8.0
**Created:** 2026-01-06
**Status:** 📋 Planning Complete, Ready for Implementation

---

## Executive Summary

Implement hybrid response caching (hash-based + semantic similarity) to reduce API costs by 70% while maintaining offline capability and zero-config user experience.

**Key Metrics:**
- **Target cost reduction:** 70% on cached workflows
- **Cache hit rate goal:** 70-75% (combined hash + semantic)
- **Performance target:** <100ms cache lookup overhead
- **Storage:** In-memory + persistent disk cache
- **User experience:** Zero-config with one-time opt-in prompt

---

## Architecture Overview

### **Three-Tier Caching Strategy**

```
┌─────────────────────────────────────────────────────────┐
│                   Workflow Execution                     │
│                  (code-review, etc.)                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Cache Manager (Smart Router)                │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 1. Hash Cache (Fast Path) - 1-5μs              │    │
│  │    └─> Exact match → Return cached response     │    │
│  │                                                  │    │
│  │ 2. Semantic Cache (Smart Path) - 10-100ms       │    │
│  │    └─> Similarity > 95% → Return similar response│   │
│  │                                                  │    │
│  │ 3. LLM Call (Miss) - 1-3s                       │    │
│  │    └─> Call LLM → Cache response → Return       │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Storage Layer (Memory + Disk)                    │
│  ┌──────────────────┐  ┌────────────────────────────┐   │
│  │ In-Memory Cache  │  │ Persistent Disk Cache      │   │
│  │ (LRU, fast)      │  │ (~/.empathy/cache/)        │   │
│  │ Max: 100MB       │  │ Max: 500MB, TTL: 24h       │   │
│  └──────────────────┘  └────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### **1. Base Cache Interface** (`src/attune/cache/base.py`)

**Status:** ✅ Implemented

**Purpose:** Abstract interface for all cache implementations.

**Key Classes:**
- `BaseCache` - Abstract cache interface
- `CacheEntry` - Cached response with metadata
- `CacheStats` - Hit/miss/eviction tracking

**Methods:**
```python
class BaseCache(ABC):
    def get(workflow, stage, prompt, model) -> Optional[Any]
    def put(workflow, stage, prompt, model, response, ttl) -> None
    def clear() -> None
    def get_stats() -> CacheStats
```

---

### **2. Hash-Only Cache** (`src/attune/cache/hash_only.py`)

**Status:** 🔄 Next to implement

**Purpose:** Fast exact-match caching using SHA256 hashing.

**Performance:** 1-5μs lookup time
**Hit Rate:** ~30% (exact matches only)
**Dependencies:** None (always available)

**Cache Key Format:**
```python
key = SHA256(workflow + "|" + stage + "|" + prompt + "|" + model)
```

**Implementation Details:**
- In-memory dict: `{key: CacheEntry}`
- Disk storage: JSON file at `~/.empathy/cache/hash_cache.json`
- LRU eviction when memory limit exceeded
- TTL expiration: 24 hours default

**Example:**
```python
# First call (cache miss)
result = await code_review.execute(diff="fix bug in auth.py")
# → LLM call: 2.5s, $0.45

# Second call - exact same diff (cache hit)
result = await code_review.execute(diff="fix bug in auth.py")
# → Cache hit: 0.001s, $0.00
```

---

### **3. Hybrid Cache** (`src/attune/cache/hybrid.py`)

**Status:** 🔄 To implement

**Purpose:** Hash + semantic similarity caching for maximum hit rate.

**Performance:**
- Hash lookup: 1-5μs
- Semantic lookup: 50ms (CPU) / 10ms (GPU)
- Total overhead: <100ms

**Hit Rate:** ~70-75% (hash 30% + semantic 40-45%)

**Dependencies:**
- `sentence-transformers>=2.0.0`
- `torch>=2.0.0`
- `numpy>=1.24.0`

**Semantic Similarity:**
- Model: `all-MiniLM-L6-v2` (80MB)
- Threshold: 0.95 (configurable)
- Metric: Cosine similarity

**Workflow:**
```python
def get(workflow, stage, prompt, model):
    # Step 1: Try hash cache (fast path)
    hash_key = SHA256(workflow + stage + prompt + model)
    if hash_key in hash_cache:
        return hash_cache[hash_key]  # 1μs

    # Step 2: Try semantic cache (smart path)
    embedding = model.encode(prompt)  # 50ms
    for cached_embedding, response in semantic_cache:
        similarity = cosine_similarity(embedding, cached_embedding)
        if similarity > 0.95:
            # Add to hash cache for future fast lookups
            hash_cache[hash_key] = response
            return response  # Semantic hit

    # Step 3: Cache miss - call LLM
    return None
```

**Example:**
```python
# Original prompt
result1 = await code_review.execute(diff="Added auth middleware to app.py")
# → Cache miss: LLM call 2.5s

# Similar prompt (92% similarity)
result2 = await code_review.execute(diff="Added logging middleware to app.py")
# → Semantic hit: 50ms from cache (instead of 2.5s LLM call)
```

---

### **4. Storage Layer** (`src/attune/cache/storage.py`)

**Status:** 🔄 To implement

**Purpose:** Hybrid in-memory + disk persistence with TTL.

**Architecture:**
```python
class CacheStorage:
    memory_cache: dict[str, CacheEntry]  # LRU, max 100MB
    disk_cache_path: Path  # ~/.empathy/cache/responses.db

    def load() -> None:
        """Load disk cache into memory on startup."""

    def save() -> None:
        """Persist memory cache to disk."""

    def evict_expired() -> int:
        """Remove expired entries based on TTL."""
```

**Storage Format (Disk):**
```json
{
  "version": "3.8.0",
  "entries": [
    {
      "key": "a1b2c3...",
      "workflow": "code-review",
      "stage": "scan",
      "model": "claude-3-5-sonnet-20241022",
      "prompt_hash": "d4e5f6...",
      "response": {...},
      "timestamp": 1704585600.0,
      "ttl": 86400
    }
  ]
}
```

**Memory Management:**
- Max in-memory: 100MB (configurable)
- Eviction policy: LRU (least recently used)
- Write-through: Save to disk on put()
- Lazy load: Load from disk on get() if not in memory

---

### **5. Dependency Manager** (`src/attune/cache/dependency_manager.py`)

**Status:** 🔄 To implement

**Purpose:** Auto-detect missing dependencies, prompt user to install.

**User Experience:**
```bash
# User installs base version
pip install attune-ai

# First workflow run
attune workflow run code-review

# Output:
⚡ Smart Caching Available

  Attune AI can reduce your API costs by 70% with hybrid caching.
  This requires installing sentence-transformers (~150MB).

  Would you like to enable smart caching now? [Y/n]: y

  ↓ Installing cache dependencies...
  ✓ sentence-transformers 2.3.1 installed
  ✓ torch 2.1.2 installed
  ✓ numpy 1.24.3 installed

  ✓ Smart caching enabled! Future runs will save 70% on costs.
```

**Implementation:**
```python
class DependencyManager:
    def is_cache_installed() -> bool:
        """Check if sentence-transformers available."""

    def should_prompt_cache_install() -> bool:
        """Check if we should prompt (first run, not declined)."""

    def prompt_cache_install() -> bool:
        """Prompt user and install if accepted."""

    def install_cache_dependencies() -> bool:
        """Run pip install sentence-transformers torch numpy."""
```

**Configuration (``~/.empathy/config.yml`):**
```yaml
cache:
  enabled: true
  install_declined: false  # User said "no" to prompt
  prompt_shown: true       # Never prompt again
  model: all-MiniLM-L6-v2
  similarity_threshold: 0.95
  max_size_mb: 500
  ttl: 86400  # 24 hours
```

---

### **6. BaseWorkflow Integration** (`src/attune/workflows/base.py`)

**Status:** 🔄 To implement

**Purpose:** Transparent caching for all workflows.

**Modifications:**
```python
class BaseWorkflow:
    def __init__(self, **kwargs):
        # Auto-prompt for cache on first run
        self._maybe_setup_cache()

        # Create cache (hybrid if available, hash-only otherwise)
        self.cache = self._create_cache()

    def _maybe_setup_cache(self):
        """One-time prompt to install cache deps."""
        from attune.cache import auto_setup_cache
        auto_setup_cache()

    def _create_cache(self):
        """Create appropriate cache based on installed deps."""
        from attune.cache import create_cache
        return create_cache()

    async def _execute_stage(self, stage_name, prompt, model):
        """Execute stage with caching."""
        # Try cache first
        cached = self.cache.get(
            workflow=self.name,
            stage=stage_name,
            prompt=prompt,
            model=model
        )

        if cached is not None:
            self.cache.stats.hits += 1
            return cached

        # Cache miss - call LLM
        self.cache.stats.misses += 1
        response = await self._call_llm(prompt, model)

        # Store in cache
        self.cache.put(
            workflow=self.name,
            stage=stage_name,
            prompt=prompt,
            model=model,
            response=response
        )

        return response
```

---

### **7. Cost Reporting Enhancement**

**Status:** 🔄 To implement

**Purpose:** Show cache savings in cost reports.

**Current Cost Report:**
```python
@dataclass
class CostReport:
    total_cost: float
    per_stage_cost: dict[str, float]
    model_breakdown: dict[str, float]
```

**Enhanced Cost Report:**
```python
@dataclass
class CostReport:
    total_cost: float  # Actual cost paid
    per_stage_cost: dict[str, float]
    model_breakdown: dict[str, float]

    # NEW: Cache metrics
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float  # Percentage
    estimated_cost_without_cache: float  # What it would have cost
    savings_from_cache: float  # Money saved
    savings_percent: float  # Percentage saved
```

**Example Output:**
```bash
✓ Code review complete

Cost Report:
  Actual cost: $0.45
  Without cache: $1.50
  Savings: $1.05 (70%)

  Cache: 3 hits / 2 misses (60% hit rate)

  Per-stage:
    classify: $0.15 (cache hit)
    scan: $0.00 (cache hit)
    architect_review: $0.30 (cache miss)
```

---

## Implementation Plan

### **Phase 1: Core Infrastructure** (Days 1-2)

**Tasks:**
1. ✅ Create base cache interface (`base.py`)
2. ⏳ Implement HashOnlyCache (`hash_only.py`)
3. ⏳ Implement storage layer (`storage.py`)
4. ⏳ Write unit tests for hash cache

**Deliverable:** Hash-only caching working, ~30% cost savings

---

### **Phase 2: Hybrid Caching** (Days 3-4)

**Tasks:**
1. ⏳ Implement HybridCache with semantic similarity
2. ⏳ Handle optional dependency gracefully (fallback to hash-only)
3. ⏳ Write unit tests for semantic matching
4. ⏳ Benchmark performance (hash vs semantic vs LLM)

**Deliverable:** Hybrid caching working, ~70% cost savings

---

### **Phase 3: User Experience** (Day 5)

**Tasks:**
1. ⏳ Implement DependencyManager with one-time prompt
2. ⏳ Create `~/.empathy/config.yml` configuration system
3. ⏳ Integrate cache into BaseWorkflow
4. ⏳ Test with code-review workflow

**Deliverable:** Zero-config UX, automatic setup

---

### **Phase 4: Cost Reporting** (Day 6)

**Tasks:**
1. ⏳ Enhance CostReport with cache metrics
2. ⏳ Calculate estimated cost without cache
3. ⏳ Log cache stats (hits/misses/savings)
4. ⏳ Update workflow result formatting

**Deliverable:** Cost savings visible to users

---

### **Phase 5: Testing & Documentation** (Days 7-8)

**Tasks:**
1. ⏳ Comprehensive unit tests (target: 100% coverage)
2. ⏳ Integration tests with real workflows
3. ⏳ Create `docs/caching.md` documentation
4. ⏳ Update README with caching info
5. ⏳ Update `pyproject.toml` for v3.8.0

**Deliverable:** Production-ready, fully tested

---

## Testing Strategy

### **Unit Tests**

**Files to create:**
- `tests/unit/cache/test_base_cache.py`
- `tests/unit/cache/test_hash_cache.py`
- `tests/unit/cache/test_hybrid_cache.py`
- `tests/unit/cache/test_storage.py`
- `tests/unit/cache/test_dependency_manager.py`

**Test Coverage:**
- ✅ Cache hit/miss scenarios
- ✅ TTL expiration
- ✅ LRU eviction
- ✅ Disk persistence and reload
- ✅ Semantic similarity matching
- ✅ Fallback to hash-only when deps missing
- ✅ Cost report calculations

---

### **Integration Tests**

**Test Scenarios:**
1. Run code-review twice with same diff → cache hit
2. Run code-review with similar diff → semantic hit
3. Run without sentence-transformers → hash-only fallback
4. Restart framework → reload cache from disk
5. Cache exceeds size limit → LRU eviction
6. Entry exceeds TTL → expire and miss

---

## Configuration Schema

**File:** `~/.empathy/config.yml`

```yaml
# Cache configuration
cache:
  enabled: true                      # Enable/disable caching
  type: hybrid                       # hybrid | hash-only | disabled
  install_declined: false            # User declined install prompt
  prompt_shown: false                # Has prompt been shown?

  # Hybrid cache settings
  model: all-MiniLM-L6-v2           # Sentence transformer model
  similarity_threshold: 0.95         # Semantic match threshold (0.0-1.0)
  device: cpu                        # cpu | cuda

  # Storage settings
  max_size_mb: 500                   # Max disk cache size
  max_memory_mb: 100                 # Max in-memory cache
  ttl: 86400                         # Default TTL (24 hours)
  cache_dir: ~/.empathy/cache        # Cache storage path

  # Logging
  log_hits: true                     # Log cache hits to debug
  log_misses: true                   # Log cache misses to debug
```

---

## pyproject.toml Updates

**Version bump:** 3.7.1 → 3.8.0

**New optional dependencies:**
```toml
[project.optional-dependencies]
cache = [
    "sentence-transformers>=2.0.0",
    "torch>=2.0.0",
    "numpy>=1.24.0",
]

full = [
    "attune-ai[cache,developer,healthcare]",
]
```

---

## Performance Targets

| Operation | Target | Acceptable |
|-----------|--------|------------|
| Hash cache lookup | <5μs | <10μs |
| Semantic cache lookup | <100ms (CPU) | <200ms |
| Disk load on startup | <500ms | <1s |
| Memory overhead | <100MB | <200MB |
| Disk usage | <500MB | <1GB |

---

## Cost Savings Projections

**Workflow:** code-review (5 stages)

| Scenario | LLM Calls | Cache Hits | Cost | Savings |
|----------|-----------|------------|------|---------|
| **No cache** | 5 | 0 | $1.50 | 0% |
| **Hash-only** | 3.5 | 1.5 (30%) | $1.05 | 30% |
| **Hybrid** | 1.5 | 3.5 (70%) | $0.45 | 70% |

**Monthly savings (at $1,000/month spend):**
- Hash-only: $300/month saved
- Hybrid: $700/month saved

---

## Risk Mitigation

### **Risk 1: Semantic model download fails**
**Mitigation:** Fallback to hash-only cache automatically, log warning.

### **Risk 2: Cache causes incorrect responses**
**Mitigation:**
- Default threshold: 0.95 (95% similarity)
- Include model in cache key (different models don't share cache)
- Users can disable caching entirely

### **Risk 3: Cache fills disk**
**Mitigation:**
- Max size limit: 500MB (configurable)
- TTL expiration: 24 hours
- LRU eviction policy

### **Risk 4: Breaking change for existing users**
**Mitigation:**
- Backwards compatible (cache is opt-in)
- Base install still works without cache deps
- No API changes to workflows

---

## Success Metrics

**v3.8.0 will be considered successful if:**

- ✅ 70% cache hit rate on code-review workflow
- ✅ <100ms cache lookup overhead
- ✅ Zero breaking changes (all existing tests pass)
- ✅ User can install with `pip install attune-ai[cache]`
- ✅ User can add cache later with `attune install cache`
- ✅ Cost report shows savings accurately
- ✅ Works offline after initial model download
- ✅ 100% test coverage on cache module

---

## Next Steps

1. ✅ **Planning complete** - This document
2. ⏳ **Implement Phase 1** - Hash-only cache + storage
3. ⏳ **Implement Phase 2** - Hybrid semantic caching
4. ⏳ **Implement Phase 3** - DependencyManager + UX
5. ⏳ **Implement Phase 4** - Cost reporting
6. ⏳ **Implement Phase 5** - Tests + docs
7. ⏳ **Release v3.8.0** - Ship to PyPI

---

**Status:** 📋 Ready to implement
**Estimated completion:** 8 days
**Target release date:** v3.8.0 mid-January 2026
