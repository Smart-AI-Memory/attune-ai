# Gemini Projector Integration — Requirements

**Status: PARKED — SUPERSEDED (ratified 2026-07-18, Patrick)** by
[../antigravity-adapter/](../antigravity-adapter/requirements.md).
Google retired the Gemini CLI's free individual tier the same day
this spec was drafted (`IneligibleTierError` → "migrate to the
Antigravity suite"); the Antigravity adapter (D1 RATIFIED,
receipts green) now delivers the contract to Google's agent
surface. Revive only if a keyed (GEMINI_API_KEY) Gemini CLI
becomes worth the billing premise — see decisions.md. The
candidate adapter is preserved at
[settings.json.artifact](settings.json.artifact). Written against
the projector as merged in #1439 (`dbfd8bb58`); re-verify claims
about Gemini CLI behavior against the installed CLI before
ratifying (the D1 fork turns entirely on a live receipt).

## Problem

The collaboration contract master
(`content/collaboration/contract.md`) projects into the two current
provider surfaces — `AGENTS.md` (Codex) and `.claude/CLAUDE.md`
(Claude) — via `scripts/project_collaboration_contract.py`, with a
`--check` drift gate and marker-delimited blocks. Gemini CLI loads
neither file: its context surface is `GEMINI.md` (hierarchical:
global `~/.gemini/GEMINI.md`, repo root, subdirectories), with
workspace config in `.gemini/settings.json`. Adding Gemini as a
third collaborating agent without a mechanical projection re-creates
exactly the hand-copy drift the projector was built to kill.

## Design fork (decide before any implementation)

- **D1 — adapter shape.** Two candidate mechanisms:
  - **(a) Config-only adapter (recommended if verified):** track a
    minimal `.gemini/settings.json` that sets `contextFileName` to
    include `AGENTS.md`, so Gemini reads the *existing* projected
    surface. Zero new projection targets, zero new drift surface;
    the projector is untouched. Requires a live receipt that the
    installed Gemini CLI honors the setting from a workspace
    `.gemini/settings.json` and loads repo-root `AGENTS.md` (AC-1).
    Fits "simpler is better" and the contract's "provider-specific
    setup stays in adapters" rule.
  - **(b) Third projection target:** add `GEMINI.md` to
    `CONTRACT_TARGETS` with the standard marker pair. Mechanical,
    symmetric with the existing targets, but adds a tracked file
    whose non-projected remainder needs an owner and content plan.
  - Pick (a) unless the live receipt fails; fall back to (b).

- **D2 — `.gemini/` tracked-vs-ignored split.** `.gitignore` line
  267 ignores `.codex/` wholesale; `.gemini/` has no entry today.
  Unlike `.codex/`, option (a) requires *one tracked file inside*
  `.gemini/` (`settings.json`). Proposed: ignore `.gemini/*` except
  `settings.json` (negation pattern), keeping caches/session state
  out while versioning the adapter. If (b) wins D1, ignore
  `.gemini/` wholesale like `.codex/`.

- **D3 — preflight coverage.** `scripts/collaboration_preflight.py`
  checks `.codex/` is ignored (`codex-ignore`). Extend with the
  D2-consistent check: (a) `.gemini/settings.json` tracked + rest
  ignored; (b) `.gemini/` ignored wholesale. Also decide whether a
  missing-Gemini environment stays silent (Gemini not installed is
  the common case; the contract must keep working when only one
  provider is available).

## Requirements

- **R1** The shared contract reaches Gemini's loaded context
  mechanically — no hand-copied contract text on any
  Gemini-read surface. (Mechanism per D1.)
- **R2** Provider-specific setup lives in the adapter
  (`.gemini/settings.json` or the `GEMINI.md` non-projected
  remainder), never in the contract master. The master stays
  provider-neutral.
- **R3** If D1=(b): `GEMINI.md` joins the projector's preflight-
  all-targets-then-write discipline, `--check` names it on drift,
  and the marker/notice conventions match the existing targets
  byte-for-byte. Existing projector tests extend to the third
  target (drift, malformed markers, symlink rejection, partial-
  write containment).
- **R4** The `.gitignore` and preflight changes land per D2/D3 in
  the same PR as the adapter, with the preflight's read-only
  receipt still passing.
- **R5** Everything works with zero Gemini installed: no test,
  hook, or preflight check may require the Gemini CLI. Live-CLI
  receipts are recorded in this spec's decisions.md, not asserted
  in CI.
- **R6** A Gemini session follows the same branch/worktree
  discipline as Codex/Claude (one branch per agent per task,
  handoffs from `templates/agent-handoff.md`). If Gemini's tooling
  can't create worktrees, document the constraint in the adapter,
  don't weaken the contract.

## Acceptance criteria (failure-sensitive)

- **AC-1 (gates D1)** Live receipt: in a scratch worktree with the
  candidate `.gemini/settings.json`, an actual Gemini CLI session
  demonstrably loads the contract (e.g. it can quote the session
  protocol from `AGENTS.md` without being shown the file). A
  transcript excerpt goes in decisions.md. If this fails, D1=(b).
- **AC-2** With the adapter landed, `python
  scripts/project_collaboration_contract.py --check` and `python
  scripts/collaboration_preflight.py` both exit 0 on a clean tree —
  run as commands, not unit-mocked.
- **AC-3** If D1=(b): editing the master without re-projecting
  makes `--check` exit 1 naming `GEMINI.md`; the drift-gate test
  suite covers it.
- **AC-4** `git check-ignore` receipts match D2 exactly (probe
  both a `.gemini/` scratch file AND `.gemini/settings.json`).
- **AC-5** Full keyless test suite green on all OS lanes — the
  projector's path-output lesson (#1439's `as_posix()` fix) says
  Windows receipts are load-bearing for this script family.

## Out of scope

- Projecting into Gemini's *global* `~/.gemini/GEMINI.md` (user-
  level config is the user's, not the repo's).
- Any Gemini API/SDK integration in `src/attune` (this spec is
  collaboration-contract plumbing only).
- Retrofitting `.codex/` to the D2 negation pattern.
- **Google Antigravity** — promoted to its own sibling spec the
  same day (see
  [../antigravity-adapter/requirements.md](../antigravity-adapter/requirements.md));
  deferred here because it is a separate product from Gemini CLI
  with its own context-loading mechanism (workspace rules in
  `.agents/rules/`, skills from `.agents/skills/` — see the
  sibling spec), and folding it in would double the verification
  surface before this spec's D1 is ratified.
