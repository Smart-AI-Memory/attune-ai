---
type: comparison
name: deep-review-comparison
feature: deep-review
depth: comparison
generated_at: 2026-06-02T10:54:11.468921+00:00
source_hash: e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4
status: generated
---

# Comparison: Deep Review vs alternatives

## What deep review does

`deep_review` runs a multi-pass code review by coordinating three specialized subagents — `security-reviewer`, `quality-reviewer`, and `test-gap-reviewer` — in parallel, then synthesizes their findings into a single consolidated report. The report includes an overall health score (0–100), severity-ordered findings per domain, and up to ten prioritized next steps tied back to specific findings.

The entry point is `DeepReviewAgentSDKWorkflow.execute(**kwargs)` from `workflows.deep_review`.

## Feature comparison

| Criterion | `deep_review` | `code_review` | `security_audit` | `bug_predict` |
|---|---|---|---|---|
| **Passes** | 3 (security, quality, test gaps) | 1 | 1 (security only) | 1 (bug patterns only) |
| **Security findings** | ✅ Included | ⚠️ Surface-level | ✅ Primary focus | ❌ |
| **Code quality findings** | ✅ Included | ✅ Primary focus | ❌ | ❌ |
| **Test gap analysis** | ✅ Included | ❌ | ❌ | ❌ |
| **Consolidated report** | ✅ Single synthesized output | ❌ Per-pass output | ❌ Per-pass output | ❌ Per-pass output |
| **Health score (0–100)** | ✅ | ❌ | ❌ | ❌ |
| **Relative cost** | Higher — three subagents run per invocation | Lower | Lower | Lower |
| **Best for** | Pre-merge / release gates | Iterative development | Targeted security triage | Predicting regression risk |

## Tradeoffs

**`deep_review` wins when completeness matters.** Running all three subagents in one call means you get cross-domain findings in a single report, with the orchestrator citing file paths and line numbers across all domains. You don't have to reconcile the output of three separate tool calls yourself.

**`deep_review` costs more per call.** Because `security-reviewer`, `quality-reviewer`, and `test-gap-reviewer` all run for every invocation, using `deep_review` in a tight feedback loop (e.g., after every file save) is significantly more expensive than calling `code_review` alone. For quick, iterative checks during development, `code_review` is the better fit.

**`security_audit` is sharper for targeted security triage.** If you already have quality and test coverage under control and need the deepest possible security analysis, `security_audit` focuses all available capacity on that one domain instead of splitting it three ways.

**`bug_predict` solves a different problem entirely.** It analyzes code patterns to predict where bugs are likely to appear — a forward-looking signal, not a review of current state. It does not overlap with `deep_review`'s output.

## Use `deep_review` when…

- You are preparing a PR for merge and need a single authoritative report covering security, quality, and test gaps.
- Your team or CI pipeline requires a health score and a prioritized action list before a release.
- You want one consolidated output rather than manually correlating results from multiple tools.

## Use an alternative when…

| Situation | Better choice |
|---|---|
| Fast feedback during active development | `code_review` |
| Focused investigation of a potential vulnerability | `security_audit` |
| Estimating regression risk before a refactor | `bug_predict` |
| Exploratory work or a throwaway script | None — a direct inspection is faster than wiring up any workflow tool |

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`, `comprehensive-review`
