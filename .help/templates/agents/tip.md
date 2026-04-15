---
type: tip
feature: agents
depth: tip
generated_at: 2026-04-14T15:10:02.980145+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Use ReleasePrepTeam for comprehensive release quality checks

Start with `ReleasePrepTeam.assess_readiness()` to run all release agents in parallel and get a unified quality report. This gives you test coverage, documentation gaps, code quality issues, and security concerns in one call with automatic tier escalation when needed.

The team approach catches more issues than running individual agents because it applies consistent quality gates across all dimensions and provides a single approved/blocked decision for your release pipeline.

**Tradeoff:** Higher API costs upfront, but prevents expensive rollbacks from missing critical quality issues.
