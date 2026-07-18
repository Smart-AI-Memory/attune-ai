# Antigravity Adapter — Decisions

## D1 — contract delivery: RATIFIED (a) — 2026-07-18, Patrick

Live receipts, 2026-07-18, Antigravity app 2.3.1 + `agy` CLI 1.1.4
(`~/.local/bin/agy`; authenticated silently with no browser flow — the OS-keyring path; the exact token source was not verified).
All runs: `agy --add-dir <workspace> -p "<prompt>" --mode plan` from
the workspace root. Every probe instructed "without using any tools;
if not in loaded context reply NOT IN CONTEXT" so answers could only
come from loaded context.

### AC-1 — skills discovery: PASS (41/41)

- Bare `agy -p` had NO workspace ("no active workspace set") and
  listed only Antigravity's 10 built-in skills — `--add-dir` (or a
  real project/IDE workspace) is REQUIRED for workspace skills.
- With the workspace bound, the agent listed 40 of the repo's 41
  `.agents/skills/` mirrors by name (attune-hub, spec,
  security-audit, ...). Zero-work claim holds.
- `verify` was absent from the first enumeration but a direct
  probe ("is a workspace skill named 'verify' available?")
  returned yes with its exact description — the omission was
  single-run LLM listing slippage, not a discovery gap. Lesson
  for receipt design: enumeration answers are lossy; probe
  specific names when a count matters.

### AC-2 — contract via rules: PASS, with two doc-vs-tool corrections

1. **Control (no rule file): NOT IN CONTEXT** — Antigravity does
   NOT natively read `AGENTS.md`. An adapter is required; the
   spec's premise holds.
2. **A bare markdown rule in `.agents/rules/` does NOT load.**
   Sentinel token in the rule body → NOT IN CONTEXT. The docs'
   Rules page never mentions file frontmatter (activation is "set
   at the rule level" in the UI), but the file needs
   `---\ntrigger: always_on\n---` frontmatter — with it, the
   sentinel is returned. UNDOCUMENTED, verified against the tool.
3. **`@/AGENTS.md` (docs' absolute-then-workspace form) did NOT
   inline** — contract questions stayed NOT IN CONTEXT while the
   sentinel in the same rule body succeeded. The RULES-FILE-
   RELATIVE form `@../../AGENTS.md` DOES inline: the agent then
   named the four artifact tiers (inline edit / structured
   one-shot / XML task / spec) and quoted the Session protocol
   bullet verbatim.
4. **Fidelity bonus receipt**: the workspace was a worktree at
   pre-#1439 base `ced32cd7e`, whose AGENTS.md predates the
   preflight bullet — and the agent answered exactly that item
   NOT IN CONTEXT while quoting the bullets that DO exist in that
   file revision. The @-reference serves the live file content,
   not cached or hallucinated text.

### Resulting adapter (staged at `.agents/rules/collaboration-contract.md`)

```markdown
---
trigger: always_on
---

The cross-provider collaboration contract for this repository applies
to every agent session. Its full current text follows from the
referenced file and is part of your operating instructions:

@../../AGENTS.md
```

**RATIFIED (a)** (2026-07-18, Patrick, after receipts) — one 9-line tracked file, no
new projection target, drift-free by construction (the reference
inlines whatever the projector last wrote to AGENTS.md). Risks to
carry into design: the `trigger:` frontmatter and the relative-path
resolution are behaviors verified on agy 1.1.4 / app 2.3.1, not
documented — pin both in a receipt-style test note and re-verify on
CLI updates (the binary self-updates in the background).

### D1b — adapter @-target: AGENTS.md, deliberately (reviewed)

Considered referencing the provider-neutral master
(`content/collaboration/contract.md`) instead. Kept `AGENTS.md`:
its 1,902 chars outside the contract markers are generic repo
orientation (Overview, Commands, agent-state locations) that
benefits any agent, and the projector rewrites AGENTS.md on every
contract change, so drift-freedom is identical. Revisit only if
AGENTS.md accretes truly Codex-specific instructions.

### Post-ff fidelity receipt (before/after pair)

After fast-forwarding the worktree to current main (f3ecedc91,
post-#1439), the previously-NOT IN CONTEXT probe now returns the
preflight bullet verbatim: "python scripts/collaboration_preflight.py
… read-only, uses cached Git refs, does not fetch, pull, switch
branches, invoke uv, or create an environment," citing AGENTS.md.
Same adapter, same probe, different file revision — the reference
tracks the live projected content.

## D2 — `.agents/` tracking: rules file joins the tracked adapter set

`.agents/` is already tracked (skills mirror). The one rule file is
hand-owned (like `.gemini/settings.json` in the sibling spec). No
`.gitignore` change needed for Antigravity itself; decide separately
if local Antigravity state dirs appear.

## D3 — surface parity: CLI verified; IDE pending

All receipts above are CLI (`agy` 1.1.4). The IDE (app 2.3.1)
presumably shares the rules engine; verify once in the IDE before
closing D3 (open the workspace, ask the same two questions).
