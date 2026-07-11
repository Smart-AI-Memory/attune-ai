# Decisions — Claim-drift gates

**Status:** approved (2026-07-11)

Append-only log. See `requirements.md` for the problem framing.

---

## Context that motivated the spec (2026-07-11)

Opened after the 2026-07-11 external critical review (four
independent passes over `main` @ v10.2.0), which verified ~17
instances of hand-maintained claims drifted from code — skill counts
wrong on three of our own surfaces simultaneously (17 vs 18 vs 23 vs
actual 24), the CLI welcome screen advertising three slash commands
that don't exist, `install.sh` installing the pre-rename
`empathy-framework` package, hooks.json budgets that make the memory
stash physically unable to complete, and getting-started snippets
that fail against the real API. The same review confirmed every
*machine-checked* claim (47 tools, 20k tests badge, wheel contents)
was exactly accurate.

The pattern is the project's own thesis inverted: we sell
deterministic gates between agents and code, while our claims about
ourselves are gated by nothing. `check_badge_freshness.py` proved
the fix pattern in miniature; this spec is that pattern applied to
every claim surface.

## Resolved decisions

- **D1 — gate-before-fix protocol. RATIFIED (2026-07-11).** Every gate lands red first; the fix commits land in the
  same PR until green; squash-merge preserves the red→green sequence
  in the PR history. Rationale: a gate that has never been red is
  unproven against its failure class; and fixing instances without
  the gate is how plugin/README's "18 skills" happened (true once,
  then drifted). This mirrors how badge freshness was landed.

- **D2 — where gates live. RATIFIED (2026-07-11).**
  G1/G2/G3 are plain pytest unit tests under `tests/unit/gates/`
  (they need importable `attune`, so pre-commit-only would miss
  environment drift); G5 is a pre-commit hook + CI (pure grep, no
  import needed, and pre-commit gives the fastest author feedback on
  the ratchet); G4 extends the existing `audit_doc_imports.py`
  CI wiring rather than adding a new entry point. Rationale: match
  each gate to the cheapest layer that can actually evaluate it;
  reuse the 8-gate pre-commit pattern and the existing doc-audit
  plumbing instead of inventing a third mechanism.

- **D3 — counts derive from live registries, never fixtures.
  RATIFIED (2026-07-11).** G1 imports
  `discover_workflows()` and constructs `EmpathyMCPServer()` at test
  time with env scrubbed, and asserts keyless construction as its own
  invariant. No snapshot files, no hardcoded expected counts — the
  only hardcoded artifact is the claim-site manifest (file + regex +
  binding). Rationale: a fixture is just another hand-maintained
  claim; the review showed exactly one source of truth stays honest —
  the registry the code actually runs.

- **D5 — empathy ratchet scope. RATIFIED (2026-07-11).** The G5 allowlist covers `src/`, `docs/getting-started/`,
  and `plugin/`; two tiers (`user-facing`, `internal`); shrink-only
  in both directions (new match outside allowlist fails; stale
  allowlist entry fails). Redis wire-format key prefixes
  (`empathy:signal:`, `empathy:heartbeat:`, `empathy:session`) are
  excluded by name with a pointer to the P2B migration item —
  renaming persisted key formats via lint pressure would corrupt the
  one surface where "just fix the string" causes data loss.
  `EMPATHY_*` env vars are *included* (user-facing tier) but the fix
  is add-`ATTUNE_*`-alias-and-deprecate, not remove.

- **D6 — G4 extends `audit_doc_imports.py` rather than a new
  auditor. RATIFIED (2026-07-11).** The import auditor
  already has the doc-walking, fence-extraction, and CI wiring; the
  kwarg/attr and module-path layers are new checkers behind the same
  walk. A second parallel doc auditor would itself become a drift
  surface. The CONTRIBUTING clean-venv lane is the exception — it's
  a CI job, not a checker — and stages advisory→required over two
  weeks per the ci-matrix-right-sizing precedent.

## Open decisions

- **D4 — what README claims about workflow count/stages. OPEN —
  needs Patrick.** The registry has 22 slugs over 20 distinct
  classes (`release-prep`/`release-gate`,
  `health-check`/`orchestrated-health-check` are deliberate alias
  pairs); only ~3 workflows declare multiple `stages`
  (documentation-orchestrator 4, help-maintenance 5, rag-code-gen 2).
  Options:
  (a) claim **"20 workflows"** (distinct classes) and drop the
      multi-stage claim entirely — cleanest, slightly undersells;
  (b) claim **"22 workflow commands"** (slugs) — defensible wording,
      G1 binds to the slug count;
  (c) keep "multi-stage" but redefine it against internal agent-team
      steps and expose that number from the registry so G1 can bind
      it — most work, preserves the marketing point honestly.
  Recommendation: (a) or (b); (c) only if the multi-stage framing
  matters for positioning. G1 ships with the claim manifest bound to
  whichever is ratified.

- **D7 — G1/G2/G3 in pre-commit as well as CI? OPEN.** They need an
  importable `attune`, which pre-commit's isolated env doesn't
  guarantee for all contributors. Default: CI-only for the test
  gates, pre-commit for G5 only. Revisit if drift keeps reaching CI.

- **D8 — inverse-direction command report (exists-but-unadvertised).
  OPEN.** G2's warning tier lists real commands the welcome screen
  never mentions. Gate it, report it, or drop it? Default: report
  only (non-gating), reassess after a month of output.

---

## Spec approval (2026-07-11)

Patrick approved the spec as drafted. D1, D2, D3, D5, D6 ratified;
D4 (workflow-count wording), D7 (pre-commit scope for test gates),
and D8 (inverse command report) remain open. G1's claim manifest
is the only work item blocked on an open decision (D4).
