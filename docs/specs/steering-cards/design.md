# Steering cards — design

**Status:** draft (2026-09-11) — proposed shape; the host table below
is the one verified-fact surface and the one most worth reading.

## The master

`content/steering/steering-card.md` — a Markdown file with a small
front-matter schema so projectors can read rows without parsing prose:

```yaml
sections:
  - id: layers      # rendered as the strata table, host column included
  - id: thumb       # rules of thumb
  - id: words       # routing words
  - id: conventions # generic conventions; each row may carry `contract: <anchor>`
rows:
  - n: 1
    section: thumb
    phrase: Match the failure to the layer.
    line: Shape → hook or gate. Judgment → rule text. About you → memory. Tool gotcha → lesson.
    why: A blocker cannot be out-thought; a judgment frozen into a hook is wrong the day the judgment moves.
    when: 2026-09-11 — an ask-format guard from June blocked the confirm shape ruled in September.
    hosts: [claude, codex, antigravity]   # which seats the row applies to
essay: |
  (prose slot for card 4 — the layer model abstracted; no attune names)
```

Rows keep their `n` for life (R5). `hosts` lets card 3 filter and lets
card 2 hide Codex-only notes.

## The host column (verified facts only)

| Layer | Claude | Codex | Antigravity |
|---|---|---|---|
| Hook (blocks a tool call) | yes — PreToolUse/PostToolUse | **no** — `hooks.json` does not execute (verified 2026-07-18, 0.145.0-alpha.18; re-verify on upgrade) | unverified |
| Gate test (CI) | yes — same repo gates for every seat | yes | yes |
| Rule text (read each session) | `.claude/CLAUDE.md`, resident rules | `AGENTS.md` (contract projection) | `GEMINI.md` / adapter projection (unverified which) |
| Memory (index / recall) | MCP memory tools + Redis index | MCP transport (cross-provider-memory-transport, shipped 2026-07-28) | unverified |
| Lesson (JIT recall on tool use) | yes — hook-driven | **no** (no hooks) — lessons reach Codex only as rule text | unverified |
| Chat | dies with the session | same | same |

The design consequence the card must state plainly: on Codex, "block
it" is not available — the strongest layer there is the gate test, and
a shape rule has to become a CI gate to be enforced at all.

## The three projections

1. **Help page (card 2).** A curated-input path in the help generators
   renders the master into `plugin/help/generated/<kind>/steering-card.md`
   and a genuine quickstart `quickstarts/steer-claude.md` ("open the
   card" → one command). Kind per D2. `--check` drift mode; the
   generator joins `tests/unit/help/test_generated_help_drift.py`.
2. **Contract block (card 3).** `scripts/project_collaboration_contract.py`
   gains a `steering` block: the host table + a one-line pointer to the
   full card, projected into every provider surface it already owns.
   `tests/unit/scripts/test_project_collaboration_contract.py` covers
   it. Governance text → D11 lane on the PR.
3. **Concept page (card 4).** The `essay` slot rendered to the docs
   tree (`docs/concepts/steering-an-ai.md` or the site's equivalent)
   with the abstract layer model: enforcer → test → instructions →
   memory → recall → conversation. No attune names in the body; a
   footer links to cards 2/3 for attune users.

## Drift guards

Every projection has a `--check` mode wired into an existing drift
test; the master's front-matter is validated by a small schema test
(unique `n`, known `section`, `hosts` ⊆ known seats).

## Open design questions (carried in decisions.md)

- D2: which kind holds card 2 — `concept` as-is, or a new `guide` kind?
- D4: does card 4 name attune at all, or only in the footer?
- D5: does the master carry the "give a correction that sticks" recipe
  as a section, or is that card-1-only?
