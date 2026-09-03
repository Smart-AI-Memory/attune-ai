# Round-table question — `q-fable-51-surface-overlap-001`

**Chair:** Patrick Roebuck · **Moderator:** Claude · **Roster:** Claude,
Antigravity, Codex (fixed) · **Rounds:** 1 expected, 2 if the steelman
provision fires (chair lean is recorded below), ceiling 3 (D3).
**Spend gate (chair-ruled 2026-09-03):** 3 seat invocations, 1 round;
a second round needs a fresh chair go.
**Prepared:** 2026-09-03 by the Claude seat in a Cowork session.
**Transcript:** the moderator writes the machine-local transcript to
`~/.attune/reports/roundtable/q-fable-51-surface-overlap-001.md`; please
also copy it to `docs/reports/roundtable/` so the Cowork seat (which
sees only the repo) can read it and draft the promotion triage.

## The question

The 2026-09-01 host release (Claude Fable 5.1; Cowork and Claude Code)
ships first-party versions of things attune-ai built as portable,
verified, multi-provider systems: a structured question widget
(`AskUserQuestion`), desktop-persistent project memory (`MEMORY.md` +
typed topic files), a skill-proposal card, a multi-agent workflow
runner, typed review findings, hosted artifacts with runtime state,
scheduled tasks, and a file monitor.

**Which of Attune's human↔AI communication and capability features
does this release overlap, and where should the next two minors
spend effort so the release is a tailwind rather than a headwind —
without any host becoming the privileged surface, and without
power users on Codex or Antigravity sacrificing anything?**

## What each seat is asked to return

Independently, text only, no tools (R1):

1. A ruling on each proposed requirement R1–R8 in
   `docs/specs/host-surface-parity/requirements.md`: **adopt / amend
   (say how) / decline (say why)**.
2. At least one requirement the Claude seat did **not** propose. The
   chair has asked the table to be creative and not limited to the
   brief.
3. A position on the three open mechanics: D2 (`LOCAL` as enum member
   vs routing label), D3 (no third capability contract), and whether
   Task 7 (Ollama reranker as the Phase A example extension) should
   wait for Phase B.
4. Its own dissent register: where it disagrees with the Claude
   seat's reading in the companion brief.

## Facts taken as given (verified against the tree 2026-09-03)

- attune-ai 16.2.0; attune-forms ≥ 0.12.2; `Surface.RICH / PORTABLE /
  HEADLESS`; state-bound command workspaces shipped.
- `CANONICAL_SEATS` is a literal three-tuple; `SEAT_RECIPES` fixed
  argv; `PLAN_ONLY_SEATS = {"antigravity"}`; workspace gates require
  exactly the fixed roster.
- `ModelProvider` has one member (`ANTHROPIC`); tiers are
  `CHEAP / CAPABLE / PREMIUM` in four copies plus the attune-rag
  mirror with a drift guard.
- `attune.extensions` (release-16-manifest passenger 4) is **not on
  disk**; D1/D2 ruled; D3 phasing proposed, not ruled.
- Chair rulings already made (this spec's D1, 2026-09-03): local
  models start as a `LOCAL` tier for low-stakes roles, not a seat;
  extensions are the seam for providers/backends/seats; the
  deliverable is this spec.

## Chair's lean (recorded so the steelman provision can fire)

The chair leans toward adopting the parity rule (every host-specific
capability ships with PORTABLE and HEADLESS twins, receipted, in the
same change) and toward roster-as-data. Seats that agree should
steelman the opposite; seats that disagree should say what the
parity rule costs.

## Companion material

- Brief (Claude seat opening position): artifact
  "Fable 5.1 and the Attune Surface", 2026-09-03.
- Spec: `docs/specs/host-surface-parity/` (requirements, design,
  tasks, decisions).
- Discipline: attune-ai.dev/discipline, §2 (contract), §5 (memory),
  §7 (verification), §9 (context budgeting).
