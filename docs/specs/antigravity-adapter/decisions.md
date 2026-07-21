# Antigravity Adapter — Decisions

**Status:** shipped (2026-07-21) — completion pass below;
reopen condition: Antigravity self-update breaks a verified
mechanism

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

## D3 — surface parity: CLOSED (2026-07-18) — restored via `.agents/AGENTS.md` mirror (#1445)

Final state: both surfaces verified loading the contract. CLI via
the rule file's @-reference (D1 receipts); IDE via the projected
`.agents/AGENTS.md` mirror in its workspace customization root.
The probe ladder below is the receipt trail for how the initial
FAIL was localized and fixed.

### Initial receipt: FAIL — IDE loads the rule but does NOT inline @-references

Live receipt, 2026-07-18, Antigravity IDE (app 2.3.1), workspace
`~/attune-ai` on `main` at `1e1889b59` (clean tree, adapter and
contract verified present before the probe). Patrick ran the
probes in the IDE agent panel; scored against that revision.

1. **Contract probe (same as CLI AC-2): NOT IN CONTEXT.** The
   preflight script and artifact tiers — verbatim-quotable in the
   CLI receipts — did not load.
2. **Discriminating three-part probe localized the break:**
   - Rule BODY loads: the sentinel phrase "cross-provider
     collaboration contract for this repository" was quoted back.
     (So file discovery + activation work in the IDE too.)
   - The `@../../AGENTS.md` reference was quoted back as LITERAL
     TEXT — the IDE serves it un-expanded.
   - `collaboration_preflight.py` (content that exists only in the
     referenced AGENTS.md): NOT IN CONTEXT.

Diagnosis: the CLI (`agy` 1.1.4) expands rules-file-relative
@-references; the IDE (app 2.3.1) does not expand @-references at
all. The adapter's zero-drift trick is CLI-only. Same family as
the CLI's own `@/AGENTS.md` silent no-op (AC-2 item 3): @-form
support is fragile and surface-specific across this product.

Lead for the fix: the IDE's own loaded instructions contain
"Append rules to the `AGENTS.md` file in one of the customization
roots, depending on scope" — the IDE may support AGENTS.md
NATIVELY from specific roots (workspace root evidently not among
them, or not auto-loaded, since item 3 failed). Next probe: ask
the IDE to enumerate its customization roots.

Fix options:

- (a) Probe the customization roots; if one is repo-reachable and
  tracked, AGENTS.md lands there natively and the rule file stays
  as-is for the CLI.
- (b) Make the projector write the full contract block INTO
  `.agents/rules/collaboration-contract.md` (new projection
  target). Guaranteed on both surfaces; costs the by-construction
  drift-freedom, regains it via the projector's `--check` gate.
  Keep the @-reference line too — harmless where unsupported.

### Customization-roots receipt → fix (a) selected (2026-07-18)

IDE enumeration probe (quoting its loaded context): global root
`/Users/patrickroebuck/.gemini/config`; workspace root `.agents`
(relative to the workspace root). So `.agents/` IS the workspace
customization root — which retro-explains the whole D3 result:
the rule file loaded because it lives under `.agents/`, and
repo-root `AGENTS.md` never loaded because it sits OUTSIDE the
root and the @-bridge doesn't expand in the IDE.

Fix (a): project `.agents/AGENTS.md` as a new fully-generated
projector target (byte-copy of root `AGENTS.md`), so the IDE
loads the contract natively from its customization root. Not a
symlink — Windows checkouts. Rule file stays for the CLI.
Re-probe in the IDE after landing to close D3.

### Closing receipt: IDE contract probe PASS (2026-07-18, post-#1445)

Shipped in #1445 (squash `cc2e7d1a2`): projector emits
`.agents/AGENTS.md` as a fourth target (byte-copy of root
`AGENTS.md`, created-if-missing, `--check` drift-guarded; two new
projector tests). All 10 required CI contexts green including the
Windows lane.

Patrick re-ran the original contract probe in the IDE (workspace
`~/attune-ai` on the merge commit), no-tools fence. The IDE
answered BOTH halves verbatim from loaded context: the preflight
script with its full constraint list ("read-only, uses cached Git
refs, and does not fetch, pull, switch branches, invoke `uv`, or
create an environment") and all four artifact tiers with their
one-line definitions. Same content the CLI receipts quoted —
surface parity holds. D3 CLOSED.

Carried risk (unchanged from D1): the IDE-native
`.agents/AGENTS.md` load path and the CLI's `trigger:` frontmatter
+ relative @-expansion are verified behaviors on app 2.3.1 /
agy 1.1.4 — re-verify after self-updates.

## 2026-07-21 — Completion pass: spec shipped (chair-requested)

All design forks resolved and every acceptance criterion receipted;
the stale "D3 still open" status line is corrected in this pass.

| AC | Receipt | Where |
|---|---|---|
| AC-1 skills (zero-work) | PASS 41/41 mirrored skills discovered (`--add-dir`/workspace required — recorded caveat) | entry above (2026-07-18) |
| AC-2 contract via rules | PASS with two doc-vs-tool corrections (`trigger: always_on` frontmatter; rules-file-relative `@`-paths) | entry above + transcripts |
| AC-3 drift guard | D1=(a) ruled, so the (b)-conditional lapses; #1445's `.agents/AGENTS.md` fourth projector target carries `--check` drift-guarding + two tests anyway | #1445 (`cc2e7d1a2`) |
| AC-4 preflight + checks | Re-run LIVE this pass: preflight 0 failed (governance 76 passed, skills-projection in sync), `project_collaboration_contract.py --check` all four targets unchanged, `sync_agents_skills.py --check` 42 ok | this entry |
| AC-5 full keyless suite | All 10 required contexts green incl. the Windows lane | #1445 |

R1-R6 hold: contract reaches Antigravity mechanically (rule file +
`.agents/AGENTS.md` byte-copy), skills mirror consumed as-is, R4
preflight check silent-when-absent, global config untouched. No
design.md was ever authored — the design forks (D1-D3) lived in
requirements.md and were resolved by receipts in this file; the
stage ladder reads this spec as shipped from the terminal statuses.

**Carried risk (standing, unchanged):** the verified behaviors are
pinned to app 2.3.1 / agy 1.1.4 — re-verify the `trigger:`
frontmatter, relative `@`-expansion, and IDE `.agents/AGENTS.md`
load path after Antigravity self-updates. Reopen via a dated entry
here if a self-update breaks either mechanism.
