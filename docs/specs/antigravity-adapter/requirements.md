# Antigravity Adapter — Requirements

**Status:** shipped (2026-07-21 — D1 ratified (a) + #1445's
.agents/AGENTS.md target; D2 resolved by receipts; D3 CLOSED
(IDE parity probe PASS post-#1445); AC-1..AC-5 receipted, AC-4
re-run live at close; see decisions.md completion pass. Carried
risk: behaviors pinned to app 2.3.1 / agy 1.1.4 — re-verify
after self-updates)

Sibling of [gemini-projector](../gemini-projector/requirements.md)
(PARKED 2026-07-18 — Google sunset the Gemini CLI free tier in
favor of Antigravity; this spec is the surviving Google-surface
adapter).

## The headline finding (verified from live docs, not memory)

**The repo already speaks half of Antigravity's convention.**
Antigravity discovers workspace skills from
`<workspace-root>/.agents/skills/<skill>/SKILL.md` (agentskills.io
open standard) — exactly the tracked mirror this repo has shipped
for months via `scripts/sync_agents_skills.py` (41 skills today).
Skills integration is expected to be ZERO new work; AC-1 just
proves it.

Remaining surface is the collaboration CONTRACT, via Antigravity's
workspace rules: markdown files in `.agents/rules/` at the git
root (backward-compat `.agent/rules`), ≤12,000 chars each, with
per-rule activation (Manual / Always On / Model Decision / Glob).
Rules support `@filename` references to other files. Global rules
live in `~/.gemini/GEMINI.md` — shared with Gemini CLI, user-owned,
out of repo scope.

## Design fork

- **D1 — contract delivery into `.agents/rules/`.**
  - **(a) Reference adapter (recommended if @-inlining verifies):**
    a tiny tracked `.agents/rules/collaboration-contract.md`
    (`trigger: always_on` frontmatter) whose body is essentially
    `@../../AGENTS.md` plus one framing line (the path is
    rules-file-relative; the docs' `@/AGENTS.md` form does not
    inline — verified). No duplicated contract text, no new projection
    target; drift-free by construction. Gated on verifying that
    `@` references actually inline the target file's content into
    agent context (AC-2), and on how activation mode is declared
    in-file (frontmatter format is undocumented on the page —
    inspect a UI-created rule file after install).
  - **(b) Fourth projection target:** add
    `.agents/rules/collaboration-contract.md` to the projector's
    `CONTRACT_TARGETS` with the standard marker pair. The
    projected block is 5,662 chars today — fits the 12,000-char
    rule limit with ~50% headroom, but add a projector-side size
    guard so growth past the limit fails `--check` loudly instead
    of being silently truncated by the consumer.
  - Pick (a) if AC-2 passes; (b) is the sturdy fallback and stays
    mechanically drift-guarded either way.

- **D2 — `.agents/rules/` tracked-vs-generated status.** `.agents/`
  is already tracked (skills mirror). If D1=(a) the rule file is a
  small hand-owned adapter (tracked, hand-edited, like
  `.gemini/settings.json` in the sibling spec). If D1=(b) it is
  projector-owned like AGENTS.md — never hand-edited, drift-gated.

- **D3 — surface parity.** The Customizations docs sit under the
  "Antigravity 2.0" platform section; verify with the installed
  tool whether the CLI and IDE both honor workspace
  `.agents/rules/` (expected) and whether rule activation
  defaults differ between them.

## Requirements

- **R1** The shared contract reaches Antigravity agent context
  mechanically (mechanism per D1); no hand-copied contract text.
- **R2** The existing `.agents/skills/` mirror is consumed as-is —
  no Antigravity-specific skill duplication. If Antigravity needs
  frontmatter beyond the agentskills.io fields the mirror already
  emits, extend `sync_agents_skills.py`, never hand-edit mirrors.
- **R3** If D1=(b): the new target joins the projector's
  preflight-all-then-write, `--check`, and test discipline, plus
  the size guard (rule-limit headroom asserted in tests).
- **R4** `collaboration_preflight.py` gains the D2-consistent
  check; silent when Antigravity absent. Everything works with
  Antigravity not installed (CI has no Antigravity).
- **R5** Antigravity sessions follow the same branch/worktree
  discipline; note its native "New Worktree Mode" in the adapter
  docs as the preferred mode for this repo.
- **R6** Global-level config (`~/.gemini/GEMINI.md`,
  `~/.gemini/config/skills/`) stays user-owned and out of scope.

## Acceptance criteria (failure-sensitive)

- **AC-1 (skills, zero-work claim)** With the repo opened as an
  Antigravity workspace, the agent's skill discovery lists the
  mirrored skills (spot-check 3 by name, e.g. `attune-hub`,
  `spec`, `security`). Fails → R2's extension path activates.
- **AC-2 (gates D1)** A scratch `.agents/rules/` rule containing
  an `@` reference demonstrably lands the referenced file's
  CONTENT in agent context (agent quotes contract specifics it
  was never shown directly). Record transcript in decisions.md.
- **AC-3** If D1=(b): master edit without re-projection →
  `--check` exits 1 naming the rules target; size guard fails
  when the rendered block exceeds a safety threshold (e.g.
  10,000 chars) below Antigravity's 12,000 limit.
- **AC-4** Preflight + both projector checks exit 0 on a clean
  tree with the adapter landed (real commands, not mocks).
- **AC-5** Full keyless suite green on all OS lanes (Windows
  receipts load-bearing for this script family — see #1439's
  `as_posix()` lesson).

## Out of scope

- Antigravity plugins/hooks/sidecars/subagents integration
  (separate evaluation; `attune-ai` is a Claude Code plugin — an
  Antigravity plugin port is a product decision, not contract
  plumbing).
- Migrating any workflow off Claude Code / Codex / Gemini CLI.
- The Antigravity SDK and 2.0 agent-manager surfaces.
