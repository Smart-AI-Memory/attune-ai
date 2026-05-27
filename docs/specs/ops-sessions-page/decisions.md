# Spec: Ops Sessions Page — Decisions

**Status:** approved


> Pre-committed decisions captured 2026-05-14.

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Data source | `~/.claude/projects/<encoded-canonical>*/*.jsonl` (prefix glob to catch worktree-encoded keys; see Project-key resolution below) | Canonical Claude Code session location; no parallel store to maintain. Project-keyed encoding is `path.replace('/', '-')`. |
| Time window | **Last 3 days** | Patrick's call. "I don't want to maintain dated and useless data." Older sessions stay on disk but aren't surfaced. |
| Project scope | **Current project only** | Patrick's call. Cross-project resume is a power-user feature; current-project handles the 80% case. |
| Starter-prompt generation | **Haiku-summarized** (`claude-haiku-4-5`) | Patrick's call. Sharper than heuristic. ~$0.001/session × N=20 cap = ~$0.02/uncached load. |
| Heuristic fallback | First user prompt + last assistant turn, both truncated to ~200 chars | Used when LLM gate is off (`ATTUNE_OPS_SESSIONS_LLM=0`) OR Haiku call errors out. |
| Cache key | `(jsonl_filename, mtime, sha256_of_last_4kb)` | Hashes the JSONL tail — which actually changes as the session grows — rather than the byte-identical opening block. Single seek + read. See Cache-key collision below. |
| Cache location | `<attune_home>/ops/session_summaries/<session-id>.json` | Keeps session-specific data under `attune_home`, separate from `~/.claude/projects/` which we don't write to. |
| Cache TTL | None (mtime-bound) | A file that hasn't changed since last summary doesn't need re-summarizing. |
| List cap | **N=20 most-recent sessions** | Bounds Haiku spend per page load (~$0.02 worst case). Older sessions stay on disk for `cat`, not surfaced in the list. The Resume-most-recent card is unaffected and reads independently. See Budget-cap math below. |
| Budget cap per page load | `$0.05` | Hard cap; with N=20 it almost never fires in practice. Sessions beyond the cap render heuristic-only with a "summary unavailable — over budget" marker. Configurable via `[tool.attune-ops.sessions] budget_cap_usd`. |
| Listing route | `GET /sessions` (page) + `GET /api/sessions` (JSON) | Mirrors `/specs` + `/api/specs` and `/workflows` + `/api/runs/...`. |
| Listing JSON shape | `{sessions: [{id, started_at, last_activity, duration_seconds, message_count, starter_prompt, source}]}` where `source` ∈ `{"heuristic", "haiku", "cached"}` | Lets the UI show a "summarized by Haiku · cached" badge for transparency. |
| Expand-on-click body | Server-side render the first user message; full transcript stays at the JSONL file on disk (no in-page transcript viewer) | Keeps the page light. Users who want the full transcript can `cat` the JSONL. |
| Empty state | "No sessions in the last 3 days for this project. Older sessions are at `<path>`." | Tells the user where the data lives instead of pretending it doesn't. |
| Failure mode for unreadable JSONL | Skip with WARN log, don't surface as broken row | An unreadable file is a Claude Code internal issue, not something the user can fix from the dashboard. |
| "Resume most recent" card | **Yes — current-worktree first, canonical fallback** | Most-recent session from the dashboard's *own* encoded key (matches "where you are right now"). If none in last 3 days under the current key, fall back to the canonical project root's key. Dedupes against the list below. See Resume-card scope below. |
| Compare mode | `GET /sessions?compare=1` — renders heuristic + Haiku columns side-by-side for one request | Dev tool, no UI affordance. Pre-launch eyeball check that Haiku spend is buying actual quality. ~30 LOC + template tweak. |
| Calibration harness | Committed redacted JSONL fixtures + runner emitting `tokens / cost / quality` snapshot | Lands in S3 alongside the Haiku integration. Regression signal in CI for Haiku prompt edits. See Calibration as fixture below. |
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

## Pre-S3 design tightening

> Five additional resolutions captured 2026-05-15 after a
> review pass. Each tightens a decision that the original
> matrix made on incomplete information.

### 5. Budget-cap math — list capped at N=20

**Problem.** The original $0.05/load cap was sized for
"~10 sessions in a 3-day window." The multi-key probe found
**93 sessions** in the same window across all encoded keys
— ~9× the original estimate. At ~$0.001/session that's
~$0.09 per uncached load: already 1.8× over the cap before
caching takes effect.

**Decision.** Cap the surfaced list at **N=20 most-recent
sessions** (sorted by `last_activity` desc). Worst-case
uncached spend: 20 × $0.001 = $0.02 — well under the $0.05
cap, with headroom for prompt growth or input-size variance.

**What this does NOT change.** Older sessions stay on disk;
the empty-state copy still tells users where to find them.
The Resume-most-recent card reads independently (single
session) and is unaffected. The N=20 limit is **list-only**.

**What we declined.** Background-summarize via a worker
would give the best UX (page never blocks on Haiku spend)
but adds a concept the dashboard doesn't have today
(~60 LOC + worker plumbing). Deferred — revisit in a later
slice if N=20 becomes too restrictive in practice.

### 6. Cache-key collision — hash last 4KB, not first

**Problem.** Hashing the *first* 4KB of a JSONL is
collision-prone because JSONLs grow monotonically: the
opening block is byte-identical for the lifetime of the
session. Two sessions whose initial prompts look similar
share their first 4KB, and the mtime in the key is the only
distinguishing signal — which can tick spuriously
(filesystem touches, cleanup tools) and trigger a stale
cache read.

**Decision.** Use **last 4KB** of the file instead. The tail
is the freshest content and changes every time the session
does. Cache key becomes
`(jsonl_filename, mtime, sha256_of_last_4kb)`. Single seek
(`fh.seek(-4096, SEEK_END)`) + read; same I/O cost as
hashing the head.

**Edge case.** Files < 4KB just get fully hashed
(short-session, rare, cheap).

### 7. Resume-card scope — current worktree first

**Problem.** With 47 worktree-encoded keys for attune-ai,
"globally most recent" can surface a sibling worktree's
session that the user has no current relationship to. The
card's framing ("you're returning to this work") implies
"your current stream" — but multi-worktree dev makes
"current stream" ambiguous.

**Decision.** Two-level lookup:

1. Most-recent session under the encoded key matching the
   dashboard's actual `project_root` (the worktree it was
   launched from).
2. If none in the last 3 days under that key, fall back to
   the canonical project root's encoded key.

If both miss, no resume card renders. The list below still
shows the full multi-key view, so the user always has
visibility into older worktree sessions.

### 8. Calibration as committed fixture

**Decision.** Land the calibration-harness infrastructure in
S3, alongside the Haiku integration itself:

- `tests/fixtures/ops/session_summaries/*.jsonl` — 10
  redacted real-session fixtures (~50 KB total). Each is a
  representative example: short, long, multi-thread,
  abandoned-mid-conversation, etc.
- `scripts/calibrate_session_summary.py` — runs the
  candidate Haiku prompt over the fixture set, emits per-
  fixture `{tokens_in, tokens_out, cost_usd, summary}` to a
  snapshot file.
- Snapshot file (`tests/fixtures/ops/session_summaries/snapshot.json`)
  — committed; CI fails if the snapshot diverges beyond a
  configurable tolerance (e.g. ±20% cost, length mismatch
  on summary).

**Why.** Without this, every Haiku prompt edit is a manual
calibration pass. With it, the prompt has an objective
regression signal — same pattern as polish-fact-check
Phase 1 (attune-author #28).

**Fixture-redaction discipline.** The fixture JSONLs are
real session data run through the same redaction pass we
ship for production. The fixtures **commit the redacted
form** — original sensitive content never lands in git.

### 9. Compare mode — `?compare=1` dev affordance

**Decision.** A query-param-only dev tool that renders the
session list with **both** heuristic and Haiku columns
side-by-side for a single page load. No UI button — discoverable
only by knowing the URL. Purpose: pre-launch eyeball
validation that Haiku spend is actually buying improved
output, not just different output.

**Scope.** ~30 LOC + a `compare_mode` template branch.
Doesn't bypass the budget cap; doesn't bypass redaction.
Just renders the second column alongside the first.

**Retirement plan.** Keep until S3 ships and we've validated
Haiku in production. After that, optional to leave in (cheap
dev tool) or remove. Documented in this row so a future
reader knows it's not part of the user-facing surface.

---

## Cross-spec dependencies

- **Worktree inventory** — A sibling spec at
  `docs/specs/worktree-inventory/` consumes the same
  multi-key project-key resolution this spec introduces.
  Ships independently. The shared helper
  (`enumerate_project_encoded_keys()`) lives in
  `src/attune/ops/data.py` and serves both features.

---

## Ship log

> Decision-row → first-implementing PR. Backfilled for
> S1/S2. Updated as future slices land.

| Decision | First PR / Commit | Status |
|---|---|---|
| Data source (encoded-canonical glob) | #377 (S1+S2) — `~/.claude/projects/` literal lookup; multi-key resolution in S3a (data layer) | shipped — multi-key in S3a |
| Time window (3 days) | #377 | shipped |
| Project scope (current project only) | #377 | shipped |
| Listing route (`GET /sessions`) | #377 (page) + S3b — `GET /api/sessions` in `routes/sessions.py` | shipped |
| Listing JSON shape | #377 (template only) + S3b — `routes/sessions.py::list_sessions` returns `{sessions, meta}` | shipped |
| Empty state copy | #377 | shipped |
| Failure mode (skip unreadable JSONL) | #377 | shipped |
| Heuristic fallback (S2 implementation) | #377 (S2 squash a577a7e8) | shipped |
| Cache key (last-4KB) | S3a — `session_summary_cache.compute_cache_key()` | shipped (cache module; Haiku wire-up in S3b) |
| Cache location / TTL | S3a — `<attune_home>/ops/session_summaries/<id>.json`, mtime-bound | shipped (module); first write happens in S3b |
| List cap (N=20) | S3a — `DEFAULT_SESSION_LIST_CAP` in `list_recent_sessions()` | shipped |
| Starter-prompt generation (Haiku) | S3b — `session_summarizer.summarize_session()` + `routes/sessions.py::enrich_with_summaries` | shipped |
| Budget cap ($0.05) | S3b — `session_summarizer.Budget` + `new_budget()` + `ATTUNE_OPS_SESSIONS_BUDGET_USD` | shipped (soft warning surfaced in template) |
| Source field semantics (heuristic/haiku/cached) | #377 + S3b — all three values now possible | shipped |
| Resume card (current-worktree → canonical) | TBD (S4) | pending |
| Live-session detection | TBD (S5) | pending |
| Compare mode (`?compare=1`) | S3b — `sessions_page` route query param + template branch | shipped |
| Calibration harness | S3b — `scripts/build_session_fixtures.py` (build), #393 — 12 committed redacted fixtures + `tests/unit/ops/test_session_redaction_snapshot.py` (redaction gate), post-S3 follow-up — `scripts/calibrate_session_summary.py` + `tests/unit/ops/test_calibration_snapshot.py` (Haiku cost/length gate) + `docs/specs/ops-sessions-page/calibration-runbook.md` | shipped |
| Expand-on-click body | TBD (S4 or later) | pending |

---

## Calibration record

- [x] Haiku prompt template — shipped as
  ``attune.ops.session_summarizer.SUMMARY_PROMPT`` (S3b,
  2026-05-15). Calibrated against decisions.md Decision 2's
  target shape: numbered (1. one-sentence what-was-worked-on;
  2. 0-3 open-threads bullets, skip if none; 3. ``Resume:``
  one-sentence pasteable prompt). Explicit "no filler"
  instruction; output capped at 256 tokens; input capped at
  4KB of user-prompt content.
- [x] First production-data eyeball (2026-05-15, attune-ai
  worktree silly-ramanujan-a91ddb against
  ``project_root=/Users/patrickroebuck/attune-ai``): Patrick's
  reaction was "impressed that Haiku did such a good job —
  bravo." Output reliably matched the target shape; quality
  judged to justify the spend. Cleared for merge of PR #390.
- [ ] Average tokens per summary (in / out) — measure once a
  redacted-fixture set is committed and the snapshot test lands.
- [ ] Average cost per session summary — derive from token
  counts × registry rates ($1/$5 per million for Haiku 4.5).
- [ ] Whether the budget cap ever fires during normal usage —
  observe over the first ~week of production use. With N=20
  cap and ~$0.001/session typical, the $0.05 per-load cap has
  ~2.5× headroom; cap fires expected to be rare.

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
- 2026-05-15 (S3 split) — S3 implementation broken into two
  PRs at Patrick's direction: **S3a** ships the data-layer
  foundation (multi-key `enumerate_project_encoded_keys()`,
  `list_recent_sessions()` rewire with newest-mtime dedup,
  `session_summary_cache` module with last-4KB SHA-256 key,
  `DEFAULT_SESSION_LIST_CAP = 20`) with no LLM calls. **S3b**
  adds the Haiku summarizer + redaction wire-up + budget cap
  (soft warning when breached) + `?compare=1` dev mode +
  fixture-build script for calibration. Snapshot-test +
  committed redacted fixtures defer to a post-S3 follow-up
  pending Patrick's interactive fixture curation pass.
- 2026-05-15 (S3b ship) — S3b lands the Haiku integration plus
  redaction wire-up, on-disk cache hit/miss path, per-page-load
  budget cap (default $0.05, override via
  `ATTUNE_OPS_SESSIONS_BUDGET_USD`, effective off-switch at
  cap=0), `?compare=1` dev mode, `GET /api/sessions` JSON
  endpoint, and a dry-run-by-default fixture-build script
  (`scripts/build_session_fixtures.py`). Snapshot test +
  committed fixtures intentionally deferred — they require
  Patrick's interactive curation pass over redacted real
  sessions. Calibration record below stays blank pending
  first real-session shakedown. Same-day pre-S3 design
  tightening pass (entry below) followed by:
- 2026-05-15 (later same day) — Pre-S3 design tightening
  pass. Five more decisions captured after interactive
  review: list cap N=20 (budget-cap math invalidated by
  multi-key reality), cache key switched to last-4KB
  (collision risk on monotonic JSONL growth), resume card
  scoped to current-worktree-then-canonical (multi-key
  noise), calibration harness as committed fixtures
  (regression discipline), and `?compare=1` dev affordance
  (pre-launch Haiku validation). Sixth review item
  (worktree-inventory feature) split out to its own spec
  at `docs/specs/worktree-inventory/`; cross-spec
  dependency noted above. Seventh review item (ship log
  table) added at the bottom of this file. Rows updated:
  Starter-prompt generation (cost math), Cache key
  (last-4KB), Budget cap (with N=20 footnote), Resume card
  (scope), and three new rows: List cap, Compare mode,
  Calibration harness.
