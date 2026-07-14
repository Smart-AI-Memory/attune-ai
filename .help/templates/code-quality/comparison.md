---
type: comparison
name: code-quality-comparison
feature: code-quality
depth: comparison
generated_at: 2026-07-14T15:58:49.270997+00:00
source_hash: 1cda16e2ee597c3fc3187497350da0cf77783f31c42c22e4652888adb60ca679
status: generated
---

# Multi-subagent code review across security, quality, performance, and architecture

## Comparison

Code-quality (`code-review`) and **deep-review** are both
SDK-native review workflows reached with `attune workflow run
<slug>`, both async, both predictive (LLM judgment) — but they
trade a different mix of passes and one has a narrowing knob.

| | `code-quality` (`code-review`) | `deep-review` |
|---|---|---|
| **Passes** | Four: security, quality, performance, architecture | Three: security, quality, test gaps |
| **Subagents** | `security-` / `quality-` / `perf-` / `architect-reviewer` | `security-` / `quality-` / `test-gap-reviewer` |
| **Narrowing** | None — scope via `path` only | `focus` selects a subset of passes |
| **Turn budget** | 10 / 20 / 40 (quick / standard / deep) | 15 / 30 / 50 |
| **Report sections** | Summary / Security / Quality / Performance / Architecture / Suggestions | Summary / Security / Quality / Test Gaps / Suggestions |
| **Slug** | `attune workflow run code-review` | `attune workflow run deep-review` |

Reach for **code-quality** for the everyday maintainability read —
the performance and architecture passes catch coupling and
inefficiency that a test-focused review skips. Reach for
**deep-review** when test coverage is the concern, or when you want
to narrow to a single domain with `focus`. The `/code-quality`
skill's "deep" option runs deep-review for exactly this reason.
