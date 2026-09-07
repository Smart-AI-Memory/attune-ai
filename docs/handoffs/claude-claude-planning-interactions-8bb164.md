# Agent work handoff

## Goal

Ordinary Claude planning and scoping requests use the host's built-in
`AskUserQuestion` for material independent unknowns, retain partial
answers and corrections, honor cancellation, and fall back to typed
questions where the schema cannot represent a field. Attune forms stay
experimental on Claude.

## Acceptance criteria

- Canonical elicit and planning guidance carry a Claude host default
  parallel to the Codex one; the skills mirror and generated help agree.
- Answer retention, correction, and cancel semantics are preserved;
  unsupported controls have an explicit typed fallback.
- host-surface-parity D16 records the chair's words with the lead's
  inferences separated; the probe addendum lists pending observations.
- A different-model review is run and dispositioned in the cross-review
  ledger. A reviewable PR exists; Patrick merges.

## Scope and assumptions

- Branch/worktree: `claude/claude-planning-interactions-8bb164` at
  `.claude/worktrees/morning-review-6b4c9b`, based on origin/main
  `8f1c0eabe` (contains the #2458 merge `ea3a6dc49`).
- Provider/session: Claude (Fable 5.1), desktop app Code tab, Claude Code
  2.1.260, autonomous with no user present: no rendering or keyboard
  observation was possible.
- Assumptions: Claude's native question control is `AskUserQuestion`
  (verified by inspecting the exposed tool schema). The widget, the server
  route, and `elicitation_ask` are custom Attune forms and therefore
  experimental on Claude for ordinary requests. D21 is scoped to the
  explicitly requested Attune-form path, not reversed. No adapter is
  needed: `select_form_surface` lives in attune-forms and remains the
  router for that explicit path.

## Current state

- Status: implemented and checked locally; different-model review pending
  at the time of this commit (see the ledger row added afterwards).
- Changed files: `plugin/skills/elicit/SKILL.md`,
  `plugin/skills/planning/SKILL.md`, their `.agents/skills/` mirrors,
  `plugin/help/generated/references/skill-elicit.md`,
  `plugin/help/generated/references/skill-planning.md`,
  `plugin/help/generated/tasks/use-planning.md`,
  `docs/specs/host-surface-parity/decisions.md` (D16 + open decision),
  `docs/probes/host-surface-parity/host-native-trials-2026-09-07.md`
  (Claude inspection addendum), `CHANGELOG.md`.
- Decisions: D16 recorded. Open decision: whether `.claude/CLAUDE.md`'s
  always-loaded Socratic rule adopts the Claude host default for this
  repository's own dev sessions; deliberately not edited here.
- Risks or open questions: desktop rendering, keyboard operation, partial
  submission, and dismissal behavior of `AskUserQuestion` are unobserved.
  Native cards show less option context than the D21 widget (counter-case
  in D16). Installed attune-forms 0.14.0 does not export the
  `HostQuestionProfile` that Task 1B increment 2 will pin; the guidance
  cites the tool schema, not that profile.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Starting checkout safe | `python scripts/collaboration_preflight.py` | 87 governance tests passed; clean worktree, dirty main preserved |
| Base current and contains #2458 | `git fetch origin main`; `git rev-list --count HEAD..origin/main`; `merge-base --is-ancestor ea3a6dc49 HEAD` | 0 behind; ancestor confirmed |
| Native control identified | inspection of this session's exposed `AskUserQuestion` schema | 1–4 questions, 2–4 options, `multiSelect`, `header` ≤12, built-in Other, synchronous result |
| Projections in sync | `sync_agents_skills.py --check`; five `generate_*_templates.py --check` | all pass |
| Guidance, help-drift, plugin-reference tests | `pytest` on the five focused files, `-p no:xdist` | 91 passed, 3 skipped |
| Gates and doc-import drift | `pytest tests/unit/gates tests/unit/test_generated_doc_import_drift.py` | 662 passed |
| Pinned pre-commit on changed files | `uv run --with pre-commit pre-commit run --files …` (10 files) | passed |
| Whitespace | `git diff --check` | clean |
| Different-model review | `run_review('.', seat='codex', mode='branch')` | see ledger row and PR body |
| Desktop `AskUserQuestion` behavior under this guidance | fresh desktop trial on a checkout carrying this branch | not run; pending |

## Next action

Chair: read D16 and rule the `.claude/CLAUDE.md` follow-up. Then schedule
one desktop trial of an ordinary planning request on a checkout that
carries this guidance, verifying the receiving checkout first (the bakery
recording lesson), and record tool returns separately from visible UI and
user attestation in the probe document.
