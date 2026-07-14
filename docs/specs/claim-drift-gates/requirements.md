# Spec: Claim-drift gates

**Status:** approved (2026-07-11) — see `decisions.md`; D4 ratified 2026-07-12 (option a, "20 workflows"); D7, D8 remain open; G1's claim manifest is now unblocked
**Opened:** 2026-07-11
**Layer:** attune-ai (tests / pre-commit / docs / plugin metadata)
**Owner:** Patrick + agent

---

## Problem

Every hand-maintained claim about the system drifts; every
machine-derived claim stays true. The 2026-07-11 external review
(four independent passes over `main` @ v10.2.0) verified the pattern
exhaustively:

**Machine-derived claims — all accurate:**

- "47 MCP tools" (README) — exactly 47 registered, every schema has
  a dispatch handler (`tool_schemas.py`, `server.py:270-318`).
- "20,000+ tests" badge — 20,363 `def test_` functions, and
  `scripts/check_badge_freshness.py` gates the floor in CI.
- Wheel contents — clean, because `MANIFEST.in` is executable policy.

**Hand-maintained claims — all drifted:**

| Claim | Says | Reality |
|-------|------|---------|
| `quickstart-plugin.md:24` | 17 skills | 24 (`plugin/skills/*/SKILL.md`) |
| `plugin/README.md:4` | 18 skills | 24 |
| `marketplace.json`, README:313 | 23 skills | 24 |
| `first-steps.md:68` | 17 workflows | 22 slugs registered |
| README:41-42 | "22 workflows (19 multi-stage)" | 20 distinct classes (2 alias pairs); ~3 declare multiple `stages` |
| `mcp-integration.md:91` | 41 + 5 tools | 47 with zero extras |
| `plugin/README.md` | Version: 8.5.0 | 10.2.0 |
| `.claude/CLAUDE.md` (memory) | v5.0.0 | 10.2.0 |
| CLI welcome/epilog (`cli_minimal.py:47-52,535-546`) | advertises `/testing`, `/workflows`, `/docs` | none exist in `src/attune/commands/` |
| `hooks.json` Stop timeout 15,000ms | implies stash completes | internal Ollama default 40s (`session_stash.py:225-227`) — killed every time Ollama is warm-loading |
| `hooks.json` SessionStart 3,000ms | implies recall completes | up to 3 × 4s `gh pr view` calls (`session_recall.py:60-61`) |
| `choose-your-path.md:59-68` | configure `attune.socratic.mcp_server` | module removed v6.3.0 |
| `choose-your-path.md:87-96` | `execute(target_path=)`, `result.findings` | real API: `path=`; `WorkflowResult` has no `findings` |
| `mcp-integration.md:37-50` | `.claude/mcp.json` uses `python` + PYTHONPATH | actual file uses `uv run` |
| `installation.md:28` | `[redis]` extra enables memory | empty no-op alias since 2026-07-04 |
| `install.sh` | installs the product | installs `empathy-framework` from `Deep-Study-AI` |
| CONTRIBUTING.md setup | `pip install -e .` + 3 pytest pkgs → `pytest tests/` | fails: `addopts` needs `-n auto` (pytest-xdist); `[dev]` extra never mentioned |

None of these are one-off mistakes. They are one *class* of failure:
a claim was true when written, the code moved, and nothing forced the
claim to move with it. Fixing the instances without landing gates
guarantees a repeat — the project has already fixed count drift by
hand at least once (plugin/README's "18" was presumably once true).

This spec's thesis: extend the badge-freshness pattern (machine
checks the claim, CI fails on drift) to every hand-maintained claim
surface, land each gate red, and fix the flagged instances in the
same PR until green.

## Verified context (grounded)

| Fact | Source |
|------|--------|
| Live registries exist for all three counts | `discover_workflows()`, `EmpathyMCPServer().tools`, `plugin/skills/*/SKILL.md` glob — all verified importable/countable in review |
| `release-prep`/`release-gate` and `health-check`/`orchestrated-health-check` are alias pairs | `workflows/__init__.py:304-311` (comment documents the alias deliberately) |
| Precedent gate #1: badge freshness | `scripts/check_badge_freshness.py`, run in `tests.yml:312` |
| Precedent gate #2: doc import audit | `scripts/audit_doc_imports.py` (verifies `import attune…` lines in served docs per-PR) |
| Precedent gate #3: budget-style unit test | `tests/unit/rules/test_rules_residency_budget.py` |
| Precedent rule (prose, not executable) | `.claude/rules/attune/plugin-reference-validation.md` ("A broken reference produces a silent failure at runtime") |
| Precedent rule (prose, not executable) | `.claude/rules/attune/website-content-accuracy.md` |
| 8 custom local pre-commit gates already exist | `.pre-commit-config.yaml` |
| `src/` files matching "empathy" | 117 files / 534 hits; user-facing leaks include `EMPATHY_*` env-var docs (`workflows/config.py:654-658`), `__all__` exports, SKILL.md text, 34 generated help files |
| Redis wire-format keys still `empathy:*` | `telemetry/agent_coordination.py:116`, `redis_memory_storage.py:47-51` — persisted data format |

## Relationship to existing specs / gates (complementary, not duplicate)

- **`check_badge_freshness.py`** — same philosophy, scope = README
  badges only. This spec generalizes it; does not replace it.
- **`audit_doc_imports.py`** — same philosophy, scope = import lines.
  Gate G4 extends it to kwargs/attrs and MCP-config module paths
  rather than building a parallel auditor.
- **`plugin-reference-validation.md` / `website-content-accuracy.md`**
  — the *rules* already exist as prose. G1/G2 are their executable
  forms; the rule files should end up pointing at the tests.
- **`hook-timeout-budgets` spec (Phase 0.2)** — fixes the two live
  timeout bugs. G3 here is the regression gate that keeps them fixed;
  land G3 in the same PR or immediately after.
- **`onboarding-happy-path` spec (Phase 2)** — rewrites the entry
  docs. Blocked by this spec: rewritten docs must be born under
  G1/G4 so they can't re-drift.

---

## Goals

- Every count, version, command name, timeout budget, and code
  snippet asserted in a user-facing surface is either machine-derived
  at build time or covered by a CI gate that fails on drift.
- Each gate lands **red first**, then the same PR fixes every flagged
  instance until green (proves the gate actually catches the class).
- Gates are cheap (< a few seconds each, keyless, no network) so they
  run on every PR without matrix cost.
- The empathy-naming debt gets a ratchet (allowlist that only
  shrinks), not a big-bang rename.

## Non-goals

- Not rewriting the onboarding docs' *content or structure* — that's
  `onboarding-happy-path`. This spec only makes their claims true and
  keeps them true.
- Not fixing the hook timeout *values* — that's `hook-timeout-budgets`.
  G3 only enforces the invariant.
- Not migrating Redis `empathy:*` key prefixes (data format; P2B,
  next-major trigger). G5 explicitly excludes them.
- Not deciding what the README *should* claim about multi-stage
  workflows — G1 forces the decision (D4) but the wording is
  editorial.

---

## Proposed approach — five independently-shippable gates

Ship order: G1 → G2 → G3 → G5 → G4 (cheapest-to-land first within
each dependency; G4 last because it has the largest fix surface).

### G1. Count-and-claim drift guard (unit test)

`tests/unit/gates/test_claim_drift.py`. Derive live values:

- skills: `len(glob("plugin/skills/*/SKILL.md"))`
- MCP tools: `len(EmpathyMCPServer().tools)` (keyless construction —
  verified the server builds its tool list without credentials)
- workflows: `len(discover_workflows())` and
  `len(set(registry.values()))` (slugs vs distinct classes — assert
  both; README must use whichever D4 ratifies)
- version: `pyproject.toml [project].version`

Then scan a **manifest of claim sites** (file + regex + which live
value) covering: README.md, marketplace.json, plugin/README.md,
quickstart-plugin.md, first-steps.md, mcp-integration.md,
.claude/CLAUDE.md. The manifest is data (one dict in the test file),
so adding a new claim site is a one-line diff. Unmatched-regex is
itself a failure (a claim site that disappears silently is drift too).

*Red-first fix set:* the seven count/version rows in the Problem
table, plus the D4 wording decision.

### G2. Advertised-command reference validation (unit test)

Assert every `/command` token printed by `_show_welcome`, `cmd_setup`,
and the argparse epilog resolves to `src/attune/commands/<name>.md`
or `plugin/commands/<name>.md`. Extract the advertised set by calling
the render functions, not by grepping source, so refactors can't
bypass it.

*Red-first fix set:* `/testing`, `/workflows`, `/docs` (retarget to
real commands — `/smart-test`, `/dev`, `/doc-gen` are candidates — or
delete the lines). Also assert the inverse direction as a warning
tier: commands that exist but are advertised nowhere (discoverability
report, non-gating).

### G3. Hook-budget self-audit (unit test)

For each hook in `plugin/hooks/hooks.json`, require the hook module
to expose its worst-case internal budget (a module-level
`WORST_CASE_MS` derived from its own timeout constants × retry
counts) and assert `WORST_CASE_MS <= hooks.json timeout`. A hook
without the declaration fails the test — new hooks are born budgeted.
Modeled on `test_rules_residency_budget.py`.

*Red-first fix set:* whatever `hook-timeout-budgets` (Phase 0.2)
decides for `session_stash.py` (15s vs 40s Ollama) and
`session_recall.py` (3s vs 12s gh calls).

### G4. Onboarding-snippet execution gate (extend `audit_doc_imports.py`)

Three additions, each behind an allowlist with a required reason
string:

a. **Kwarg/attr layer** — for allowlisted Python snippets in
   `docs/getting-started/**`, resolve called signatures and accessed
   attributes against the live API (catches `target_path=` /
   `result.findings`).
b. **MCP-config module paths** — resolve `"-m <module>"` / `args:`
   values inside JSON fences to importable modules (catches
   `attune.socratic.mcp_server`); also diff documented `.claude/mcp.json`
   fences against the real file.
c. **CONTRIBUTING clean-venv lane** — a CI job executing
   CONTRIBUTING.md's literal setup commands in a fresh venv (seed
   from `smoke_default_install.sh`), keyless, `-x -k "smoke"` subset.

*Red-first fix set:* choose-your-path.md (socratic server, wrong
kwargs/attrs, "empathy CLI"), mcp-integration.md (mcp.json fence,
both Quick Test snippets, 41+5 count — count part covered by G1),
installation.md (`[redis]` no-op), CONTRIBUTING.md (`[dev]` extra /
pytest-xdist), first-steps.md (`attune setup` prerequisite for
`/wizard`).

### G5. Stale-brand lint + empathy ratchet (pre-commit + CI)

`scripts/check_brand_drift.py` as pre-commit gate #9:

- **Hard fail, no allowlist:** `empathy-framework`, `Deep-Study-AI`,
  `empathy-scan` anywhere in the repo.
- **Ratchet:** `empathy` matches in `src/`, `docs/getting-started/`,
  `plugin/` outside `.claude/gates/empathy-allowlist.txt` (seeded
  with today's 117 files). The gate fails if a file *not* on the
  allowlist gains a match, and fails if the allowlist contains a
  file that no longer matches (forces shrink-on-fix). Two sections
  in the allowlist file — `# user-facing` and `# internal` — so the
  burn-down priority is visible in the diff.
- **Exclusion (documented in the gate's header):** Redis key-prefix
  constants (`empathy:signal:` etc.) — data-format migration, P2B.
- Print the remaining count per tier on every run (ambient burn-down
  metric, same trick as the coverage gate).

*Red-first fix set:* `install.sh` + `rename_to_attune.sh` deletion
(Phase 0.1), `choose-your-path.md:26` "empathy CLI".

---

## Done when

- All five gates run green in CI and (G5, plus G1–G3 if fast enough)
  in pre-commit.
- Each gate's landing PR shows the red→green sequence: gate commit
  fails CI, fix commits bring it green, squash-merged together.
- Every row in the Problem table is either fixed or explicitly
  re-homed (hook timeouts → `hook-timeout-budgets`; doc structure →
  `onboarding-happy-path`; D4 wording ratified in decisions.md).
- `plugin-reference-validation.md` and `website-content-accuracy.md`
  rule files are updated to point at their executable gates.
- The empathy allowlist is committed with both tiers populated and
  the user-facing tier count recorded in decisions.md as the
  burn-down baseline.

## Risks

- **Gate brittleness → gate deletion (highest).** If G1's regexes
  false-positive on ordinary prose ("47 ways to...") or G4's kwarg
  resolution fights every doc edit, the gates get `# noqa`'d into
  uselessness. Mitigate: manifest-driven claim sites (explicit, not
  repo-wide grep), allowlists with required reason strings, and a
  hard budget — each gate < 5s keyless or it doesn't ship.
- **Keyless construction assumptions (medium).** G1 imports the MCP
  server and workflow registry at test time; if a future change makes
  construction require credentials/network, the gate breaks in CI.
  Pin the keyless contract with its own assertion (construction
  succeeds with env scrubbed) so the failure mode is explicit.
- **Alias-count ambiguity re-drifts (medium).** If D4 lands "20
  workflows" but a future alias is added, slugs (23) vs classes (21)
  diverge again silently. G1 asserts both numbers and the claim
  manifest binds README to one of them by name — divergence then
  fails loudly instead of silently.
- **Ratchet fatigue (low).** The empathy allowlist could sit static
  forever. Accept: this spec only guarantees no *new* debt; burn-down
  pace is a Phase-4/opportunistic concern. The per-run count print
  keeps it visible without nagging.
- **CONTRIBUTING lane flake (low).** A clean-venv pip install in CI
  adds a network-dependent job. Cache wheels, pin to the lockfile,
  and mark the lane advisory for the first two weeks before making
  it required (same staging pattern as ci-matrix-right-sizing).
