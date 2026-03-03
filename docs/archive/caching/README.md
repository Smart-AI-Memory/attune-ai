---
description: Caching Documentation: Complete guide to Attune AI's intelligent response caching system (v3.8.0+).
---

# Caching Documentation

Complete guide to Attune AI's intelligent response caching system (v3.8.0+).

## 📚 Documentation Index

### 🚀 [Quick Reference](QUICK_REFERENCE.md)
**Start here for common scenarios and quick answers.**

One-page reference covering:
- Common use cases with code examples
- Cache type comparison table
- Decision tree for choosing cache type
- Performance numbers and cost savings
- Troubleshooting guide

**Read this if:** You want quick answers and code snippets.

---

### ⚙️ [Configuration Guide](CONFIGURATION_GUIDE.md)
**Comprehensive guide to caching configuration.**

Detailed coverage of:
- Hash-only vs Hybrid cache selection
- When to enable/disable caching
- Configuration options (TTL, similarity threshold)
- Per-workflow configuration
- Cache maintenance and monitoring
- Performance benchmarks

**Read this if:** You want to understand all configuration options and make informed decisions.

---

### 🧠 [Adaptive Workflows](ADAPTIVE_WORKFLOWS.md)
**Understanding deterministic vs adaptive workflow behavior.**

In-depth explanation of:
- Workflow types (deterministic vs adaptive)
- The "Caching Paradox" - why adaptive workflows may cost more with cache
- Real-world Security Audit example
- Workflow classification table (12 workflows)
- When to use each approach
- Best practices for each type

**Read this if:** You noticed Run 2 costing more than Run 1 and want to understand why, or you're writing about caching for educational purposes.

---

## 🎯 Quick Start

### Default Setup (Recommended)

```python
from attune.workflows import CodeReviewWorkflow

# That's it! Framework handles cache setup automatically
workflow = CodeReviewWorkflow(enable_cache=True)
result = await workflow.execute(diff=my_diff)

# Check cache effectiveness
print(f"Cache hit rate: {result.cost_report.cache_hit_rate:.1f}%")
print(f"Savings: ${result.cost_report.savings_from_cache:.4f}")
```

### Explicit Cache Configuration

```python
from attune.cache import create_cache
from attune.workflows import SecurityAuditWorkflow

# Create cache instance
cache = create_cache(cache_type="hash")  # or "hybrid"

# Use with workflow
workflow = SecurityAuditWorkflow(cache=cache, enable_cache=True)
result = await workflow.execute(target_path="./src")
```

## 📊 Performance at a Glance

| Cache Type | Lookup Time | Memory | Hit Rate (Identical) | Hit Rate (Similar) |
|------------|-------------|--------|----------------------|-------------------|
| Hash-only  | ~5μs        | <1MB   | 100%                 | 0%                |
| Hybrid     | ~100ms      | ~500MB | 100%                 | 70-90%            |

**Cost Savings (v3.8.0 benchmarks):**
- Without cache: $0.856/run (12 workflows)
- With cache: $0.428/run (50% savings on repeated runs)

## 🔍 Which Document Should I Read?

### I want to...

**Get started quickly**
→ [Quick Reference](QUICK_REFERENCE.md)

**Understand cache types and when to use them**
→ [Configuration Guide](CONFIGURATION_GUIDE.md) - "Cache Types Compared"

**Configure TTL and similarity thresholds**
→ [Configuration Guide](CONFIGURATION_GUIDE.md) - "Configuration Options"

**Understand why Run 2 costs more than Run 1**
→ [Adaptive Workflows](ADAPTIVE_WORKFLOWS.md) - "The Caching Paradox"

**Learn which workflows are adaptive vs deterministic**
→ [Adaptive Workflows](ADAPTIVE_WORKFLOWS.md) - "Workflow Classification Table"

**Optimize cost savings**
→ [Configuration Guide](CONFIGURATION_GUIDE.md) - "Common Patterns"

**Debug cache issues**
→ [Quick Reference](QUICK_REFERENCE.md) - "Common Issues & Fixes"

**Monitor cache effectiveness**
→ [Configuration Guide](CONFIGURATION_GUIDE.md) - "Cache Statistics"

**Write about caching in educational material**
→ [Adaptive Workflows](ADAPTIVE_WORKFLOWS.md) - Comprehensive coverage of adaptive behavior

## 🧪 Testing Caching

### Quick Test (2-3 minutes)

```bash
python benchmark_caching_simple.py
```

Tests 2 workflows (code-review, security-audit) to verify cache is working.

### Full Benchmark (15-20 minutes)

```bash
python benchmark_caching.py
```

Tests all 12 production workflows and generates comprehensive report.

## 📁 Cache Storage

**Location:** `~/.empathy/cache/responses.json`

```bash
# View cache size
du -h ~/.empathy/cache/responses.json

# Clear cache
rm ~/.empathy/cache/responses.json

# Backup cache
cp ~/.empathy/cache/responses.json ~/.empathy/cache/responses.backup
```

## 🔧 Installation

### Hash-Only Cache (Default)

No additional installation required - included with Attune AI.

```bash
pip install attune-ai
```

### Hybrid Cache (Semantic Matching)

Install ML dependencies:

```bash
# Recommended: Install with cache extra
pip install attune-ai[cache]

# Or install dependencies separately
pip install sentence-transformers torch
```

## 💡 Key Concepts

### Hash-Only Cache
- **How it works:** SHA256 hash of prompt → exact match lookup
- **Best for:** CI/CD, testing, batch processing with identical inputs
- **Pros:** Fast (~5μs), zero dependencies, 100% hit rate on exact matches
- **Cons:** 0% hit rate on different prompts

### Hybrid Cache
- **How it works:** Hash lookup first, then semantic similarity search
- **Best for:** Development, production with similar prompts
- **Pros:** 70-90% hit rate on similar prompts, significant cost savings
- **Cons:** Slower (~100ms), requires ML dependencies, higher memory

### Adaptive Workflows
- **How it works:** Adjust execution based on findings (e.g., deeper analysis on critical issues)
- **Cache behavior:** May use more PREMIUM tier on Run 2 (smarter analysis)
- **Examples:** Security Audit, Bug Prediction, Performance Audit
- **Key insight:** Run 2 costing more is a FEATURE (better analysis), not a bug

### Deterministic Workflows
- **How it works:** Always execute same stages with same tiers
- **Cache behavior:** Run 2 costs ≤ Run 1 (predictable savings)
- **Examples:** Code Review, Test Generation, Document Generation
- **Key insight:** 100% cache hit rate on repeated runs

## 📈 Real-World Impact

### Scenario: Active Development Team

**Daily usage:**
- 20 security audits
- 30 code reviews
- 10 performance audits

**Without cache:**
- Daily cost: ~$15
- Monthly cost: ~$450

**With hybrid cache (70% hit rate):**
- Daily cost: ~$5
- Monthly cost: ~$150
- **Annual savings: ~$3,600**

### Scenario: CI/CD Pipeline

**Daily usage:**
- 100 test generation runs (identical inputs)

**Without cache:**
- Daily cost: ~$5
- Monthly cost: ~$150

**With hash-only cache (100% hit rate after first run):**
- Daily cost: ~$2.50
- Monthly cost: ~$75
- **Annual savings: ~$900**

## 🎓 Educational Use

The caching documentation, especially [Adaptive Workflows](ADAPTIVE_WORKFLOWS.md), is designed for educational purposes and can be incorporated into:

- **Book chapters** on LLM application optimization
- **Tutorials** on cost-effective AI application development
- **Case studies** demonstrating intelligent resource allocation
- **Training materials** for developers building LLM-powered tools

Key educational topics covered:
1. Deterministic vs adaptive workflow design
2. Cache effectiveness metrics and interpretation
3. Cost-quality trade-offs in AI applications
4. Intelligent resource allocation patterns

## 🆘 Support

- **Examples:** `tests/integration/test_cache_integration.py`
- **Issues:** [GitHub Issues](https://github.com/empathy-ai/attune-ai/issues)
- **Changelog:** [CHANGELOG.md](../../CHANGELOG.md#380---2026-01-06)

## 🔄 Version

This documentation is for **Attune AI v3.8.0+**.

For earlier versions, upgrade to v3.8.0:
```bash
pip install --upgrade attune-ai
```

## 📝 Contributing

Found an issue or have suggestions for improving the caching documentation?

1. Check existing [GitHub Issues](https://github.com/empathy-ai/attune-ai/issues)
2. Create new issue with label `documentation`
3. Include specific document and section

---

**Last updated:** 2026-01-06 (v3.8.0 release)
