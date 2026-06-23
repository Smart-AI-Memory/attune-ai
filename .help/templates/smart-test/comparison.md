---
type: comparison
name: smart-test-comparison
feature: smart-test
depth: comparison
generated_at: 2026-06-23T15:57:46.208360+00:00
source_hash: d6dccb651feffe160b811a9e8fef002ec3bb96ee10e3299e09f78b3c41c3cbbe
status: generated
---

# Find untested code with a coverage audit, then generate pytest tests to close the gaps

## Comparison

Smart-test and **deep-review** both surface test gaps, but only
smart-test generates the tests to close them.

| | `smart-test` | `deep-review` |
|---|---|---|
| **Scope** | Dedicated to test coverage: audit gaps, then generate tests | One pass of a broader review (security / quality / test gaps) |
| **Test-gap detection** | `test-audit` — three subagents focused on coverage | The `test-gap-reviewer` pass (one of three) |
| **Generates tests** | Yes — `test-gen` and the batch generator | No — it reports gaps, it does not write tests |
| **Slugs** | `attune workflow run test-audit` / `test-gen` | `attune workflow run deep-review` |

Reach for **smart-test** when the goal is coverage — find what's
untested and write tests for it. Reach for **deep-review** when you
want test gaps as one input alongside a security and quality read,
without generating anything. A common flow is deep-review (or
test-audit) to find the gaps, then test-gen to fill them. To repair
*failing* tests rather than write missing ones, see **fix-test**.
