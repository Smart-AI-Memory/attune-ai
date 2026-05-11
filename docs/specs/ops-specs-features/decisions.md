# Decisions — Port spec-handling features from attune-gui to attune ops

**Status:** Approved (2026-05-11) — execution gated on existing-features-stable
**Owner:** Patrick

---

## Problem

attune-gui has a fairly developed spec-handling surface
(`sidecar/attune_gui/routes/cowork_specs.py`,
`sidecar/attune_gui/templates/specs.html`) including:

- List specs across one or more roots (federated multi-root
  added in attune-gui PR #30)
- Create a new spec from a slug — bootstraps
  `requirements.md` from a Phase 1 template
- Bootstrap subsequent phase files (`design.md`, `tasks.md`)
  from the template, with prerequisite checks
- Update the `**Status**:` line in any phase file
  (`draft`/`in-review`/`approved`/`complete`/`done`)

attune ops, by contrast, has Home / Workflows / Telemetry /
Memory / Releases / Health tabs — but no specs tab. Specs live
in the filesystem and are managed entirely from the CLI / editor.

The friction:

- Side-by-side use of attune ops (workflows + telemetry) and
  attune-gui (specs + living docs) requires context-switching
  between two dashboards
- Spec status updates require manual file edits; the gui's
  status-flip UX is much faster
- Patrick uses spec-driven dev as the primary work pattern
  (per `.claude/CLAUDE.md` session-start protocol and the
  recently-reinforced "tar-pit trip-wire / spec-on-iter-3"
  lesson) — specs should be first-class in the dev dashboard
- The recent 10-hour CI tar-pit (PR #212) was partly caused by
  reactive iteration vs spec-first work; better spec
  accessibility makes spec-first more habitual

## Why this is a spec, not an immediate build

Patrick explicitly stated: *"I don't want to add features
until we get all of our existing ones working well."* This
spec exists to **capture the design now while the ideas are
fresh, without committing engineering time.** Execution is
gated.

## Decision

**Port the federated spec listing + status-flip UI from
attune-gui to attune ops as a new `Specs` tab, with explicit
scope limits and an execution gate.**

### What we port (Phase 1)

- **List specs** across `docs/specs/` (and any other configured
  spec roots) — pull from attune-gui's federated multi-root
  pattern
- **Status display + flip** — show current status of each
  spec's phase files; allow one-click flip between valid
  statuses
- **Per-spec drill-in** — view `decisions.md`, `tasks.md`,
  `design.md`, `requirements.md` content read-only

### What we explicitly do NOT port

- **Spec creation from slug** (attune-gui POST endpoints)
  — `/spec` slash command and the spec-driven workflow
  already cover this; doubling up adds maintenance with no
  user-facing win
- **Phase bootstrap from template** — same reason; the
  template lives in attune-author and the `/spec` skill
  uses it
- **Editor integration** — read-only viewer only. Editing
  happens in the user's editor or via `/spec`.
- **Living docs / corpus / template-editor surfaces** —
  those are attune-gui's primary domain; attune ops shouldn't
  encroach

The principle: attune ops is the *developer workflow* hub.
Specs are a developer workflow artifact. Read + status are
enough. Authoring stays in the existing tools.

## Execution gate

Phase 1 does NOT start until ALL of these are true:

1. **PR #212 (CI stabilization) merged and stable** —
   3 consecutive green CI runs on `main` AND no new CI-fix
   PRs opened during that period. Measurable, not calendar-
   based: the signal is *evidence of stability*, not *time
   elapsed*. Could clear in a day or a week — whichever
   demonstrates the data.
2. **`#227` (ops default-run), `#228` (ops 409 UX)
   merged and verified** — current ops surface is rough;
   building on top of bugs is wasteful
3. **No critical open ops bugs** — check
   `gh issue list --label ops --state open`
4. **Probe C Phase 4 settled** — parallel xdist restored
   on default runners with no new failures
5. **(Optional) `#226` larger runners** — not blocking,
   but if landed, this work benefits from the dev-parity
   improvement

The gate is the spec's main load-bearing element. Without it,
this spec is "yet another feature to add"; with it, this spec
is "the work we'll do once the foundation is solid."

## Alternatives considered

1. **Keep two dashboards forever** — works, has the context-
   switch cost. Acceptable if attune ops never grows a
   significant user base; less acceptable as more developers
   use it.
2. **Port the full attune-gui surface to ops** — too much;
   attune ops is workflow-focused and would lose that focus.
3. **Move specs to attune-gui exclusively** — backwards;
   specs are dev artifacts, not docs artifacts.
4. **Build a new spec UI from scratch** — duplicates
   attune-gui's working code; rejected unless attune-gui's
   API turns out to be a poor fit for ops's frontend
   conventions.

## Acceptance criteria

- A `Specs` tab in attune ops nav, between `Workflows` and
  `Telemetry`
- Lists specs from `docs/specs/` (configurable via
  `--specs-root` or env var matching attune-gui's pattern)
- Each spec shows: name, latest phase status, last-modified
- One-click status flip with optimistic UI + server
  confirmation
- Read-only viewer for phase files
- No new write endpoints beyond status updates
- Existing attune ops tabs continue working (no regressions)
- Tests cover the new routes at parity with existing ops
  routes

## What this spec is NOT

- A commitment to start work soon. The gate is the contract.
- A statement that attune-gui will lose its spec features.
  Both dashboards keep working; attune ops just gains a
  subset.

## Out of scope

- Mobile or external-network access to the specs UI
  (attune ops is localhost by default; this stays)
- Multi-user collaboration on spec edits
- Spec analytics / trend dashboards (interesting but
  separate)
- Slack/email notifications on status changes
- Diff view between phase files

---

(per-phase decisions appended as the gate is approached)
