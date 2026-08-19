# Review stub — attune.context post-retirement (2026-08-19)

One-page curated stub; the full receipted report lives local-first at
`~/.attune/reports/reviews/context-arch-review-post-12.0.0-2026-08-19.md`.

**Verdict:** the post-12.0.0 `attune.context` package (3 files /
278 LOC) is healthy; every risk found lives at the edges, none in the
package. Chair rulings recorded in
`docs/specs/context-compaction-retirement/decisions.md` D3.

| Finding | Anchor | Disposition |
|---------|--------|-------------|
| `suggest_compact.py` dormant twin of deleted `pre_compact.py` (3 dead-code-gate signals) | `src/attune/hooks/scripts/suggest_compact.py` | DELETED (chair, D3) |
| `POST_COMPACT` enum member — not a real Claude Code event, zero handlers | `src/attune/hooks/config.py` | Removed; `PRE_COMPACT` kept (real event) |
| Compaction doc fiction outlived the deletion | `docs/hooks.md`, `ACKNOWLEDGEMENTS.md`, `content/features/hooks.md` | Fixed in the residue PR |
| `last_fit` telemetry structurally dead in production (4 throwaway-allocator consumers) | `src/attune/context/allocator.py:30` | Minimal-measurement follow-up PR approved (D3) |
| Budgets 1250/1250/1000/750 unratified folklore | 4 workflow call sites | Deferred until measurement data exists (D3) |
| Post-compact continuity was an implicit 4-hook contract | `plugin/hooks/{spec_orient,session_recall,usage_consent_notice,compact_warning}.py` | Documented: `docs/architecture/post-compact-continuity.md` |
| D2 commands gate pass untracked outside decisions.md | `docs/specs/context-compaction-retirement/decisions.md` | TASKS.md entry added |
| `.claude/PROJECT-CONTEXT.xml` stale historical artifact | (whole file) | Left as-is; already ruled a deletion candidate by claim-drift-gates — chair-clickable follow-up |
| Inflater / cross-file packing / new infrastructure | — | Not reopened (D1 + roundtable rulings stand) |
