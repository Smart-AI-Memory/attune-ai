# Spec: Ops Sessions Page — Decisions

> Pre-committed decisions captured 2026-05-14.

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Data source | `~/.claude/projects/<encoded-canonical>*/*.jsonl` (prefix glob to catch worktree-encoded keys; see Project-key resolution below) | Canonical Claude Code session location; no parallel store to maintain. Project-keyed encoding is `path.replace('/', '-')`. |
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
| "Resume most recent" card | **Yes — prominent top-of-page card** | Patrick approved 2026-05-14. The newest session by mtime gets full-card treatment with the full Haiku summary, a copy button, and a resume-in-new-session hint. Dedupes against the list below it. |
| Live-session detection sources | (1) **`CLAUDE_CODE_SESSION_ID` env var — verified present 2026-05-15**; (2) mtime within last 5 min on a session JSONL as a fallback | The pointer-file (`~/.claude/__last_session`) hypothesis was disproved during design probe — file does not exist. Env var name corrected from `CLAUDE_SESSION_ID` to `CLAUDE_CODE_SESSION_ID`. |
| Live-session card behavior | "You're currently in this session" label, suppress the duplicate row in the list below | Avoids surfacing a "resume" prompt for a session that doesn't need resuming. |

---

## Resolved design questions

> All four open questions resolved 2026-05-15.

### 1. Project-key resolution — read multiple keys (prefix-globbed)

**Decision: read multiple encoded keys**, not canonicalize down
to one.

**Why.** Empirical scan of `~/.claude/projects/` on 2026-05-15
showed the worktree-development setup produces a key per
worktree, not per logical project. For attune-ai specifically:

- Canonical `-Users-patrickroebuck-attune-ai`: 44 sessions
- 47 distinct worktree-encoded keys
  (`-Users-patrickroebuck-attune-ai--claude-worktrees-<slug>`):
  57 sessions
- **93 sessions in the last 3 days across all keys**

Canonical-only lookup would miss the majority of recent
sessions in this dev pattern. Patrick's instinct was right;
the data forced the resolution.

**Implementation.**

- Compute encoded prefix from
  `Path(project_root).expanduser().resolve()` →
  `str.replace('/', '-')`.
- Glob `~/.claude/projects/<encoded>*` for matching dirs.
- Accept a dir iff its name equals `<encoded>` exactly, OR
  starts with `<encoded>-` (the `-` separator guards against
  sibling-project false matches like `attune-ai-something`).
- Read all `*.jsonl` from matched dirs.
- Dedup sessions by session-id (the JSONL filename's stem) —
  if a session somehow appears under multiple keys, the
  newest-mtime copy wins; log a WARN.

### 2. Haiku prompt template — calibration-driven

**Decision: design through a 5–10 session calibration pass
before defaulting.**

**Target output shape.** A starter prompt that:

1. Names what was being worked on (1 short sentence).
2. Lists any open threads (bullets, 0–3 items).
3. Suggests a 1-sentence resume prompt the user can paste.

**Calibration plan.** Pick 5–10 real sessions of varying
length from `~/.claude/projects/-Users-patrickroebuck-attune-ai*`;
run the candidate prompt against each; manually score the
output against the target shape. Iterate the template until
the median output is ship-worthy. The finalized prompt text
lands in the calibration record below.

### 3. Active prompt-redaction — yes, explicit pass

**Decision: add a redaction pass before sending to Haiku.**

**Why.** Relying on the model to "naturally summarize away"
sensitive content is non-deterministic — one session out of
fifty leaks a token verbatim into a cached summary and that's
a real incident. An explicit pass is cheap and bounded.

**Patterns to redact (initial set; extend as we learn).**

- API key shapes:
  `sk-ant-[a-zA-Z0-9_-]+`, `sk-[a-zA-Z0-9]{20,}`,
  `ghp_[a-zA-Z0-9]{36}`, `gho_…`, `ghu_…`, `xoxb-…`,
  `AKIA[0-9A-Z]{16}`, generic `[A-Za-z0-9]{40,}` tokens
  preceded by `key|token|secret|password` within 5 chars.
- Bearer-style headers: `Bearer [A-Za-z0-9._-]+`.
- Absolute paths under `~` or `/Users/<name>/` — replace
  with `<user-home>` or `<...>` (paths inside the project
  root are kept; they're useful context).
- IP addresses (RFC 1918 + public).
- Email addresses outside a small allowlist (Patrick's own
  emails per CLAUDE.md are fine; redact the rest).

**Order.** Redact first, then send to Haiku, then cache the
already-redacted summary. The cache never holds a sensitive
prompt; subsequent reads inherit the redaction for free.

### 4. Live-session detection — env var + mtime fallback

**Decision: 2-layer detection, env var primary.**

**Empirical findings (probed inside a Claude Code session
2026-05-15):**

- `CLAUDE_CODE_SESSION_ID` env var **is present**
  (e.g. `accc710d-5f39-46bb-bf8b-06d779a03291`). Note: the
  spec draft had this as `CLAUDE_SESSION_ID` — wrong name.
  Actual variable has the `CODE_` infix. Same value the
  JSONL file is named after.
- `~/.claude/__last_session` (and obvious variants
  `last_session`, `session`) **does not exist** on disk.
  Was a guess; dropping from the design.
- `~/.claude/sessions/` directory does exist but appears
  unrelated to per-project session detection — out of scope
  for this design.

**Implementation.**

1. Read `CLAUDE_CODE_SESSION_ID` from the dashboard's process
   env. If present, that's the live session.
2. Fallback: any `.jsonl` whose mtime is within the last 5
   minutes is considered "potentially live." If exactly one
   matches, treat as live. If multiple, no live indicator
   (don't guess).

The dashboard process inherits the env from whatever shell
launched it, which means: when launched from inside a Claude
Code session, the dashboard correctly detects "that
session." When launched from a plain shell, only the mtime
fallback fires.

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
- 2026-05-15 — All four open questions resolved before S3
  implementation. Two empirical probes drove the resolutions:
  (1) directory scan of `~/.claude/projects/` revealed
  multi-key reality (worktree-per-encoded-key), confirming
  Patrick's "read multiple keys" instinct; (2) env probe
  inside a Claude Code session corrected the live-session
  variable name (`CLAUDE_CODE_SESSION_ID`, not
  `CLAUDE_SESSION_ID`) and disproved the
  `~/.claude/__last_session` pointer-file hypothesis. Data
  source row updated for the prefix-glob; live-session
  detection row updated for the corrected env var. S1 + S2
  shipped in PR #377 prior to these resolutions; the
  multi-key fix applies to whichever future slice rewires
  `list_recent_sessions()` (S3 design pulls it forward).
