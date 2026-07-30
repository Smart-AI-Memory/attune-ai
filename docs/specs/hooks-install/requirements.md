# Hooks Install — Requirements (CANDIDATE)

**Status:** draft (2026-07-30) — spec CANDIDATE captured at
Patrick's request; a `/spec` interview re-derives requirements from
this brainstorm input. Do not implement from this document.
**Slug:** `hooks-install`
**Provenance:** 2026-07-30 fix-test tutorial session (PR #1798 +
Screen Studio shooting script). The tutorial's automation chapter
teaches users to hand-copy a ~40-line PostToolUse hook script plus
a settings.json block; the session retro named the product gap:
"the tutorial teaches a hook that attune doesn't actually ship."

## Problem (motivating evidence)

The tests-on-edit loop (run the matching test after every
`Edit|Write`, route failures back to Claude as exit-2 stderr) is
the highest-leverage automation attune currently documents — and
its install path is two manual copy-pastes into the user's repo.
The tutorial and its video create demand for exactly this pattern;
every viewer who wants it must transcribe code from a doc. attune
already ships a hooks runtime (`plugin/hooks/hooks.json`,
`src/attune/hooks/scripts/`) but has no way to install a hook INTO
a user's project.

## Sketch (one line)

`attune hooks install tests-on-edit` — copies the hook script into
the project's `.claude/hooks/` and merges the `PostToolUse` entry
into `.claude/settings.json`, idempotently; `attune hooks list` /
`attune hooks uninstall <name>` complete the lifecycle.

## Pre-listed /spec interview questions

1. **Catalog scope** — is `tests-on-edit` the only launch hook, or
   does a catalog shape the design from day one (format-on-save,
   lessons-reminder, etc.)? Smallest-viable vs. registry.
2. **settings.json merge strategy** — programmatically editing a
   user's `.claude/settings.json` is the riskiest surface (comments
   are lost, existing hooks blocks must merge, a bad write breaks
   every session). Merge in place, emit a paste-ready diff, or
   write a separate include if the harness supports one?
3. **Script placement** — copy the script into the user's repo
   (vendored, user-editable, drift-prone) vs. reference the
   installed attune package path (upgrades propagate, but the hook
   breaks if attune is uninstalled)?
4. **Test-mapping convention** — the tutorial's glob
   (`tests/**/test_<stem>*.py`) is one line by design; does install
   prompt for the project's convention (Socratic scoping) or ship
   the default with a documented edit point?
5. **Uninstall/upgrade story** — what marks a managed hook as
   attune-installed so uninstall removes only what install added,
   and upgrade can re-write it?
6. **Interaction with plugin hooks** — the attune plugin already
   registers its own hooks via `plugin/hooks/hooks.json`; installed
   project hooks must not collide or double-fire.
7. **Security posture** — an installer that writes executable hook
   code into repos needs the path-validation gate treatment and
   security tests (Critical Rules); does it also need a dry-run
   default?

## Non-goals (candidate-stage)

- Not a general hook framework or marketplace — attune-authored
  hooks only.
- No daemon/watcher; Claude Code's hook runtime is the only
  execution surface.
