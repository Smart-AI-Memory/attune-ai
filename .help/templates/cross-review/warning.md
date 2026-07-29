---
type: warning
name: cross-review-warning
feature: cross-review
depth: warning
generated_at: 2026-07-29T00:49:32.207827+00:00
source_hash: 68691bdb8533cb43d997bbec5457fa5ba004c65c48af6cfc90d4d4c8c87a638d
status: generated
---

# One-shot second-opinion diff review by a different-model seat, advisory only

## Failure modes

### Risk areas

- **Absent seat** — the seat CLI is missing or unauthenticated.
  The run records `absent` with the exit code and reply head; this
  is a valid outcome, not an error to retry blindly.
- **Board unreachable** — local Redis down. The review still runs;
  the result records `board: skipped (<reason>)`.
- **Oversized diff** — files beyond the 60k budget are omitted and
  named in the manifest. A review that saw only part of the diff
  says so everywhere the result renders.
- **Format noncompliance** — a seat that replies in prose is
  reported as `format_noncompliant` with the raw reply preserved.
  Findings are never fabricated from prose.

### Diagnosis order

1. `status` first: `absent` → check the seat CLI and its auth;
   `format_noncompliant` → read the raw reply.
2. `manifest` next: were the files you care about in `sent`?
3. `board` last: `skipped (...)` names the reason; the review
   itself is unaffected.
