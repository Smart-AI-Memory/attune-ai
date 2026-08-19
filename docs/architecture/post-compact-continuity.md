# Post-compact continuity

How attune-ai sessions keep their bearings when Claude Code compacts
the context window. Since the 12.0.0 compaction-stack retirement
(`docs/specs/context-compaction-retirement/`), there is no in-package
compaction state manager — continuity is a small, deliberate contract
between four plugin hooks. This page makes that contract explicit
(ruled by the chair, 2026-08-19, from the post-retirement
architecture review).

## The contract

Claude Code re-fires `SessionStart` hooks after a compaction with
`source == "compact"` in the payload. The four hooks split the
responsibility:

| Hook | On `source == "compact"` |
|------|--------------------------|
| `plugin/hooks/spec_orient.py` | **Owns re-orientation**: renders a compact spec pin for the most relevant in-flight spec (`render_spec_pin`, 8 KB character budget) so the post-compact context reopens on the active work. |
| `plugin/hooks/session_recall.py` | **Stands down** (returns 0): recall output would pile onto the fresh context; the spec pin is the designated re-orientation payload. |
| `plugin/hooks/usage_consent_notice.py` | **Stands down** (returns 0): consent notices never compete with post-compact re-orientation. |
| `plugin/hooks/compact_warning.py` | **Upstream of compaction**: a Stop-hook that fires once per session when a transcript-size proxy crosses `ATTUNE_AI_COMPACT_WARNING_THRESHOLD` (default 0.70), recommending a clean exit + resume prompt instead of an in-place compact. |

## Design intent

- Exactly ONE hook (spec_orient) speaks into post-compact context;
  the others' early returns are deliberate, not missing features.
- Durable continuity lives in tracked artifacts (specs,
  `docs/handoffs/`, the session-stash memory layer) — not in a
  compaction-time state snapshot. That is the retirement's D1/D2
  ruling: git-visible state over parallel persistence.

## Changing this contract

If a hook needs to add post-compact output, move the ownership —
don't add a second speaker. Update this page and the hooks' inline
comments together; the comments reference "handled elsewhere", and
this page is the elsewhere.
