---
type: comparison
name: telemetry-comparison
feature: telemetry
depth: comparison
generated_at: 2026-06-24T00:53:03.849694+00:00
source_hash: 70af5f419937014536c9522dee18a1346bb18f723c2ed51057c807380c66ee6b
status: generated
---

# Usage tracking, model-tier feedback loops, and agent-coordination signals

## Comparison

Telemetry is the **measurement** layer, distinct from the surfaces that
read it:

| | telemetry | ops-dashboard | usage-signals phone-home |
|--|-----------|---------------|--------------------------|
| Role | Records usage/quality/coordination | Renders it in a local web UI | Optionally reports anonymized signal |
| Locality | Local store under `~/.attune/telemetry` | Reads the local store | Network, opt-in only |
| Entry | `UsageTracker` / `FeedbackLoop` | `python -m attune.ops` | Consent-gated client |

`UsageTracker` answers "what did it cost"; `FeedbackLoop` answers "what
tier should this stage use"; the coordination classes answer "which
agents are alive."
