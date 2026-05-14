# Spec: Ops Sessions Page — Decisions

> Pre-committed decisions captured 2026-05-14.

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Data source | `~/.claude/projects/<encoded-current-project>/*.jsonl` | Canonical Claude Code session location; no parallel store to maintain. Project-keyed encoding is `path.replace('/', '-')`. |
| Time window | **Last 3 days** | Patrick's call. "I don't want to maintain dated and useless data." Older sessions stay on disk but aren't surfaced. |
| Project scope | **Current project only** | Patrick's call. Cross-project resume is a power-user feature; current-project handles the 80% case. |
| Starter-prompt generation | **Haiku-summarized** (`claude-haiku-4-5`) | Patrick's call. Sharper than heuristic. ~$0.001/session × ~10 sessions in 3-day window = ~$0.01 per uncached page load. |
| Heuristic fallback | First user prompt + last assistant turn, both truncated to ~200 chars | Used when LLM gate is off (`ATTUNE_OPS_SESSIONS_LLM=0`) OR Haiku call errors out. |
| Cache key | `(jsonl_filename, mtime, sha256_of_first_4kb)` | Detects edits to the file without paying for a full content hash. Cache hits are cheap on subsequent page loads. |
| Cache location | `<attune_home>/ops/session_summaries/<session-id>.json` | Keeps session-specific data under `attune_home`, separate from `~/.claude/projects/` which we don't write to. |
| Cache TTL | None (mtime-bound) | A file that hasn't changed since last summary doesn't need re-summarizing. |
| Budget cap per page load | `$0.05` | Hard cap; sessions beyond the cap render heuristic-only with a "summary unavailable — over budget" marker. Configurable via `[tool.attune-ops.sessions] budget_cap_usd`. |
| Listing route | `GET /sessions` (page) + `GET /api/sessions` (JSON) | Mirrors `/specs` + `/api/specs` and `/workflows` + `/api/runs/...`. |
| Listing JSON shape | `{sessions: [{id, started_at, last_activity, duration_seconds, message_count, starter_prompt, source}]}` where `source` ∈ `{"heuristic", "haiku", "cached"}` | Lets the UI show a "summarized by Haiku · cached" badge for transparency. |
| Expand-on-click body | Server-side render the first user message; full transcript stays at the JSONL file on disk (no in-page transcript viewer) | Keeps the page light. Users who want the full transcript can `cat` the JSONL. |
| Empty state | "No sessions in the last 3 days for this project. Older sessions are at `<path>`." | Tells the user where the data lives instead of pretending it doesn't. |
| Failure mode for unreadable JSONL | Skip with WARN log, don't surface as broken row | An unreadable file is a Claude Code internal issue, not something the user can fix from the dashboard. |

---

## Open questions (resolve during design phase)

1. **Project-path encoding edge cases.** Some users may have
   sessions for `~/attune-ai` (no leading `/Users/`) and
   `/Users/patrickroebuck/attune-ai` (canonical) — same project,
   different encoded keys. Decide whether to read multiple keys
   or canonicalize.

2. **Haiku prompt template.** The summarization prompt itself
   needs care — what makes a good "starter prompt" vs a bad one?
   Probably: name what was being worked on, list any open
   threads, suggest a 1-sentence resume prompt the user can
   paste. Calibrate against 5-10 real sessions before defaulting.

3. **Active prompt-redaction.** First user messages may contain
   API keys, file paths, or other sensitive info. The Haiku
   summary should not echo these verbatim. Add a redaction pass
   or rely on Haiku's natural summarization to drop specifics?

---

## Calibration record

To be filled in during implementation:

- [ ] Haiku prompt template — finalized text and 5-session test
  snapshot
- [ ] Average tokens per summary (in / out)
- [ ] Average cost per session summary
- [ ] Whether the budget cap ever fires during normal usage

---

## Decision-change log

- 2026-05-14 — Initial decisions captured during spec draft.
  Triggered by ops-dashboard QA punch list item P1-4. Memory
  page explicitly dropped per Patrick.
