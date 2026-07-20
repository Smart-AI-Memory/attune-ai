# Feature-Page Scaffolder — Tasks

**Status:** parked (2026-07-13) — spec docs shipped (#1190); implementation not started (T1–T4 remain: template, scaffold/build verbs, tests, playbook retirement) · Resume-Trigger: evergreen (no external clock) · implements
[design.md](design.md). Each task names its acceptance.

## T1 — Template + `scaffold` verb

- Add `content/features/_TEMPLATE.md`: fixed `nav`
  (`how-to`/`architecture`/`reference`), substitutable
  `feature`/`summary`/`tags`/`source_globs`, and the canonical section
  skeleton (Overview / Concepts / Quickstart / Tasks / Reference /
  Comparison / Failure modes / FAQ seeds / Notes & tips / Design &
  extension), each with one `<!-- fill: … -->` line.
- `scripts/new_feature.py scaffold <slug> --summary … --tags … --globs …`:
  validate slug (R5), render the master from the template, append the
  `features.yaml` entry preserving comments (D2).
- **Acceptance:** scaffolding a throwaway slug yields a master whose
  frontmatter parses and whose section set equals the projector's
  expected sections; a duplicate slug and a non-kebab slug both exit
  non-zero with a clear reason; the new `features.yaml` re-parses.

## T2 — `build` verb + env resolution

- `scripts/new_feature.py build <slug>`: run project → sync → import
  audit (scoped to the 4 new docs pages) → wiring audit, each with its
  postcondition asserted (D6).
- Resolve a `attune_author`-capable interpreter (current → `--python` →
  discovered main venv); on failure, exit with the actionable remedy, not
  a raw `ModuleNotFoundError` (R4).
- **Acceptance:** on a filled throwaway master, `build` exits 0 and the
  bundle-sync `--check` is clean; with `attune_author` unavailable and no
  `--python`, it exits non-zero naming the fix.

## T3 — Tests

- Unit (T1 surface): render correctness, slug rejection, yaml insertion.
- Integration / regression: scaffold a throwaway feature, fill from a
  fixture body, `build`, and assert the produced `.help` + docs + bundle
  outputs are byte-identical to a hand-run `project_features.py` +
  `sync_help_bundle.py` — the wrapper adds no drift. Teardown removes the
  throwaway slug and all its artifacts (incl. the `features.yaml` entry)
  so nothing leaks into the repo.
- **Acceptance:** the suite is green and the throwaway slug is absent from
  `features.yaml` after the run.

## T4 — Retire the playbook into the command

- Update the lessons entry ("API-free single-source feature-page
  playbook") to lead with `scripts/new_feature.py scaffold|build` and
  demote the manual 5 steps to "under the hood".
- Add a short `content/features/_TEMPLATE.md`-adjacent note or a
  `docs/how-to/` pointer so the command is discoverable in-repo (closing
  the "knowledge cliff" R1 names).
- **Acceptance:** a reader who finds the lessons entry or the how-to is
  routed to the command first; the manual steps remain only as
  explanation.

## Sequencing

T1 → T2 are the build order; T3 lands with each (unit alongside T1,
integration alongside T2). T4 is the closeout once T1–T3 are green. No
task depends on the sibling fact-check-gate work (decisions.md Open).
