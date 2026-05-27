# Decisions — Anthropic Files API adoption in attune-ai
**Status:** approved (2026-05-11) — gated on briefing-followup batch
**Owner:** Patrick

---

## Problem

attune-ai's perf-audit, security-audit, code-review,
deep-review, and other workflows send code payloads to the
Anthropic API by **inlining file contents into request
strings.** For small codebases this is fine. For larger ones
(multi-thousand-file repos, PDFs, large binary attachments),
this approach:

1. **Hits context-window limits** — request bodies grow with
   the codebase
2. **Re-uploads on every call** — no persistence; the same
   file goes over the wire each request
3. **Costs more** — input tokens include the full file content
   for each call

Anthropic's **Files API** addresses all three:

- Upload a file once; get a `file_id`
- Reference `file_id` in subsequent requests (saves token cost)
- Persists across calls within the upload's lifetime
- Works for text, code, PDFs, images

Today, **zero attune-ai files import the Files API.** No
`client.files.upload`, no `file_id` references in source.

## Decision

Adopt Files API in attune-ai workflows where context size is
the bottleneck. Phased adoption per workflow:

1. **Phase 1**: identify workflows hitting the inline-payload
   ceiling (size, cost, latency)
2. **Phase 2**: pilot Files API on ONE workflow (probably
   `code-review` or `perf-audit` — these have the largest
   payloads)
3. **Phase 3**: roll out to other workflows that benefit
4. **Phase 4**: cleanup story — uploaded files have a TTL but
   we should explicitly delete after use to keep the account
   tidy

## What's in scope

- Workflows where input payload exceeds ~50K tokens regularly
- Multi-file payloads (whole-repo scans)
- PDF inputs to perf-audit if those exist

## What's NOT in scope

- Migrating workflows whose payloads are <10K tokens (no win)
- Image uploads to multi-modal workflows (separate concern)
- Storing artifacts ACROSS workflows (Files API is
  per-conversation; long-term storage is a different system)

## Alternatives considered

1. **Leave as-is** — works today. Cost is real on big repos
   but not blocking. Acceptable for v6.7.x.
2. **Use prompt caching alone** — already in use. Helps with
   repeated calls but doesn't shrink any individual request.
   Complements Files API rather than replacing it.
3. **Custom client-side compression** (gzip payloads, etc.) —
   complex, doesn't address context limit (the API decompresses
   immediately).
4. **Switch to streaming completions only** — orthogonal;
   doesn't solve the upload-once problem.

## Acceptance criteria

- At least one workflow uses Files API end-to-end with
  upload → reference → use → cleanup
- Measurable token cost reduction on a representative payload
- Cleanup pattern documented and tested (no orphan uploads
  after CI runs)
- Spec closed with results

## Execution gate

Not urgent. Don't start until:

1. v6.7.x stable on PyPI
2. Probe C Phase 4 (-n auto restore) is settled
3. No active CI debt

---

(per-phase decisions appended as work happens)
