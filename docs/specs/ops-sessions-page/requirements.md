# Spec: Ops Dashboard — Sessions Page

> Add a `/sessions` page to the ops dashboard surfacing the last 3
> days of Claude Code sessions for the **current project**, each with
> a Haiku-summarized starter-prompt for resuming.

---

## Phase 1: Requirements

**Status**: draft

### Problem statement

The 2026-05-14 QA punch list flagged that `/sessions` returns 404 —
no template exists (P1-4). Patrick confirmed: keep Sessions, drop
Memory, narrow scope. The use case: refreshing memory on what was
worked on across recent Claude Code sessions, so a new session can
start with context rather than from scratch.

Existing context-recovery surface today: re-reading transcripts
manually from `~/.claude/projects/<encoded-path>/`. Each transcript
is a `.jsonl` file with line-delimited messages — useful but
high-friction. A dashboard surface that lists recent sessions with
short summaries and copy-pasteable starter prompts is the UX win.

### Scope

**In scope:**

- New page `/sessions` in the ops dashboard.
- Data source: `~/.claude/projects/<encoded-current-project>/*.jsonl`
  where the encoding is the current-project absolute path with `/`
  replaced by `-`. The dashboard's `cfg.project_root` provides the
  unencoded path.
- Time window: only sessions with mtime within the last **3 days**.
- Scope: current project only (no cross-project listing).
- Per-session display (table or card layout):
  - Session id (short, ~8 chars of the UUID)
  - Started timestamp (relative + absolute on hover, matching the
    Updated column pattern on Specs)
  - Duration (last message timestamp minus first)
  - Message count
  - **Starter prompt** — Haiku-summarized one-paragraph summary +
    a suggested first prompt for resuming the session
- Click → expand to show the first user message in full (truncated
  to ~500 chars) plus a "Copy starter prompt to clipboard" button.
- A "Sessions older than 3 days are hidden" footer note so users
  understand the filter (not actively pruned from disk — Claude
  Code owns that).

**Out of scope:**

- Cross-project session listing
- Filtering / search beyond the time-window default
- Editing sessions
- Resuming a session in-process (just copies a starter prompt)
- Memory page (explicitly dropped by Patrick, 2026-05-14)

### Acceptance criteria

1. Navigating to `/sessions` returns HTTP 200 with a list of the
   project's sessions from the last 3 days, sorted newest first.
2. Each session row shows id, started time, duration, message
   count, and a Haiku-generated starter prompt.
3. Sessions older than 3 days are not shown.
4. Sessions with empty / unreadable JSONL files are skipped
   (logged at WARN, not surfaced as broken rows).
5. The Haiku summarization is gated by `ATTUNE_OPS_SESSIONS_LLM=1`
   or an equivalent opt-in; with the gate off, a heuristic summary
   (first user prompt + last assistant turn truncated) is used.
6. Session summaries are cached on disk under
   `<attune_home>/ops/session_summaries/<session-id>.json` keyed
   by the JSONL file's mtime+sha256, so the same session isn't
   re-summarized on every page load.
7. Total cost per full page load (assuming cache miss on every
   session shown) stays below `$0.05` — bounded by the 3-day
   window and Haiku pricing.

### Non-goals / explicitly deferred

- **Pruning Claude Code's sessions directory.** Not our job.
- **Live in-progress session detection.** Could be a Phase 2
  follow-up — the currently-running Claude Code instance has a
  PID and could be cross-referenced, but the read-only Sessions
  page can punt.
- **Cross-machine session sync.** Out of scope — sessions live
  on the local machine only.

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Encoded-path heuristic doesn't always match Claude Code's logic | Med | Read `~/.claude/projects/` directly, find the dir whose name is `cfg.project_root` with `/` → `-`; fall back to any single dir if there's only one (single-project user) |
| JSONL parsing is slow for many large sessions | Low | Only read the first line (start timestamp + first user message) and the file's mtime — no full parse for the listing view. Full parse only on expand. |
| Haiku summarization adds visible cost | Med | Cache aggressively; opt-in flag for first release; budget cap per page load |
| Summary quality varies | Low | Phase 1 ships heuristic + Haiku; if Haiku underperforms, fall back |
