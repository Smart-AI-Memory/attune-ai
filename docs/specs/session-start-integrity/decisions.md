# Session-Start Integrity — Decisions

Append-only. Chair rules; the lead records.

## D1 — Repo identity = origin slug, no UUIDs (RATIFIED chair 2026-08-18)

Codex's round-1 follow-up asked: remote URL, committed UUID, or
both. Proposed: normalized `origin` slug (`owner/name`), fallback
directory name. Rationale: zero setup for a solo developer, derivable
everywhere git runs; a committed UUID adds an authoring step to every
repo — exactly the manual discipline this spec exists to remove.
Trade-off accepted: forks/renames change identity — acceptable at
this fleet's scale.

## D2 — Absence is soft, mismatch is hard (RATIFIED chair 2026-08-18)

Hard refusal of verification fires only on PROVEN repo mismatch.
Missing provenance warns loudly but still verifies. Rationale:
Claude seat's named risk (refusal-becomes-common-path erodes trust
in the surface) + Codex's degradation rule (fail closed for
verification claims only). Existing unstamped starters keep working
through the transition.

## D3 — Canonical hook source is `plugin/hooks/` (RATIFIED chair 2026-08-18)

The plugin already ships these hooks and is the projector source for
the `.agents/` mirror; a second canonical home would recreate the
twin problem this spec deletes.

## OQ1 — Retire the global starter (RULED chair 2026-08-18: RETIRE)

Claude and Antigravity independently proposed absorbing the global
starter into the ratified per-branch handoff convention
(`docs/handoffs/<branch-slug>.md`, tracked, deleted on merge;
`cross-provider-session-handoff` spec owns the tooling). Initially
deferred at approval; the chair reversed to RETIRE the same day
("oq1 — I've decided I want it too"). Scope lands in this spec as
R9: the starter-prompt hook prefers the current branch's tracked
handoff, then the newest tracked handoff, then the PROJECT-local
stamped starter; the global `~/.attune/next_session_starter.md` is
archived (rename, reversible) and the hook stops advertising it
except as a labeled legacy fallback during the transition.
Provenance enforcement (R1–R3) still applies to project-local
starters and any legacy global file encountered before archival.

## R8/R9 remediation receipts (2026-08-18, live runs)

- Fleet: `sync_session_hooks.py --write` converged all 5 siblings
  (help/author/rag refreshed; forms/lite gained hooks + settings
  entry); `--check` clean after; live `spec_orient.py` runs in
  attune-forms and attune-lite exited 0 with orientation output;
  projection committed per sibling (help cc6ccf6, author 7551eda,
  rag 6925247, forms 152bd0c, lite b9246bb — unpushed).
- Global starter: archived to
  `~/.attune/next_session_starter.archived-20260818.md` (rename,
  reversible); attune-ai queue migrated to
  `~/attune-ai/.attune/next_session_starter.md` and stamped
  (repo=smart-ai-memory/attune-ai, branch=main, head 8f35c599).
- Nudge receipts: worktree cwd surfaces `handoff:newest` (tracked);
  main cwd surfaces handoff + stamped project starter; reconciler
  emits provenance-matched banner with no warnings and no
  cross-repo verdicts.
- Orientation regex (R5): live re-run renders real statuses
  (shipped/approved/active…) instead of 53/55 "(unknown)".
