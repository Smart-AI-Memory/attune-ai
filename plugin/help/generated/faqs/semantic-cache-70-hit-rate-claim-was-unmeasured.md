---
name: semantic-cache-70-hit-rate-claim-was-unmeasured
source: .claude/CLAUDE.md
summary: This template documents how the semantic cache's advertised 70% hit rate
  was discovered to be unmeasured, explains the technical reasons for the actual 0.2%
  hit rate (strict similarity threshold and non-repetitive prompts), and provides
  steps for validating performance claims against telemetry data before publication.
type: faq
---

# FAQ: Semantic Cache 70% Hit Rate Claim Was Unmeasured

## Answer

Internal telemetry data (`~/.attune/telemetry/usage.jsonl`, 17,264 requests) revealed a **0.2% actual hit rate**, saving $0.26 out of $72 in total costs — far below the documented 70% claim.

The discrepancy has two root causes:

- **High similarity threshold:** The 0.95 cosine similarity threshold is too strict for most real-world prompts to qualify as cache hits.
- **Non-repetitive prompt content:** Typical workflow prompts contain unique elements such as file paths, timestamps, and code snippets, which prevent near-matches from firing.

### Resolution

Always validate performance claims against actual telemetry before publishing documentation:

1. Locate the telemetry log:
   ```
   ~/.attune/telemetry/usage.jsonl
   ```
2. Measure the cache hit rate and cost savings over a representative sample of requests.
3. Update or retract any claims that do not reflect measured behavior.

## Related Topics

- [Error Reference: Semantic Cache 70% Hit Rate Claim Was Unmeasured](#)
