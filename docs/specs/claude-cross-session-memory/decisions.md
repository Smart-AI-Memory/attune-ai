# Claude Cross-Session Memory — Decisions

**Status:** approved
**Ratified:** 2026-06-02

## D1 — Recall trigger

**Decision:** SessionStart hook (auto top-k) + `/recall` skill (user-invoked).

**Rationale:** For a solo developer who is always present, a skill is superior
to an autonomous MCP tool for on-demand recall: it's explicit, shows what was
surfaced and why, and puts the user in control. The hook handles "background"
context that should always be available, while `/recall` handles intentional
deeper pulls. No Claude-autonomous mid-session recall without user intent.

**Rejected alternatives:**
- On-demand MCP tool only — Claude autonomously calls it; less transparent for
  solo dev who wants to see what memory is active.
- Hook + MCP tool (original design lean) — replaced by Hook + Skill for better
  solo-dev UX.

---

## D2 — Write / promotion policy

**Decision:** Session findings auto-stash to Redis with a TTL (7 days default).
Promotion from Redis to the curated `~/.claude/memory/` layer stays
review-gated (no auto-promotion).

**Rationale:** Consistent with the principle that the curated layer is
human-tuned. Auto-stash captures useful findings without requiring explicit
`/remember` invocations. The TTL prevents Redis from becoming a graveyard of
stale data. Review-gated promotion keeps the curated layer's signal-to-noise
high and auditable.

**Rejected alternatives:**
- Auto-promote to curated — risks filling the curated layer with unreviewed
  content; harder to audit what Claude wrote vs what Patrick wrote.
- Manual only — loses session findings that seemed trivial at the time.

---

## D3 — Cross-memory reference format

**Decision:** `[[link]]` stays as reference (lint-checkable name resolution
only); `@import` reserved for explicit inline-composition when content must
be inlined.

**Rationale:** `[[link]]` is already enforced by `memory_lint.py` and is cheap
(no content loading). Reserving `@import` for intentional composition keeps
the distinction clear: a `[[link]]` is "this memory is related," an `@import`
is "inline this memory's content here." Most cross-references are the former.

**Rejected alternatives:**
- `@import` everywhere — higher context cost; every reference pulls full file.
- `[[link]]` only, no inline — loses composition capability for cases where
  context genuinely needs to be merged (e.g. a meta-memory that aggregates
  multiple related topics for a complex project).
