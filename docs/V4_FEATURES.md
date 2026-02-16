---
description: Attune AI v4.0.0 - Meta-Orchestration Features: **Release Date:** January 2026 **Status:** Production Ready **Breaking Changes:** None (fully backward c
---

# Attune AI v4.0.0 - Meta-Orchestration Features

**Release Date:** January 2026
**Status:** Production Ready
**Breaking Changes:** None (fully backward compatible)

---

## 🎯 What's New in v4.0

Version 4.0 introduces **Meta-Orchestration** - workflows that use real analysis tools instead of simulated data. This enables accurate, trustworthy assessments of your codebase's health and release readiness.

### Key Features

1. **Orchestrated Health Check** - Comprehensive codebase analysis
2. **Orchestrated Release Prep** - Quality gate validation for releases
3. **VSCode Extension Integration** - One-click access from dashboard

---

## ✅ Orchestrated Health Check

### What It Does

Runs real analysis tools to assess your codebase's health across multiple dimensions:

- **Security Audit** - Scans for vulnerabilities using Bandit
- **Code Quality** - Analyzes code with Ruff and MyPy
- **Test Coverage** - Measures actual test coverage with pytest-cov
- **Performance** - (Optional) Checks for performance issues

### How to Use

**Command Line:**
```bash
# Daily check (3 agents: Security, Coverage, Quality)
attune orchestrate health-check --mode daily

# Weekly check (5 agents: adds Performance, Documentation)
attune orchestrate health-check --mode weekly

# Release check (6 agents: comprehensive validation)
attune orchestrate health-check --mode release
```

**VSCode Extension:**
1. Open Empathy Dashboard (sidebar)
2. Scroll to "META-ORCHESTRATION (v4.0)" section
3. Click "Health Check" button
4. Results open in dedicated panel

### Example Output

```
======================================================================
PROJECT HEALTH CHECK REPORT (Meta-Orchestrated)
======================================================================

Overall Health: ✅ 84.6/100 (Grade B)
Mode: DAILY
Agents Executed: 3
Duration: 4.22s

----------------------------------------------------------------------
CATEGORY BREAKDOWN
----------------------------------------------------------------------
✅ Security        100.0/100 (weight: 30%) ████████████████████
✅ Quality          99.5/100 (weight: 20%) ███████████████████
❌ Coverage         54.3/100 (weight: 25%) ██████████
     • Coverage below 80% (54.3%)

----------------------------------------------------------------------
🚨 ISSUES FOUND (1)
----------------------------------------------------------------------
  • Coverage below 80% (54.3%)

----------------------------------------------------------------------
💡 RECOMMENDATIONS (2)
----------------------------------------------------------------------
  • 🧪 Increase test coverage to 80%+ (currently 54.3%)
  •    → Run: attune orchestrate test-coverage --target 80
```

### Grading Scale

- **A (90-100)**: Excellent - production ready
- **B (80-89)**: Good - minor improvements needed
- **C (70-79)**: Fair - address issues before release
- **D (60-69)**: Poor - significant work needed
- **F (0-59)**: Failing - not ready for production

### Real Tools Used

- **Bandit** - Security vulnerability scanner
- **Ruff** - Fast Python linter
- **MyPy** - Static type checker
- **pytest-cov** - Test coverage measurement

---

## ✅ Orchestrated Release Prep

### What It Does

Validates your codebase against quality gates before releasing:

- **Security Gate** - No high/critical vulnerabilities
- **Coverage Gate** - Minimum 80% test coverage
- **Quality Gate** - Code quality score ≥ 7/10
- **Documentation Gate** - 100% API documentation

### How to Use

**Command Line:**
```bash
# Check if project is ready for release
attune orchestrate release-prep --path .

# Example output shows which gates pass/fail
```

**VSCode Extension:**
1. Open Empathy Dashboard
2. Click "Release Prep" button in v4.0 section
3. Review quality gates in dedicated panel

### Example Output

```
======================================================================
RELEASE READINESS REPORT (Meta-Orchestrated)
======================================================================

Status: ❌ NOT READY
Confidence: LOW
Duration: 4.56s

----------------------------------------------------------------------
QUALITY GATES
----------------------------------------------------------------------
✅ Security: ✅ PASS (actual: 0.0, threshold: 0.0)
🔴 Test Coverage: ❌ FAIL (actual: 54.3, threshold: 80.0)
✅ Code Quality: ✅ PASS (actual: 9.9, threshold: 7.0)
⚠️ Documentation: ❌ FAIL (actual: 97.8, threshold: 100.0)

----------------------------------------------------------------------
🚫 RELEASE BLOCKERS
----------------------------------------------------------------------
  • Test Coverage failed: Test Coverage: ❌ FAIL (actual: 54.3, threshold: 80.0)

----------------------------------------------------------------------
EXECUTIVE SUMMARY
----------------------------------------------------------------------
❌ RELEASE NOT APPROVED

Critical quality gates failed. Address blockers before release.

Quality Gate Summary:
  Passed: 2/4
  Failed:
    • Test Coverage: 54.3 < 80.0
    • Documentation: 97.8 < 100.0
```

### Quality Gates Explained

| Gate | Threshold | Description |
|------|-----------|-------------|
| **Security** | 0 issues | No high/critical vulnerabilities |
| **Test Coverage** | 80% | Minimum code coverage by tests |
| **Code Quality** | 7.0/10 | Linting + type checking score |
| **Documentation** | 100% | All public APIs documented |

---

## 🔧 Configuration

### Prerequisites

Install analysis tools (most are already included):

```bash
pip install bandit ruff mypy pytest pytest-cov
```

### Optional: Customize Thresholds

Create or edit `empathy.config.yml`:

```yaml
orchestration:
  health_check:
    modes:
      daily:
        agents: ["security", "coverage", "quality"]
        coverage_threshold: 80
        quality_threshold: 7.0
      weekly:
        agents: ["security", "coverage", "quality", "performance", "documentation"]
      release:
        agents: ["security", "coverage", "quality", "performance", "documentation", "dependencies"]

  release_prep:
    quality_gates:
      security_threshold: 0  # No high/critical issues
      coverage_threshold: 80  # 80% minimum coverage
      quality_threshold: 7.0  # 7/10 quality score
      documentation_threshold: 100  # 100% documented APIs
```

---

## 🆚 v4.0 vs v3.x

### What Changed?

| Feature | v3.x | v4.0 |
|---------|------|------|
| **Health Check** | Simulated data | Real analysis tools |
| **Release Prep** | Basic checks | Quality gates with real tools |
| **Accuracy** | Mock metrics | Actual codebase metrics |
| **Performance** | Instant (<1s) | Real analysis (3-5s) |
| **Trust** | ❌ Not trustworthy | ✅ Production-grade |

### Migration Path

**Good news:** v4.0 is fully backward compatible!

- Old workflows still work (`health-check`, `release-prep`)
- New workflows use `-orchestrated` prefix (`orchestrated-health-check`)
- VSCode extension automatically uses v4.0 versions

**Recommended:**
- Use `orchestrated-health-check` instead of `health-check`
- Use `orchestrated-release-prep` instead of `release-prep`
- Old versions are deprecated but won't be removed

---

## 🐛 Troubleshooting

### "Coverage report not found"

**Problem:** Release Prep fails with "Coverage report not found"

**Solution:** Generate coverage data first:
```bash
pytest tests/ --cov=src --cov-report=json
attune orchestrate release-prep --path .
```

**Why:** The workflow uses existing coverage data to avoid re-running tests every time.

---

### "Bandit not available"

**Problem:** Health Check shows "Bandit not available or returned invalid JSON"

**Solution:** Install bandit:
```bash
pip install bandit
```

---

### Health Check is Slow (>30s)

**Problem:** Health check takes a long time

**Cause:** First run generates coverage data (runs all tests)

**Solution:**
- Subsequent runs use cached coverage (< 5s)
- Coverage cache expires after 1 hour
- Use `--mode daily` for faster checks (3 agents vs 5-6)

---

## 📊 Performance

### Execution Times (Measured on Attune AI - 63,690 LOC)

| Workflow | Mode | First Run | Cached Run | Speedup | Agents |
|----------|------|-----------|------------|---------|--------|
| Health Check | daily | 207.89s | 0.42s | **481x** | 3 |
| Health Check | weekly | 207.90s | 0.90s | **231x** | 5 |
| Health Check | release | 207.90s | 0.90s | **231x** | 6 |
| Release Prep | N/A | 207.92s | 0.92s | **226x** | 4 (parallel) |

### Performance Optimizations (v4.0.0)

**1. Incremental Coverage Analysis (9.8x speedup on cached runs)**
- Uses cached `coverage.json` if <1 hour old
- Skips running 1310 tests when no files changed
- Result: 0.43s vs 4.22s (previous v4.0 without optimization)

**2. Parallel Test Execution (1.4x speedup on first run)**
- Uses pytest-xdist with `-n auto` flag
- Runs on 3-4 CPU cores automatically
- Result: 207.89s vs 296s (sequential execution)
- CPU efficiency: 330% = 3.3 cores utilized

**3. Incremental Security Scanning (19x speedup)**
- Git-based change detection
- Scans only modified files instead of entire codebase
- Result: 0.2s vs 3.8s (full scan)

**Note:** First run generates coverage by running all tests (207s). Subsequent runs use cached data.

---

## 🔍 What's Not Included

### Coverage Boost (Disabled)

The `test-coverage-boost` workflow is **disabled** in v4.0.0:

**Why:** Poor quality results (0% test pass rate), not ready for production

**Status:** Being redesigned for future release

**Alternative:** Use direct test generation:
```bash
attune workflow run test-gen --path src/your_module.py
```

---

## 💡 Best Practices

### 1. Run Health Check Daily

Add to your development routine:
```bash
# Start of day: check codebase health
attune orchestrate health-check --mode daily
```

### 2. Run Release Prep Before Releases

Before creating a release:
```bash
# Validate quality gates
attune orchestrate release-prep --path .

# If all gates pass, proceed with release
git tag v1.0.0
git push --tags
```

### 3. Use VSCode Extension

For the best UX:
- Install Attune AI VSCode extension
- Click buttons instead of typing commands
- Results open in dedicated panels with rich formatting

---

## 🎓 Advanced Usage

### Custom Agent Teams

Create custom health check modes:

```python
from attune.workflows.orchestrated_health_check import OrchestratedHealthCheckWorkflow

# Custom mode with specific agents
workflow = OrchestratedHealthCheckWorkflow()
result = workflow.execute({
    "mode": "custom",
    "agents": ["security", "quality"],  # Only these two
    "project_root": "."
})

print(f"Health Score: {result.overall_health}/100")
```

### Programmatic Access

Use in Python scripts:

```python
from attune.workflows import OrchestratedHealthCheckWorkflow

# Run health check
workflow = OrchestratedHealthCheckWorkflow()
result = workflow.execute({"mode": "daily"})

# Check if project is healthy
if result.overall_health >= 80:
    print("✅ Project is healthy!")
else:
    print(f"⚠️  Health score: {result.overall_health}/100")
    for issue in result.issues:
        print(f"  - {issue}")
```

---

## 📚 Related Documentation

- [CHANGELOG.md](../CHANGELOG.md) - Full release notes
- [CODING_STANDARDS.md](CODING_STANDARDS.md) - Framework coding standards
- [API Reference](api/workflows.md) - Workflow API documentation

---

## 🙋 FAQ

**Q: Do I need to install anything new?**
A: Most tools are included. Optionally install: `bandit`, `ruff`, `mypy`

**Q: Will v4.0 break my existing workflows?**
A: No! Fully backward compatible. Old workflows still work.

**Q: Why is the first health check slow?**
A: It runs all tests to measure coverage. Subsequent checks use cached data (~4s).

**Q: Can I customize quality gates?**
A: Yes! Edit `empathy.config.yml` (see Configuration section).

**Q: What happened to Coverage Boost?**
A: Disabled due to poor quality (0% pass rate). Being redesigned.

---

**Ready to try v4.0?**

```bash
# Install/upgrade
pip install attune-ai --upgrade

# Run your first health check
attune orchestrate health-check --mode daily
```

**Questions?** Open an issue at [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
