# Claude Cross-Session Memory — Tasks

**Status:** approved
**Phase:** ready-to-implement

> **API corrections (2026-06-03 verify pass — authoritative: see
> [decisions.md](decisions.md) D4).** The method names below are confabulated;
> use the verified APIs:
>
> - `PersonalMemory.store()` does **not** exist → use `.capture(topic,
>   content, kind)` (promote path; runs LLM polish) or `.query(query, k,
>   kind_filter)` (semantic recall).
> - `RedisShortTermMemory.store()` does **not** exist → use `.stash(key, data,
>   credentials, ttl)` / `.retrieve(key, credentials)` (key-based; requires
>   `AgentCredentials`).
> - `recall_entries()` (T1.3) is a **merge** of `PersonalMemory.query()`
>   (semantic, durable) + a cheap keyword/recency/cwd filter over the raw
>   stash — **not** a semantic query against Redis. See D4.
> - Stash writes are **raw, no polish** (Stop hook stays fast); polish happens
>   only at user-gated promotion (T2.2).

Phases:
- **Phase 1** (P1): SessionStart hook + Redis stash infrastructure
- **Phase 2** (P2): `/recall` skill + promotion UX
- **Phase 3** (P3): Cross-worktree dedup + polish

---

## Phase 1 — Auto-inject hook + session stash

### T1.1 — SessionStart recall hook

**Objective:** Inject top-k relevant memories at session start from Redis.

**Files to create:**
- `~/.claude/hooks/session_recall.py` — standalone hook script

**Spec:**
- Reads `CLAUDE_CODE_SESSION_ID` + cwd for query context.
- Calls `attune_rag` / `attune.memory.PersonalMemory` for top-k (default 5).
- Writes a fenced `## Recalled memories` block to stdout (hook inject pattern).
- Falls back to empty output if Redis absent or `attune_rag` not importable.
- Exits 0 always (failure is silent).

**Registers in:** `~/.claude/settings.json` under `hooks.SessionStart`.

**Acceptance:**
- Hook completes in ≤ 1 second on cold Redis query.
- No error banner when Redis is absent.
- Output is ≤ 400 tokens.

---

### T1.2 — Session-end stash (Stop hook)

**Objective:** Auto-stash notable session findings to Redis at session end.

**Files to create:**
- `~/.claude/hooks/session_stash.py` — Stop hook script

**Spec:**
- Reads recent session transcript (last N messages via `CLAUDE_CODE_SESSION_ID`
  → `~/.claude/projects/<encoded>/<id>.jsonl`).
- Extracts notable entries: decisions made, bugs encountered, patterns observed,
  file paths touched with rationale.
- Runs attune-ai PII scrubber + secrets detector before writing.
- Stashes to Redis via `attune.memory.RedisShortTermMemory` or
  `PersonalMemory.store()` with TTL (7 days default).
- Falls back to local file `~/.attune/session_stash/<date>.jsonl` if no Redis.
- Exits 0 always.

**Registers in:** `~/.claude/settings.json` under `hooks.Stop`.

**Acceptance:**
- Stashed entries appear in `/recall` results in the next session.
- PII/secrets gates fire before any write.
- File fallback written when Redis absent.

---

### T1.3 — Redis stash entry schema

**Objective:** Define the canonical shape for a stashed session entry.

**Files to create/modify:**
- `src/attune/memory/session_stash.py` — `SessionStashEntry` dataclass +
  `stash_entry()` / `recall_entries()` helpers

**Schema:**
```python
@dataclass
class SessionStashEntry:
    id: str           # uuid
    session_id: str   # CLAUDE_CODE_SESSION_ID
    cwd: str          # project root at write time
    timestamp: str    # ISO-8601
    type: str         # "decision" | "pattern" | "bug" | "reference" | "note"
    content: str      # the memory text (≤ 500 chars)
    tags: list[str]
    ttl_days: int = 7
```

**Acceptance:**
- `stash_entry()` validates schema, runs PII/secrets gates, writes to backend.
- `recall_entries(query, top_k, cwd)` returns ranked results cross-cwd.
- Tests: schema validation, PII gate fires, Redis absent → file fallback.

---

## Phase 2 — `/recall` skill + promotion UX

### T2.1 — `/recall` skill

**Objective:** User-invocable skill that surfaces relevant memories.

**Files to create:**
- `plugin/skills/recall/SKILL.md`

**Spec:**
```yaml
name: recall
description: Surface relevant memories from prior sessions. Call with no args to infer from context, or /recall <topic> for an explicit query.
```

**Skill body:**
- Calls `recall_entries(query, top_k=10)` (R2).
- Presents results grouped by type with source (curated / Redis stash) and
  relevance note.
- Offers to inject selected results into conversation or promote to curated.

**Acceptance:**
- Returns results in ≤ 2 seconds.
- Shows source (curated vs stash), type, and relevance.
- No-Redis path returns curated-file results only (no error).
- Added to plugin skill count + attune-hub reference table (three gates per
  "Adding a plugin skill" lesson).

---

### T2.2 — Stash → curated promotion workflow

**Objective:** Let Patrick promote a Redis stash entry to a curated memory file.

**Approach:** Extend the existing `/remember` skill or add a `promote` subcommand
that:
1. Shows the stash entry content.
2. Runs `memory_lint.py` schema validation.
3. Writes to `~/.claude/memory/<slug>.md` with correct frontmatter.
4. Adds pointer to `MEMORY.md`.
5. Deletes the entry from Redis stash.

**Files to modify:**
- `plugin/skills/remember/SKILL.md` or create `plugin/skills/promote/SKILL.md`

**Acceptance:**
- Promoted entry passes `memory_lint.py --check-all` with 0 violations.
- Entry removed from Redis stash after promotion.
- MEMORY.md updated atomically.

---

## Phase 3 — Cross-worktree dedup + polish

### T3.1 — Content-keyed dedup in recall

**Objective:** Prevent duplicate entries when the same content is stashed from
multiple cwds (main + worktrees).

**Files to modify:**
- `src/attune/memory/session_stash.py` — add `content_hash` to schema; dedup
  on hash at write time.

**Acceptance:**
- Stashing identical content from two different cwds produces one entry (not two).
- Recall returns the entry for any cwd query.

---

### T3.2 — TTL + budget guardrails

**Objective:** Prevent Redis stash from growing unbounded; keep context budget safe.

**Files to modify / create:**
- `src/attune/memory/session_stash.py` — enforce max-entries-per-session (20),
  max-content-length (500 chars), TTL renewal on recall hit.
- `~/.claude/hooks/session_recall.py` — enforce top-k ≤ 5 and token budget ≤ 400.

**Acceptance:**
- Stash write rejects entries > 500 chars (truncate or split).
- Recall output never exceeds 400 tokens.
- Expired entries pruned on next stash write (lazy expiry).

---

## Implementation notes

- Redis stays optional everywhere: `try: import redis except ImportError: ...`
- PII/secrets gates are **required** at every write (R3 AC).
- The hook scripts live in `~/.claude/hooks/` (user home), not the repo, so
  they affect all Claude Code sessions. Register via `settings.json`.
- Skill goes through the three-gate test suite (skill count + attune-hub +
  sync_agents_skills) per the existing lesson.
