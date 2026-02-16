# XML vs Plain Text Benchmark Results

**Date:** 2026-02-15 21:48
**Models:** claude-sonnet-4-5-20250929
**Workflows:** security-audit, code-review, perf-audit
**Total calls:** 30
**Total cost:** $0.8701

---

## Summary

| Metric | XML | Plain | Delta |
|--------|-----|-------|-------|
| Parse success rate | 100% | 0% | +100% |
| Avg prompt tokens | 669.87 | 309.87 | +116% |
| Avg completion tokens | 2029.80 | 1641.20 | +24% |
| Avg cost per call | $0.0325 | $0.0255 | +27% |
| Avg latency (ms) | 32520.04 | 26014.60 | +25% |
| Avg completeness | 1.00 | 1.00 | +0% |
| Avg precision | 0.43 | 0.00 | N/A |
| Avg actionability | 1.00 | 1.00 | +0% |
| Avg consistency | 0.00 | 0.00 | N/A |
| Avg overall quality | 0.76 | 0.45 | +68% |

---

## Per-Workflow Breakdown


### security-audit

| Format | Parse % | Completeness | Precision | Actionability | Cost/call |
|--------|---------|-------------|-----------|---------------|-----------|
| XML | 100% | 1.00 | 0.41 | 1.00 | $0.0394 |
| Plain | 0% | 1.00 | 0.00 | 1.00 | $0.0343 |

### code-review

| Format | Parse % | Completeness | Precision | Actionability | Cost/call |
|--------|---------|-------------|-----------|---------------|-----------|
| XML | 100% | 1.00 | 0.51 | 1.00 | $0.0180 |
| Plain | 0% | 1.00 | 0.00 | 1.00 | $0.0115 |

### perf-audit

| Format | Parse % | Completeness | Precision | Actionability | Cost/call |
|--------|---------|-------------|-----------|---------------|-----------|
| XML | 100% | 1.00 | 0.38 | 1.00 | $0.0400 |
| Plain | 0% | 1.00 | 0.00 | 1.00 | $0.0308 |

---

## Cost Analysis

- XML total cost: $0.4868 (15 calls)
- Plain total cost: $0.3832 (15 calls)
- XML avg cost/call: $0.0325
- Plain avg cost/call: $0.0255
- **XML cost overhead: +27.0%**

XML cost overhead exceeds 25% threshold.

---

## Recommendation

- **security-audit**: ENABLE XML (+30% quality, +15% cost)
- **code-review**: KEEP PLAIN (Cost overhead too high (+56%))
- **perf-audit**: KEEP PLAIN (Cost overhead too high (+30%))
