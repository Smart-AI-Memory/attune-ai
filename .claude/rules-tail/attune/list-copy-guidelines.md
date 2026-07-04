# Code Review Guidelines: Preventing Unnecessary List Copies

**Version:** 1.0
**Last Updated:** January 10, 2026
**Maintainer:** Engineering Team

## Overview

This document provides guidelines for code reviewers and developers to identify and prevent unnecessary list copy operations that can impact performance and memory usage in the Attune AI.

---

## 🎯 Quick Reference

### When List Copies Are GOOD
✅ **Defensive copying** - Preventing external modification
✅ **Transformations** - Creating new data structures
✅ **Serialization** - Converting objects to dicts
✅ **Thread safety** - Avoiding concurrent modification

### When List Copies Are BAD
❌ **sorted()[:N]** - Use `heapq.nlargest(N, ...)` instead
❌ **list(range(n))** - Use `range(n)` directly
❌ **list(set(...))** - Use `dict.fromkeys(...)` to preserve order
❌ **Unnecessary API conversions** - Use iterators when possible

---

## 📋 Checklist for Code Review

When reviewing code that involves lists, check for these patterns:

### 1. Top-N Queries (HIGH PRIORITY)

**❌ AVOID:**
```python
# Bad: O(n log n) and creates full sorted list
top_10 = sorted(items, key=lambda x: x.score, reverse=True)[:10]
```

**✅ PREFER:**
```python
# Good: More efficient, doesn't create intermediate list
import heapq
top_10 = heapq.nlargest(10, items, key=lambda x: x.score)

# For smallest N items:
bottom_10 = heapq.nsmallest(10, items, key=lambda x: x.score)
```

**When to use:**
- Getting top/bottom N items from a large collection
- Sorted result with `[:N]` slice
- Priority queues

**Performance impact:**
- Both are O(n log k) where k=N
- heapq has better constant factors
- Significant savings when N << len(items)

---

### 2. Deduplication (MEDIUM PRIORITY)

**❌ AVOID:**
```python
# Bad: Loses insertion order (pre-Python 3.7 behavior)
unique_items = list(set(items))
```

**✅ PREFER:**
```python
# Good: Preserves insertion order (Python 3.7+)
unique_items = list(dict.fromkeys(items))
```

**When to use:**
- Removing duplicates while maintaining order
- Processing user-visible lists where order matters
- Chaining operations where order is significant

**Performance impact:**
- Same time complexity: O(n)
- Same space complexity: O(n)
- Better semantic correctness

---

### 3. Range Conversions (LOW PRIORITY)

**❌ AVOID:**
```python
# Bad: Creates unnecessary list
indices = list(range(n))
for i in indices:
    process(i)
```

**✅ PREFER:**
```python
# Good: Use range directly
for i in range(n):
    process(i)

# Also good: When you need a sequence for iteration
for i, item in enumerate(items):
    process(i, item)
```

**Exception:** Only create list if you need random access or multiple iterations:
```python
# OK: Need to iterate multiple times
indices = list(range(n))
first_pass = [compute(i) for i in indices]
second_pass = [refine(i, first_pass[i]) for i in indices]
```

---

### 4. Dictionary/Set to List Conversions

**❌ AVOID (when unnecessary):**
```python
# Bad: Creates intermediate list when not needed
for key in list(my_dict.keys()):
    process(key)
```

**✅ PREFER:**
```python
# Good: Iterate directly
for key in my_dict:
    process(key)

# Good: When you need a list for API requirements
def get_all_keys() -> list[str]:
    return list(self._cache.keys())  # API requires list
```

**When list conversion IS necessary:**
- Function signature requires `list` return type
- Need to modify dict during iteration
- Need random access by index
- Serialization/JSON export

---

### 5. Filter Operations

**Generally OK:**
```python
# Usually fine: List comprehensions for filtering
active_users = [u for u in users if u.is_active]
```

**Consider generators for large datasets:**
```python
# Better for memory: Generator expression
active_users_gen = (u for u in users if u.is_active)

# Use when you can process items one at a time
for user in active_users_gen:
    send_email(user)
```

**When NOT to optimize:**
- Small lists (< 1000 items)
- Need multiple iterations over result
- Code clarity significantly reduced

---

## 🔍 Pattern Detection

### Automated Detection

Use these regex patterns in code review tools:

```regex
# Top-N antipattern
sorted\([^)]+\)\[:\d+\]

# list(set()) antipattern
list\(set\([^)]+\)\)

# list(range()) antipattern
list\(range\(

# Unnecessary dict.keys() conversion
list\([^)]+\.keys\(\)\)
```

### Manual Review Questions

Ask these questions during code review:

1. **Is the list copy necessary?**
   - Is the original data being modified?
   - Is thread safety required?
   - Is this for defensive programming?

2. **Could we use an iterator instead?**
   - Is the data only accessed once?
   - Would a generator work here?
   - Does the API actually require a list?

3. **Is there a better algorithm?**
   - Are we sorting just to get top N?
   - Are we deduplicating with order requirements?
   - Could we use a set/dict for O(1) lookups?

4. **What's the data size?**
   - < 100 items: Don't optimize, prioritize readability
   - 100-10,000 items: Consider optimization if in hot path
   - > 10,000 items: Optimize proactively

---

## 📊 Optimization Decision Matrix

| Operation | Small Data (<100) | Medium (100-10k) | Large (>10k) |
|-----------|-------------------|------------------|--------------|
| `sorted()[:N]` | OK | Consider heapq | Use heapq |
| `list(set())` | OK | Use dict.fromkeys | Use dict.fromkeys |
| `list(range())` | OK | Avoid | Avoid |
| List comprehension | OK | OK | Consider generator |
| `list(dict.keys())` | OK | Avoid if possible | Avoid |

---

## 💡 Best Practices

### 1. Document Intentional Copies

```python
# Good: Explains why copy is needed
def process_items(items: list[Item]) -> list[Item]:
    # Defensive copy - caller may modify original list
    items_copy = items.copy()
    items_copy.sort(key=lambda x: x.priority)
    return items_copy
```

### 2. Use Type Hints to Indicate Iteration

```python
# Good: Iterator type hints signal no list needed
def get_active_users() -> Iterator[User]:
    return (u for u in self._users if u.is_active)

# Also good: Explicit about list creation
def get_active_users_list() -> list[User]:
    return [u for u in self._users if u.is_active]
```

### 3. Profile Before Optimizing

```python
# Add profiling for optimization validation
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # Your code here
    result = expensive_operation()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)

    return result
```

---

## 🚫 Common Anti-Patterns

### Anti-Pattern 1: Double Sorting

```python
# Bad: Sorts twice
items = sorted(data, key=lambda x: x.score)
top_10 = sorted(items, reverse=True)[:10]

# Good: Single sort + slice OR heapq
top_10 = heapq.nlargest(10, data, key=lambda x: x.score)
```

### Anti-Pattern 2: Unnecessary List Construction

```python
# Bad: Creates list just for length check
if len(list(filter(lambda x: x.is_valid, items))) > 0:
    process()

# Good: Use any() with generator
if any(x.is_valid for x in items):
    process()
```

### Anti-Pattern 3: Multiple List Copies in Pipeline

```python
# Bad: Multiple intermediate lists
result = list(filter(validate, items))
result = list(map(transform, result))
result = sorted(result, key=lambda x: x.score)

# Good: Generator pipeline
from itertools import chain
result = sorted(
    (transform(item) for item in items if validate(item)),
    key=lambda x: x.score
)
```

---

## 🎓 Training Examples

### Example 1: Refactoring Top-N Pattern

**Before:**
```python
def get_high_priority_issues(self, issues: list[Issue]) -> list[Issue]:
    """Get top 10 high priority issues."""
    sorted_issues = sorted(
        issues,
        key=lambda i: (i.severity, -i.created_at.timestamp()),
        reverse=True
    )
    return sorted_issues[:10]
```

**After:**
```python
import heapq

def get_high_priority_issues(self, issues: list[Issue]) -> list[Issue]:
    """Get top 10 high priority issues."""
    return heapq.nlargest(
        10,
        issues,
        key=lambda i: (i.severity, i.created_at.timestamp())
    )
```

### Example 2: Preserving Order in Deduplication

**Before:**
```python
def get_unique_tags(self, articles: list[Article]) -> list[str]:
    """Get unique tags from articles."""
    all_tags = []
    for article in articles:
        all_tags.extend(article.tags)
    return list(set(all_tags))  # Order lost!
```

**After:**
```python
def get_unique_tags(self, articles: list[Article]) -> list[str]:
    """Get unique tags from articles (preserves order)."""
    all_tags = []
    for article in articles:
        all_tags.extend(article.tags)
    return list(dict.fromkeys(all_tags))  # Order preserved
```

---

## 📈 Performance Impact Examples

Based on benchmarks from our optimization effort (Jan 2026):

| Pattern | Before (ms) | After (ms) | Improvement |
|---------|-------------|------------|-------------|
| `sorted(1000)[:10]` | 0.52 | 0.31 | 40% faster |
| `sorted(10000)[:10]` | 6.8 | 2.1 | 69% faster |
| `sorted(100000)[:10]` | 89.2 | 18.4 | 79% faster |
| `list(set(1000))` | 0.08 | 0.08 | Same |
| `dict.fromkeys(1000)` | 0.09 | 0.09 | Same (+ order) |

**Key Takeaway:** Optimization impact scales with data size. Focus on hot paths with large datasets.

---

## ✅ Review Checklist

Use this checklist during code review:

- [ ] No `sorted()[:N]` patterns (use heapq instead)
- [ ] No `list(range())` antipattern (use range directly)
- [ ] Order-preserving deduplication uses `dict.fromkeys()`
- [ ] Defensive copies are documented
- [ ] Large list operations (>10k items) are optimized
- [ ] Generator expressions used for one-time iterations
- [ ] No double-sorting or redundant operations
- [ ] Type hints indicate when lists vs iterators are used

---

## 🔗 Related Resources

- [Python heapq documentation](https://docs.python.org/3/library/heapq.html)
- [Attune AI Coding Standards](./../../../docs/CODING_STANDARDS.md)
- [Advanced Optimization Plan](../../../docs/archive/planning/advanced-optimization-plan.md)
- [List copy optimization PR #XXX](https://github.com/Smart-AI-Memory/attune-ai/pulls)

---

## 📝 Changelog

**v1.0 (2026-01-10):**
- Initial release
- Added guidelines based on Jan 2026 optimization effort
- Covered top-N, deduplication, and range antipatterns
- Added performance benchmarks and examples

---

**Questions or suggestions?** Open an issue at [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)

**Maintained by:** Engineering Team
**Last Review:** January 10, 2026
