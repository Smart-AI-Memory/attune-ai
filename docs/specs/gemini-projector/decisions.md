# Gemini Projector Integration — Decisions

## D1 — adapter shape (OPEN, receipt pending)

**Candidate (a), config-only adapter, staged for the live test.**

Verified against the installed CLI, not docs-from-memory
(2026-07-18, `@google/gemini-cli` 0.51.0 via npm):

- The legacy flat `contextFileName` settings key is STALE for this
  version. The bundle reads `settings.context?.fileName` — the v2
  nested schema. An adapter written from older docs
  (`{"contextFileName": ...}`) would silently no-op.
- Candidate adapter (now preserved as `settings.json.artifact`):
  `{"context": {"fileName": ["GEMINI.md", "AGENTS.md"]}}` —
  `GEMINI.md` kept first so a future native context file still
  loads; `AGENTS.md` carries the projected contract block.

### AC-1 experiment protocol (runs after one-time Google auth)

1. **Control** — in a checkout WITHOUT `.gemini/settings.json`:
   `gemini -p "According to your loaded project context, what
   script must be run before non-trivial work, and what are the
   four artifact tiers?"`
   Expected: cannot answer from context (no GEMINI.md exists;
   AGENTS.md not loaded by default).
2. **Test** — same prompt in this worktree WITH the staged
   settings. Expected: quotes `scripts/collaboration_preflight.py`
   and the inline-edit / structured-one-shot / XML-task / spec
   tiers from AGENTS.md's projected contract block.
3. Paste both transcript excerpts below; ratify (a) on pass,
   fall back to (b) on fail.

### Receipt: BLOCKED BY PRODUCT SUNSET (2026-07-18)

The free-tier OAuth path no longer exists. With valid shared
credentials in `~/.gemini/` (from the Antigravity sign-in),
`gemini -p` (CLI 0.51.0) fails hard:

```
IneligibleTierError: This client is no longer supported for
Gemini Code Assist for individuals. To continue using Gemini,
please migrate to the Antigravity suite of products:
https://antigravity.google
```

Google has retired the standalone Gemini CLI's individual free
tier in favor of Antigravity. Remaining paths for THIS spec:
(a) GEMINI_API_KEY auth from AI Studio (API-quota billing;
changes the premise from "free ambient CLI" to "keyed tool"), or
(b) PARK this spec as superseded — the Antigravity adapter
(../antigravity-adapter/, D1 RATIFIED, receipts green) already
delivers the contract to Google's agent surface, and Antigravity
shares `~/.gemini/GEMINI.md` for global rules.

**RATIFIED (b) — parked as superseded (2026-07-18, Patrick).** The staged
`.gemini/settings.json` adapter is kept in the spec dir as an
artifact of record; do not track it at repo root unless (a) is
chosen later.

## D2 — `.gemini/` tracked-vs-ignored (OPEN)

Depends on D1. If (a): proposed `.gitignore` entries
`.gemini/*` + `!.gemini/settings.json`. If (b): `.gemini/`
wholesale like `.codex/` (line 267).

## D3 — preflight coverage (OPEN)

Depends on D2. Extend `scripts/collaboration_preflight.py` with the
D2-consistent ignore/tracked check; silent when Gemini absent.
