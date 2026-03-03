---
description: Adaptive Workflows and Caching Behavior: ## Overview The Attune AI uses two types of workflow execution strategies: **Deterministic** and **Adaptive**.
---

# Adaptive Workflows and Caching Behavior

## Overview

The Attune AI uses two types of workflow execution strategies: **Deterministic** and **Adaptive**. Understanding the difference is crucial for predicting costs and interpreting cache performance.

## Workflow Types

### Deterministic Workflows

**Characteristics:**
- Always execute the same stages in the same order
- Use the same model tiers for each stage
- Produce consistent costs for identical inputs
- Cache hit rate approaches 100% on repeated runs

**Examples:**
- **Code Review**: Fixed analysis pattern regardless of findings
- **Document Generation**: Consistent structure for same input code
- **Test Generation**: Same code produces same test suite
- **Keyboard Shortcuts**: Feature set determines shortcut assignments

**Cost Prediction:**
```python
# Deterministic workflow costs
Run 1: $0.00478  (0% cache hit - cold)
Run 2: $0.00478  (50% cache hit - warm)
Run 3: $0.00478  (100% cache hit - fully warm)

# Tier usage is identical:
Run 1: CHEAP $0.00048, CAPABLE $0.00430
Run 2: CHEAP $0.00048, CAPABLE $0.00430  # Same!
```

### Adaptive Workflows

**Characteristics:**
- Adjust execution based on findings
- May use different tiers based on severity
- Costs vary based on what's discovered
- Cache enables SMARTER analysis (not just faster)

**Examples:**
- **Security Audit**: Deep dive on critical vulnerabilities
- **Bug Prediction**: Extra analysis on complex code patterns
- **Performance Audit**: Deeper profiling on bottlenecks
- **Health Check**: More investigation when issues found

**Cost Pattern:**
```python
# Adaptive workflow costs
Run 1: $0.1127  (0% cache hit - slow discovery)
Run 2: $0.1339  (40% cache hit - SMARTER!)

# Tier usage adapts:
Run 1: CHEAP $0.0061, CAPABLE $0.0740, PREMIUM $0.0325
Run 2: CHEAP $0.0061, CAPABLE $0.0740, PREMIUM $0.0538  # More premium!

# Why? Run 2 found issues faster (cached early stages)
# → Had more time/budget for deep PREMIUM analysis
# → Better security assessment!
```

## The Caching Paradox

### Deterministic Workflows: Cache = Faster + Cheaper
```
Without cache: 30 seconds, $0.05
With cache:     2 seconds, $0.025 ✅
```

### Adaptive Workflows: Cache = Smarter (May Cost More)
```
Without cache: 45 seconds, $0.10 (surface scan)
With cache:    15 seconds, $0.12 (deep analysis) ✅

Why the extra cost?
- Cached early stages free up 30 seconds
- Workflow uses saved time for PREMIUM tier analysis
- Finds security vulnerabilities missed in Run 1
- Extra $0.02 cost = Better security assessment
```

## When Each Approach Makes Sense

### Use Deterministic When:
1. **Consistency is critical** - Same input must produce same output
2. **Cost predictability needed** - Budget constraints are tight
3. **Reproducibility matters** - Testing, documentation, code generation
4. **No intelligence benefit** - More analysis doesn't yield better results

### Use Adaptive When:
1. **Intelligence matters** - Quality > Cost
2. **Severity varies** - Some issues need deep investigation
3. **ROI-driven** - Worth paying more for critical findings
4. **Time-sensitive** - Cache enables thorough analysis in less time

## Real-World Impact

### Example: Security Audit

**Scenario**: Codebase with SQL injection vulnerability

**Deterministic Approach** (hypothetical):
```python
1. Scan files (CHEAP): 10 seconds → Found SQL injection
2. Categorize (CAPABLE): 5 seconds → Tagged as critical
3. Deep analysis (PREMIUM): 5 seconds → Analyzed 3 issues (fixed budget)
4. Total: 20 seconds, $0.10

Issues found: SQL injection
Issues missed: Related XSS, potential exploit chain
```

**Adaptive Approach** (actual):
```python
Run 1 (cold cache):
1. Scan files (CHEAP): 10 seconds → Found SQL injection
2. Categorize (CAPABLE): 5 seconds → Tagged as critical
3. Deep analysis (PREMIUM): 5 seconds → Started critical analysis
4. Total: 20 seconds, $0.10

Run 2 (warm cache):
1. Scan files (CHEAP): 0.1 seconds → Cache hit!
2. Categorize (CAPABLE): 0.1 seconds → Cache hit!
3. Deep analysis (PREMIUM): 7 seconds → FULL critical analysis
4. Exploit chain (PREMIUM): 5 seconds → Check related vulnerabilities
5. Remediation (PREMIUM): 3 seconds → Detailed fix recommendations
6. Total: 15 seconds, $0.13

Issues found: SQL injection + XSS + exploit chain + mitigations
Extra value: $0.03 cost → Prevented security breach
```

## Configuration

### Making a Workflow Deterministic

If you need deterministic behavior for an adaptive workflow:

```python
from attune.workflows import SecurityAuditWorkflow

# Standard adaptive behavior
workflow = SecurityAuditWorkflow(
    enable_cache=True,
    adaptive_depth=True  # Default
)

# Force deterministic behavior
workflow = SecurityAuditWorkflow(
    enable_cache=True,
    adaptive_depth=False,  # Disable adaptive logic
    max_premium_calls=3    # Fixed budget
)
```

### Monitoring Adaptive Behavior

```python
result = await workflow.execute(target_path="./src")

print(f"Total cost: ${result.cost_report.total_cost:.4f}")
print(f"Tier breakdown:")
print(f"  CHEAP:   ${result.cost_report.by_tier['cheap']:.4f}")
print(f"  CAPABLE: ${result.cost_report.by_tier['capable']:.4f}")
print(f"  PREMIUM: ${result.cost_report.by_tier['premium']:.4f}")

# Track adaptivity
if result.cost_report.by_tier['premium'] > expected_premium_cost:
    print("⚠️ Workflow adapted - found critical issues requiring deep analysis")
```

## Benchmarking Adaptive Workflows

When benchmarking adaptive workflows:

1. **Expect cost variance** - Not a bug, it's intelligence!
2. **Compare value, not just cost** - Did you get better insights?
3. **Measure tier usage** - Track PREMIUM tier changes
4. **Assess findings** - More expensive runs often find more issues

### Example Benchmark Interpretation

```
Security Audit Results:
  Run 1: $0.11 - Found 3 issues (surface scan)
  Run 2: $0.13 - Found 7 issues (deep analysis)

Interpretation: ✅ GOOD
  - Cache enabled smarter analysis
  - Extra $0.02 found 4 additional vulnerabilities
  - ROI: $0.02 cost → Prevented potential security breach
```

## Workflow Classification Table

| Workflow | Type | Why | Cost Variance |
|----------|------|-----|---------------|
| Code Review | Deterministic | Same diff = same review needed | <5% |
| Security Audit | **Adaptive** | Critical issues need deep analysis | 20-40% |
| Bug Prediction | **Adaptive** | Complex code needs more scrutiny | 15-30% |
| Refactor Planning | **Adaptive** | Scope based on code complexity | 10-25% |
| Health Check | **Adaptive** | Problems trigger investigation | 20-35% |
| Test Generation | Deterministic | Same code = same tests | <5% |
| Performance Audit | **Adaptive** | Bottlenecks need profiling | 15-30% |
| Dependency Check | **Adaptive** | Vulnerabilities need research | 10-20% |
| Document Gen | Deterministic | Consistent docs desired | <5% |
| Release Prep | **Adaptive** | Major releases need more checks | 10-25% |
| Research Synthesis | **Adaptive** | Complex sources need deep analysis | 15-25% |
| Keyboard Shortcuts | Deterministic | Features → shortcuts (fixed) | <5% |

## Best Practices

### For Deterministic Workflows
1. ✅ Enable caching for cost reduction
2. ✅ Expect 100% cache hit rates on repeated runs
3. ✅ Use for CI/CD where consistency matters
4. ✅ Budget accurately (costs are predictable)

### For Adaptive Workflows
1. ✅ Enable caching for SMARTER analysis
2. ✅ Budget for variance (use max observed cost)
3. ✅ Value findings over raw cost
4. ✅ Monitor tier usage to understand adaptation
5. ⚠️ Don't compare Run 1 vs Run 2 costs directly
6. ✅ Compare findings quality instead

## Conclusion

**Adaptive workflows are not more expensive - they're more intelligent.**

When cache enables an adaptive workflow to find 4 additional security vulnerabilities for an extra $0.02, that's not a cost increase - it's an investment in code quality that would cost far more to fix in production.

The framework's caching system doesn't just make workflows faster - it makes them **smarter** by freeing up time and resources for deeper, more valuable analysis where it matters most.
