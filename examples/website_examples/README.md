# Website Examples: 3 Things That Weren't Possible Before

These standalone examples demonstrate what persistent memory enables for developers. Each example is self-contained and can be run independently.

---

## Quick Start

```bash
pip install attune-ai
cd examples/website_examples
python 01_bug_correlation.py
```

---

## Example 1: Bug Pattern Correlation

**File:** `01_bug_correlation.py`

**The Problem:** Every debugging session starts from zero. Your AI doesn't remember past bugs or how they were fixed.

**The Solution:** AI that remembers past bugs and recommends proven fixes.

```python
result = await wizard.analyze({
    "error_message": "TypeError: Cannot read property 'map' of undefined",
    "file_path": "src/components/UserList.tsx",
    "correlate_with_history": True,  # Enable historical matching
})

# Output:
# 📚 HISTORICAL MATCH FOUND:
#    Similarity: 87%
#    Root Cause: API returned null instead of empty array
#    Fix Applied: data?.items ?? []
#    Resolution Time: 15 minutes
```

**Key Capability:** What Sarah learned 3 months ago helps Mike today.

---

## Example 2: Tech Debt Trajectory

**File:** `02_tech_debt_trajectory.py`

**The Problem:** Debt count is just a number—no context, no trends, no prediction of when it becomes critical.

**The Solution:** AI that tracks debt over time and predicts future problems.

```python
result = await wizard.analyze({
    "project_path": ".",
    "track_history": True,  # Enable trajectory analysis
})

# Output:
# 📈 TRAJECTORY:
#    Previous (30 days ago): 47 items
#    Current: 72 items
#    Change: +53%
#    Trend: INCREASING
#
# 🔮 PROJECTIONS:
#    In 90 days: 150 items
#    ⚠️ Days until critical: 85
```

**Key Capability:** Justify cleanup time with data. Predict when debt becomes unmanageable.

---

## Example 3: Security False Positive Learning

**File:** `03_security_learning.py`

**The Problem:** Same false positives flagged every scan. Security alert fatigue.

**The Solution:** AI that learns from team decisions and suppresses known acceptable risks.

```python
result = await wizard.analyze({
    "project_path": ".",
    "apply_learned_patterns": True,  # Apply team decisions
})

# Output:
# 🧠 LEARNING APPLIED:
#    Suppressed: 8 findings
#    Noise Reduction: 40%
#
#    Suppression Details:
#    • sql_injection
#      Decision: false_positive by @sarah
#      Reason: "ORM handles SQL escaping"
```

**Key Capability:** AI learns your team's security policies. Review once, suppress forever.

---

## The Key Insight

| Before (Stateless) | After (Memory-Enhanced) |
|-------------------|------------------------|
| Debugging starts from zero | Correlates with past bugs |
| Debt is just a number | Trajectory analysis + predictions |
| Same alerts every scan | Learns team decisions |

**Memory changes everything.**

---

## How It Works

### Git-Based Pattern Storage (Zero Infrastructure)

```
./patterns/
├── debugging/
│   └── bug_20250915_abc123.json
├── tech_debt/
│   └── debt_history.json
└── security/
    └── team_decisions.json
```

- Patterns stored in your repo
- Version-controlled like code
- No Redis required for long-term storage
- Works for students and individual developers

### Optional Redis (Team Coordination)

```bash
pip install 'attune-ai[memory]'  # Redis auto-detected
```

- Real-time multi-agent coordination
- Sub-millisecond queries
- Team-wide pattern sharing

---

## Installation

```bash
pip install attune-ai
```

---

## Links

- **Full Demo:** `python ../persistent_memory_showcase.py`
- **Documentation:** [docs](https://github.com/Smart-AI-Memory/attune-ai/tree/main/docs)
- **GitHub:** [attune-ai](https://github.com/Smart-AI-Memory/attune-ai)

---

*Copyright 2025 Smart AI Memory, LLC — Apache License 2.0*
