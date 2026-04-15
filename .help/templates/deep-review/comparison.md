---
type: comparison
feature: deep-review
depth: comparison
generated_at: 2026-04-14T14:55:32.104097+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Deep Review vs other code review approaches

## What deep review provides

Deep review orchestrates three specialized Claude agents to analyze your codebase across security, code quality, and test coverage gaps. Unlike single-pass reviews, it produces a consolidated report with severity rankings and specific file/line references.

The workflow coordinates these subagents:
- **security-reviewer** — identifies vulnerabilities and security anti-patterns
- **quality-reviewer** — flags maintainability and performance issues
- **test-gap-reviewer** — spots missing test coverage and weak assertions

## Feature comparison

| Aspect | Deep Review | Manual Code Review | Static Analysis Tools |
|--------|-------------|-------------------|---------------------|
| **Coverage** | Security + quality + tests in one pass | Depends on reviewer expertise | Tool-specific (usually single domain) |
| **Consistency** | Systematic across all three domains | Varies by reviewer and time pressure | High within tool scope |
| **Context awareness** | Understands code relationships | Excellent for business logic | Limited to syntax/patterns |
| **Setup time** | One workflow execution | No setup, immediate | Requires tool configuration |
| **Speed** | ~2-3 minutes for medium codebases | Hours for thorough review | Seconds to minutes |
| **False positives** | Moderate (AI interpretation) | Low (human judgment) | High (pattern matching) |

## Use deep review when

- You need comprehensive coverage across security, quality, and testing
- Your team lacks specialized security or testing expertise
- You want consistent review quality regardless of reviewer availability
- You're reviewing unfamiliar codebases and need systematic analysis
- You need actionable suggestions ranked by impact

## Use alternatives when

- **Manual review** — Business logic changes require human judgment about requirements
- **Static analysis** — You need zero false positives and can accept narrow scope
- **Simple linting** — You only care about style consistency, not architectural issues
- **Performance profiling** — You need runtime behavior data, not code structure analysis

## Recommendation

Start with deep review for general-purpose code health assessment. Its multi-domain approach catches issues that single-purpose tools miss, and the consolidated report format makes it easy to prioritize fixes. Supplement with manual review for business logic validation and static analysis for build pipeline enforcement.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`
