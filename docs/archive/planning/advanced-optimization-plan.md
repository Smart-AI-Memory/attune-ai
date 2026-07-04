# Advanced Optimization Plan - Attune AI

> **Archived 2026-07-04** (rules-corpus-jit): Jan-2026 Phase-2
> planning doc, not a rule; moved out of always-loaded
> `.claude/rules/`. Historical reference only.

**Version:** 1.0
**Created:** January 10, 2026
**Owner:** Engineering Team
**Status:** Planning Phase

---

## 🎯 Executive Summary

This document outlines Phase 2 optimization efforts following the successful list copy optimization initiative (Jan 2026). Focus areas: profiling-driven optimization, generator expressions, data structure improvements, and intelligent caching.

**Prerequisites:**
- ✅ Phase 1 completed: List copy optimizations (14 high-priority, 6 medium-priority)
- ✅ Baseline established: Performance benchmarks documented
- ✅ Testing infrastructure: 127+ tests passing

**Goals:**
- 📊 Identify and eliminate performance bottlenecks through profiling
- ⚡ Reduce memory footprint with generator expressions
- 🔍 Optimize lookup operations with appropriate data structures
- 💾 Implement strategic caching for expensive computations

**Timeline:** 2-3 weeks (estimated)

---

## 📋 Phase 2: Four-Track Optimization Strategy

### Track 1: Profile Hot Paths (Priority: HIGH)
### Track 2: Generator Expression Migration (Priority: MEDIUM)
### Track 3: Data Structure Optimization (Priority: MEDIUM)
### Track 4: Intelligent Caching (Priority: HIGH)

---

## 🔬 Track 1: Profile Hot Paths

**Objective:** Use data-driven profiling to identify actual bottlenecks rather than guessing.

### 1.1 Setup Profiling Infrastructure

**Tools to install:**
```bash
# Install profiling tools
pip install memory_profiler
pip install line_profiler
pip install py-spy
pip install snakeviz  # Visualization
```

**Create profiling utilities:**
```python
# File: scripts/profile_utils.py
import cProfile
import pstats
import io
from functools import wraps
from pathlib import Path
import time
from typing import Callable, Any

def profile_function(output_file: str | None = None):
    """Decorator to profile a function with cProfile."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()

            result = func(*args, **kwargs)

            profiler.disable()

            # Print to stdout
            s = io.StringIO()
            stats = pstats.Stats(profiler, stream=s)
            stats.sort_stats('cumulative')
            stats.print_stats(20)  # Top 20
            print(s.getvalue())

            # Save to file if requested
            if output_file:
                stats.dump_stats(output_file)
                print(f"\nProfile saved to: {output_file}")
                print(f"Visualize with: snakeviz {output_file}")

            return result
        return wrapper
    return decorator


def time_function(func: Callable) -> Callable:
    """Simple timing decorator."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        print(f"{func.__name__} took {duration:.4f} seconds")
        return result
    return wrapper


def profile_memory(func: Callable) -> Callable:
    """Decorator for memory profiling (requires memory_profiler)."""
    from memory_profiler import profile
    return profile(func)
```

### 1.2 Identify Profiling Targets

**High-priority targets** (frequently used, user-facing):

1. **Project Index Scanner** (`src/attune/project_index/scanner.py`)
   - `scan()` method - Scans entire codebase
   - `_build_summary()` - Aggregates metrics
   - Expected bottleneck: File I/O and AST parsing

2. **Workflow Execution** (`src/attune/workflows/base.py`)
   - `execute()` method - Runs multi-tier workflows
   - Expected bottleneck: LLM API calls, JSON parsing

3. **Pattern Matching** (`src/attune/pattern_library.py`)
   - `match()` method - Pattern recognition
   - Expected bottleneck: Regex operations, list iterations

4. **Memory Operations** (`src/attune/memory/unified.py`)
   - `recall()` method - Retrieves from memory graph
   - Expected bottleneck: Graph traversal, deserialization

5. **Test Generator** (`src/attune/workflows/test_gen/workflow.py`)
   - `_generate_test_cases()` - Generates parametrized tests
   - Expected bottleneck: AST parsing, template rendering

### 1.3 Create Profiling Test Suite

**File:** `benchmarks/profile_suite.py`

```python
"""Profiling test suite for identifying bottlenecks."""
import sys
from pathlib import Path
from scripts.profile_utils import profile_function, time_function

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from attune.project_index import ProjectIndex
from attune.pattern_library import PatternLibrary
from attune.workflows.test_gen import TestGenerationWorkflow


@profile_function(output_file="profiles/scanner_scan.prof")
@time_function
def profile_scanner():
    """Profile project scanner on real codebase."""
    index = ProjectIndex(project_root=".")
    index.scan()  # Scans entire codebase
    summary = index.get_summary()
    print(f"Scanned {summary.total_files} files")


@profile_function(output_file="profiles/pattern_matching.prof")
@time_function
def profile_pattern_matching():
    """Profile pattern matching operations."""
    library = PatternLibrary()

    # Simulate 1000 pattern matches
    for i in range(1000):
        context = {
            "query": f"test query {i}",
            "history": [f"item {j}" for j in range(10)],
            "metadata": {"timestamp": i}
        }
        matches = library.match(context)

    print(f"Completed 1000 pattern matches")


@profile_function(output_file="profiles/test_generation.prof")
@time_function
def profile_test_generation():
    """Profile test generation workflow."""
    workflow = TestGenerationWorkflow()

    # Simulate generating tests for 100 functions
    for i in range(100):
        result = workflow._analyze_function(
            name=f"test_function_{i}",
            code=f"def test_function_{i}(x: int) -> int:\n    return x * 2",
            docstring="Test function for profiling"
        )

    print("Completed 100 test generations")


if __name__ == "__main__":
    import os
    os.makedirs("profiles", exist_ok=True)

    print("=" * 60)
    print("PROFILING SUITE - Attune AI")
    print("=" * 60)

    print("\n1. Profiling Scanner...")
    profile_scanner()

    print("\n2. Profiling Pattern Matching...")
    profile_pattern_matching()

    print("\n3. Profiling Test Generation...")
    profile_test_generation()

    print("\n" + "=" * 60)
    print("PROFILING COMPLETE")
    print("=" * 60)
    print("\nView profiles with:")
    print("  snakeviz profiles/scanner_scan.prof")
    print("  snakeviz profiles/pattern_matching.prof")
    print("  snakeviz profiles/test_generation.prof")
```

### 1.4 Execute Profiling

**Steps:**
1. Run profiling suite: `python benchmarks/profile_suite.py`
2. Visualize with snakeviz: `snakeviz profiles/*.prof`
3. Identify functions consuming >10% cumulative time
4. Document findings in `docs/PROFILING_RESULTS.md`

**Expected output format:**
```
Top 10 Hotspots (by cumulative time):
1. _parse_python_file() - 45% (I/O + AST parsing)
2. _calculate_complexity() - 15% (AST traversal)
3. _match_patterns() - 12% (Regex operations)
4. json.dumps() - 8% (Serialization)
5. Path.glob() - 6% (File system operations)
...
```

### 1.5 Create Optimization Tickets

**Template:**
```markdown
## Performance Optimization: [Function Name]

**Hotspot:** [file:line]
**Current Performance:** X ms per call
**Cumulative Time:** Y% of total execution
**Call Count:** Z calls

**Root Cause:**
- [Analysis from profiling]

**Proposed Fix:**
- [Specific optimization approach]

**Expected Impact:**
- [Estimated performance improvement]

**Implementation Priority:** [HIGH/MEDIUM/LOW]
```

---

## 🔄 Track 2: Generator Expression Migration

**Objective:** Replace memory-intensive list comprehensions with memory-efficient generators for one-time iterations.

### 2.1 Identify Candidates

**Search patterns:**
```bash
# Find large list comprehensions (>3 lines or in loops)
grep -r "\[.*for.*in.*\]" src/ --include="*.py" | grep -v "test_"

# Find list comprehensions with multiple iterations
grep -r "for.*\[.*for.*in" src/ --include="*.py"
```

**Manual review criteria:**
- List is iterated only once
- List size potentially large (>1000 items)
- List is not indexed or sliced
- List is not modified after creation

### 2.2 Prioritized Conversion List

**High-Priority Candidates** (estimated memory savings):

1. **File scanning operations** (`project_index/scanner.py`)
   ```python
   # Before: Creates list of all .py files in memory
   py_files = [f for f in Path(".").rglob("*.py")]
   for file in py_files:
       process(file)

   # After: Generator yields files one at a time
   py_files = (f for f in Path(".").rglob("*.py"))
   for file in py_files:
       process(file)

   # Savings: ~1MB per 1000 files
   ```

2. **Log processing** (`telemetry/cli.py`)
   ```python
   # Before: Loads all log entries into memory
   entries = [parse_line(line) for line in log_file]
   recent = [e for e in entries if e.timestamp > cutoff]

   # After: Generator pipeline
   entries = (parse_line(line) for line in log_file)
   recent = (e for e in entries if e.timestamp > cutoff)

   # Savings: ~10MB for large log files
   ```

3. **Pattern matching** (`pattern_library.py`)
   ```python
   # Before: Creates list of all matches
   matches = [p for p in patterns if p.score > threshold]
   best = max(matches, key=lambda p: p.score)

   # After: Generator with max
   matches = (p for p in patterns if p.score > threshold)
   best = max(matches, key=lambda p: p.score, default=None)

   # Savings: O(n) space -> O(1) space
   ```

### 2.3 Migration Strategy

**Safe migration pattern:**
```python
# Step 1: Add generator variant
def get_items_gen(self) -> Iterator[Item]:
    """Generator version of get_items()."""
    return (self._transform(i) for i in self._data if i.is_valid)

# Step 2: Update callers (one at a time)
for item in get_items_gen():  # Changed from get_items()
    process(item)

# Step 3: Add deprecation warning to old version
def get_items(self) -> list[Item]:
    """Get items as list (deprecated - use get_items_gen for better memory usage)."""
    warnings.warn("Use get_items_gen() for better memory efficiency", DeprecationWarning)
    return list(get_items_gen())

# Step 4: Remove old version in next major release
```

### 2.4 Testing Generator Conversions

**Test template:**
```python
def test_generator_equivalent_to_list():
    """Ensure generator produces same results as list version."""
    # Given
    data = create_test_data(size=1000)

    # When
    list_result = list(get_items(data))
    gen_result = list(get_items_gen(data))

    # Then
    assert list_result == gen_result

def test_generator_memory_efficient():
    """Verify generator doesn't load all data into memory."""
    from memory_profiler import memory_usage

    # Measure memory for list version
    list_mem = max(memory_usage((lambda: list(get_items(large_dataset)))))

    # Measure memory for generator version
    gen_mem = max(memory_usage((lambda: consume(get_items_gen(large_dataset)))))

    # Generator should use significantly less memory
    assert gen_mem < list_mem * 0.5  # At least 50% reduction
```

---

## 🔍 Track 3: Data Structure Optimization

**Objective:** Replace linear search operations with O(1) lookups using sets and dictionaries.

### 3.1 Identify Lookup Antipatterns

**Search for O(n) lookups:**
```bash
# Find "if x in list" patterns
grep -r "if .* in \[" src/ --include="*.py"

# Find list.index() calls
grep -r "\.index(" src/ --include="*.py"

# Find repeated iterations over same list
grep -r "for .* in .*:" src/ --include="*.py" -A 5 | grep "for .* in"
```

**Common antipatterns:**

1. **Membership testing with lists**
   ```python
   # Bad: O(n) per check
   valid_statuses = ["active", "pending", "reviewing"]
   if user.status in valid_statuses:  # Linear scan
       process(user)

   # Good: O(1) per check
   VALID_STATUSES = {"active", "pending", "reviewing"}
   if user.status in VALID_STATUSES:  # Hash lookup
       process(user)
   ```

2. **Repeated lookups by key**
   ```python
   # Bad: O(n) per lookup
   files = [{"path": "a.py", "size": 100}, {"path": "b.py", "size": 200}]
   for path in paths_to_check:
       file = next((f for f in files if f["path"] == path), None)  # O(n)

   # Good: O(1) per lookup
   files_by_path = {f["path"]: f for f in files}  # O(n) once
   for path in paths_to_check:
       file = files_by_path.get(path)  # O(1)
   ```

3. **Checking for duplicates**
   ```python
   # Bad: O(n²)
   unique = []
   for item in items:
       if item not in unique:  # O(n) check
           unique.append(item)

   # Good: O(n) with set
   unique = list(dict.fromkeys(items))  # Already optimized in Phase 1!
   ```

### 3.2 Optimization Candidates by File

**Priority 1: High-frequency lookups**

1. **Pattern Registry** (`src/attune/pattern_library.py`)
   ```python
   # Current: List of patterns, O(n) lookup
   self.patterns: list[Pattern] = []

   # Optimized: Dict by ID, O(1) lookup
   self._patterns_by_id: dict[str, Pattern] = {}
   self._patterns_by_tag: dict[str, list[Pattern]] = defaultdict(list)

   def get_pattern(self, pattern_id: str) -> Pattern | None:
       return self._patterns_by_id.get(pattern_id)  # O(1) vs O(n)

   def get_by_tag(self, tag: str) -> list[Pattern]:
       return self._patterns_by_tag.get(tag, [])  # O(1) vs O(n)
   ```

2. **File Index** (`src/attune/project_index/scanner.py`)
   ```python
   # Current: List of FileRecord, O(n) for path lookup
   records: list[FileRecord] = []

   # Optimized: Additional index structures
   self._records: list[FileRecord] = []
   self._by_path: dict[str, FileRecord] = {}
   self._by_category: dict[FileCategory, list[FileRecord]] = defaultdict(list)

   def get_file(self, path: str) -> FileRecord | None:
       return self._by_path.get(path)  # O(1)

   def get_by_category(self, category: FileCategory) -> list[FileRecord]:
       return self._by_category.get(category, [])  # O(1)
   ```

3. **Model Registry** (`src/attune/models/registry.py`)
   ```python
   # Already uses dict - verify no linear scans in callers
   MODEL_REGISTRY: dict[str, ModelInfo] = {...}

   # Check for antipatterns like:
   all_models = list(MODEL_REGISTRY.values())
   model = next((m for m in all_models if m.tier == "cheap"), None)  # BAD!

   # Should be:
   MODELS_BY_TIER = {
       "cheap": [m for m in MODEL_REGISTRY.values() if m.tier == "cheap"],
       "capable": [...],
       "premium": [...]
   }
   ```

### 3.3 Implementation Checklist

For each optimization:

- [ ] Benchmark current performance
- [ ] Implement index structure
- [ ] Update all lookup sites
- [ ] Add tests for new index
- [ ] Verify performance improvement (should be >50% for large datasets)
- [ ] Update documentation

---

## 💾 Track 4: Intelligent Caching

**Objective:** Cache expensive computations that are frequently accessed with the same inputs.

### 4.1 Caching Strategy Decision Tree

```
Is computation expensive (>10ms)?
├─ YES: Continue
└─ NO: Don't cache (overhead > benefit)

Are inputs hashable?
├─ YES: Continue
└─ NO: Consider custom cache key or don't cache

Is result deterministic?
├─ YES: Continue
└─ NO: Don't cache

How often is same input repeated?
├─ Often (>10% hit rate): Implement caching
└─ Rarely: Don't cache (memory waste)

What's the data size?
├─ Small (<1MB): Use @lru_cache
├─ Medium (1-100MB): Use custom cache with size limits
└─ Large (>100MB): Use disk cache or DB
```

### 4.2 Caching Candidates

**High-Value Caching Opportunities:**

1. **File Content Hashing** (`project_index/scanner.py`)
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def _hash_file(file_path: str) -> str:
       """Cache file hashes (expensive I/O operation)."""
       return hashlib.sha256(Path(file_path).read_bytes()).hexdigest()

   # Benefit: Avoid re-reading files during incremental scans
   # Hit rate: 80%+ for repeated scans
   # Memory: ~64 bytes per entry * 1000 = 64KB
   ```

2. **AST Parsing** (`project_index/scanner.py`)
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=500)
   def _parse_python_file(file_path: str, file_hash: str) -> ast.Module:
       """Cache AST parsing (expensive CPU operation).

       Args:
           file_path: Path to Python file
           file_hash: Hash of file contents (for cache invalidation)
       """
       return ast.parse(Path(file_path).read_text())

   # Benefit: Avoid re-parsing unchanged files
   # Hit rate: 90%+ for incremental operations
   # Memory: ~10KB per AST * 500 = 5MB
   ```

3. **Pattern Matching** (`pattern_library.py`)
   ```python
   from functools import lru_cache
   import json

   def _make_context_key(context: dict) -> str:
       """Create hashable key from context dict."""
       return json.dumps(context, sort_keys=True)

   @lru_cache(maxsize=1000)
   def _match_patterns_cached(context_key: str, pattern_hash: str) -> list[Match]:
       """Cache pattern matching results."""
       context = json.loads(context_key)
       return self._match_patterns_uncached(context)

   # Benefit: Avoid re-running expensive regex operations
   # Hit rate: 60%+ for similar queries
   # Memory: ~1KB per result * 1000 = 1MB
   ```

4. **API Response Caching** (`workflows/base.py`)
   ```python
   from datetime import datetime, timedelta
   from typing import TypedDict

   class CacheEntry(TypedDict):
       result: dict
       expires: datetime

   class WorkflowCache:
       """TTL-based cache for API responses."""

       def __init__(self, ttl_seconds: int = 3600):
           self._cache: dict[str, CacheEntry] = {}
           self._ttl = timedelta(seconds=ttl_seconds)

       def get(self, key: str) -> dict | None:
           entry = self._cache.get(key)
           if entry and datetime.now() < entry["expires"]:
               return entry["result"]
           return None

       def set(self, key: str, result: dict):
           self._cache[key] = {
               "result": result,
               "expires": datetime.now() + self._ttl
           }

   # Usage in workflow
   cache = WorkflowCache(ttl_seconds=1800)  # 30 min cache

   def execute(self, input_data: dict):
       cache_key = self._make_cache_key(input_data)
       cached = cache.get(cache_key)
       if cached:
           return cached  # Cache hit!

       result = self._execute_uncached(input_data)
       cache.set(cache_key, result)
       return result
   ```

### 4.3 Cache Invalidation Strategies

**File-based caching:**
```python
class FileCache:
    """Cache with file modification time tracking."""

    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}

    def get(self, file_path: str) -> Any | None:
        if file_path not in self._cache:
            return None

        cached_value, cached_mtime = self._cache[file_path]
        current_mtime = Path(file_path).stat().st_mtime

        if current_mtime == cached_mtime:
            return cached_value  # File hasn't changed

        # File modified, invalidate
        del self._cache[file_path]
        return None

    def set(self, file_path: str, value: Any):
        mtime = Path(file_path).stat().st_mtime
        self._cache[file_path] = (value, mtime)
```

**Hash-based invalidation:**
```python
def cached_computation(data: str, version: int = 1):
    """Cache with version-based invalidation.

    When algorithm changes, increment version to invalidate old cache.
    """
    cache_key = f"{hash(data)}:v{version}"
    # ... cache lookup with versioned key
```

### 4.4 Monitoring Cache Performance

**Cache metrics to track:**
```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar('T')

@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

class MonitoredCache(Generic[T]):
    """LRU cache with performance monitoring."""

    def __init__(self, maxsize: int = 128):
        self._cache: dict[str, T] = {}
        self._maxsize = maxsize
        self.stats = CacheStats()

    def get(self, key: str) -> T | None:
        if key in self._cache:
            self.stats.hits += 1
            return self._cache[key]
        self.stats.misses += 1
        return None

    def report(self) -> str:
        return (
            f"Cache Stats:\n"
            f"  Hit rate: {self.stats.hit_rate:.1%}\n"
            f"  Hits: {self.stats.hits:,}\n"
            f"  Misses: {self.stats.misses:,}\n"
            f"  Total: {self.stats.total_requests:,}\n"
            f"  Size: {len(self._cache)}/{self._maxsize}"
        )
```

---

## 📊 Implementation Roadmap

### Week 1: Profiling & Analysis

**Days 1-2: Setup & Initial Profiling**
- [ ] Install profiling tools
- [ ] Create profiling utilities (`scripts/profile_utils.py`)
- [ ] Set up profiling test suite (`benchmarks/profile_suite.py`)
- [ ] Run initial profiling on 5 target areas

**Days 3-4: Analysis & Prioritization**
- [ ] Analyze profiling results
- [ ] Create hotspot documentation (`docs/PROFILING_RESULTS.md`)
- [ ] Identify top 10 bottlenecks
- [ ] Create GitHub issues for each bottleneck

**Day 5: Planning**
- [ ] Prioritize optimizations by impact
- [ ] Assign owners to optimization tracks
- [ ] Set up performance regression tests

### Week 2: High-Priority Optimizations

**Days 1-3: Generator Conversions**
- [ ] Identify 10 high-value candidates
- [ ] Implement generator variants
- [ ] Add memory profiling tests
- [ ] Migrate callers incrementally
- [ ] Measure memory savings

**Days 4-5: Data Structure Optimizations**
- [ ] Implement index structures for Pattern Library
- [ ] Optimize File Index lookups
- [ ] Add benchmark comparisons
- [ ] Update documentation

### Week 3: Caching & Validation

**Days 1-2: Caching Implementation**
- [ ] Implement file hash caching
- [ ] Implement AST parsing cache
- [ ] Add cache monitoring
- [ ] Configure cache size limits

**Days 3-4: Testing & Validation**
- [ ] Run full test suite
- [ ] Verify no regressions
- [ ] Measure performance improvements
- [ ] Update benchmarks

**Day 5: Documentation & Wrap-up**
- [ ] Document all optimizations
- [ ] Update performance guidelines
- [ ] Create migration guide for generator expressions
- [ ] Write blog post on results

---

## 📈 Success Metrics

**Performance Targets:**

| Metric | Current | Target | Stretch Goal |
|--------|---------|--------|--------------|
| Project scan time (1000 files) | 5.2s | 3.0s | 2.0s |
| Pattern matching (1000 queries) | 850ms | 500ms | 300ms |
| Memory usage (scan) | 120MB | 80MB | 60MB |
| Test generation (100 functions) | 12s | 8s | 5s |
| Cache hit rate | 0% | 60% | 80% |

**Quality Metrics:**

- [ ] 100% test pass rate maintained
- [ ] No new performance regressions
- [ ] Code coverage maintained (>80%)
- [ ] All optimizations documented
- [ ] Performance benchmarks updated

---

## 🛠️ Tools & Resources

**Profiling Tools:**
- `cProfile` - Standard library profiler
- `line_profiler` - Line-by-line profiling
- `memory_profiler` - Memory usage profiling
- `py-spy` - Sampling profiler (no code changes)
- `snakeviz` - Visualization for cProfile output

**Monitoring:**
- `pytest-benchmark` - Performance regression tests
- Custom cache monitoring (see Track 4.4)

**Documentation:**
- [Python Performance Tips](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)
- [Memory Profiler Guide](https://pypi.org/project/memory-profiler/)
- [Generator Expressions](https://peps.python.org/pep-0289/)

---

## ⚠️ Risks & Mitigation

**Risk 1: Breaking Changes**
- **Mitigation:** Comprehensive test coverage, incremental rollout
- **Rollback Plan:** Feature flags for new optimizations

**Risk 2: Premature Optimization**
- **Mitigation:** Profile first, optimize based on data
- **Validation:** Measure actual impact with benchmarks

**Risk 3: Cache Invalidation Bugs**
- **Mitigation:** Extensive testing, monitoring of cache stats
- **Fallback:** Ability to disable caching via config

**Risk 4: Memory Leaks from Caching**
- **Mitigation:** Size-bounded caches, TTL expiration
- **Monitoring:** Track cache size in production

---

## 📝 Appendix A: Quick Reference Commands

```bash
# Profile a specific workflow
python -m cProfile -o output.prof -s cumulative workflows/test_gen.py
snakeviz output.prof

# Memory profiling
python -m memory_profiler benchmarks/profile_suite.py

# Line profiling (requires @profile decorator)
kernprof -l -v script.py

# Sampling profiler (no code changes needed)
py-spy record -o profile.svg -- python script.py

# Run performance regression tests
pytest benchmarks/ --benchmark-only

# Generate performance report
pytest benchmarks/ --benchmark-json=benchmark.json
```

---

## 📝 Appendix B: Code Review Checklist for Phase 2

When reviewing optimizations:

**Profiling:**
- [ ] Optimization based on actual profiling data, not assumptions
- [ ] Before/after benchmarks included
- [ ] Profiling artifacts committed (`.prof` files in `benchmarks/profiles/`)

**Generator Expressions:**
- [ ] Original list comprehension only used once
- [ ] Memory savings measured and documented
- [ ] No accidental multiple iterations
- [ ] Type hints updated (list → Iterator)

**Data Structures:**
- [ ] Lookup patterns identified and documented
- [ ] Index structure maintains consistency
- [ ] Tests verify correctness of new index
- [ ] Memory overhead of index is acceptable

**Caching:**
- [ ] Cache key is deterministic and hashable
- [ ] Cache invalidation strategy documented
- [ ] Memory bounds configured (maxsize)
- [ ] Cache stats tracked and reported
- [ ] TTL configured for time-sensitive data

---

**Next Review:** End of Week 3 (or after 80% completion)
**Owner:** Engineering Team
**Reviewers:** TBD
