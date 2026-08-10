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

## Resolved decisions (continued)

- **D4 — what README claims about workflow count/stages. RATIFIED
  (2026-07-12), option (a).** Claim **"20 workflows"** (distinct
  classes) and drop the multi-stage claim entirely.
  `CAPABILITIES.workflows` in `website/lib/features.ts` now derives
  from `len(set(discover_workflows().values()))` (20), not
  `list_workflows()` filtered on a truthy `stages` field (19) — that
  prior derivation counted nearly every workflow, since almost all of
  them set *some* `stages` value; only 3
  (`documentation-orchestrator` 4, `rag-code-gen` 2,
  `release-prep`/`release-gate` 4 as one alias pair) actually declare
  *multiple* stages, so "multi-stage" overclaimed what the number
  measured. Surfaced during a marketing-accuracy review
  (2026-07-12), independent of the four-pass external review that
  opened this spec. Fixed alongside: README's "22 workflows (19
  multi-stage)" → "20 workflows"; the two website copy sites
  (RELIABILITY_LOOP stage 03, the "workflows" PILLARS entry) that
  repeated "19 multi-stage workflows"; and
  `test_workflows_count_matches_registry` in
  `tests/unit/test_website_version_accuracy.py`, which now asserts
  against the distinct-class count.

## Open decisions

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

## 2026-07-20 — D7 and D8 ruled (chair: Patrick, via briefing triage)

- **D7 RULED: CI-only for the test gates (G1/G2/G3); pre-commit
  carries G5 only.** The spec's stated default, ratified as-is:
  pre-commit's isolated env can't guarantee an importable `attune`
  for all contributors. Revisit only if drift keeps reaching CI.
- **D8 RULED: report-only (non-gating).** The inverse-direction
  report (exists-but-unadvertised commands) ships as a warning-tier
  report; reassess after a month of real output. Gating would
  manufacture failures for deliberate soft-launches; dropping it
  loses a cheap signal.

With D4 (2026-07-12) and these two, every open decision on this
spec is resolved — implementation (G1 first per the ship order) is
fully unblocked.
## 2026-07-20 — G1 landed (red-first proven)

`tests/unit/gates/test_claim_drift.py`: live values derived from the
owning registries (skills glob, `EmpathyMCPServer().tools`,
`discover_workflows()` slugs AND distinct classes per D4,
pyproject version) against a 13-entry claim-site manifest across
README, marketplace.json, plugin/README, quickstart-plugin,
mcp-integration, first-steps, and .claude/CLAUDE.md.
Unmatched-regex is itself a failure (vanished claim = drift).

**Red-first receipt:** against the pre-fix tree the gate failed
10 of 14 checks — including drift ACCUMULATED SINCE THE 2026-07-11
REVIEW (skills 24→25, tools 47→53 while docs still said 23/41/43/
47), proving both the thesis and the gate. Same-PR fix set: all 10
flagged instances updated to live values (skills 25, tools 53,
workflows 20 per D4, plugin version 10.5.0); gate green 14/14;
adjacent guards (plugins, website-version, mcp-tools) 300 passed.

Per D7 the gate is CI-only (rides the unit suite); no pre-commit
hook added. Next per ship order: G2.
## 2026-07-20 — G2 landed (red-first proven)

`tests/unit/gates/test_advertised_commands.py`: the advertised set
is extracted by CALLING the render surfaces (`create_parser()`
epilog, `_show_welcome`, `cmd_setup` with `Path.home` pointed at
tmp), never by grepping source. Every line-leading `/token` must
resolve to `src/attune/commands/<name>.md` or
`plugin/commands/<name>.md`.

**Red-first receipt:** exactly the spec's predicted ghosts —
epilog advertised `/testing`, `/workflows`, `/docs` (the epilog
block existed TWICE in cli_minimal.py, both stale) and the welcome
screen advertised `/testing`. Fix set retargeted per the spec's
candidates: `/testing`→`/smart-test`, `/workflows`→`/attune`,
`/docs`→`/doc-gen`, both blocks. Gate green; 116-test gates+cli
breadth.

**D8 inverse report (report-only, as ruled)** fired its first
output: 12 commands exist but are advertised on no CLI surface —
agent, brainstorm, bulk, code-quality, deep-review, doc-gen*,
fix-test, handoff, pipeline, plan, refactor, remember (*doc-gen
now advertised post-fix). Reassess the list after a month.

Next per ship order: G3 (blocked on hook-timeout-budgets Phase 0.2
values) or G5.
## 2026-07-20 — G5 landed (red-first proven); burn-down baseline recorded

`scripts/check_brand_drift.py` (pre-commit gate #9 + CI's
pre-commit job — the one gate D7 keeps in pre-commit) +
`.claude/gates/empathy-allowlist.txt` + gate-logic tests.

**Red-first receipt:** the hard-fail scan found **27 files** —
nine times the spec's predicted red set (the repo moved in the
nine days since review). Fix set: deleted `install.sh`,
`rename_to_attune.sh`, `Dockerfile.scanner`, `bin/empathy-scan`,
`.pre-commit-config.example.yaml` (all dead, references checked);
archived the two root `metrics-review-2026-02-06*.md` to
`docs/history/`; rebranded 20 files of string/comment/default
references (`empathy-framework` → `attune-ai`) across src,
scripts, agents, deployments, examples, tests, and
`.claude/PROJECT-CONTEXT.xml`. Shrink-on-fix fired live during
the fix (two de-branded files forced off the allowlist).

**Burn-down baseline (as ruled by the spec):** 36 user-facing +
107 internal files on the empathy ratchet allowlist. The list
only shrinks; the count prints on every run.

**Documented exclusions:** CHANGELOG, docs/specs/, docs/history/,
lessons corpus, generated website mirrors, the gate's own files;
Redis `empathy:*` wire-format keys remain P2B (data format).

### G5 retro-flag addendum (2026-07-20, fix-set-balloon rule applied in hindsight)

The three behavior-adjacent edits from the G5 sweep, retro-checked
at the chair's request: (1) `deployments/wizards-backend/` — the
app NEVER imports the dependency; the requirement line was dead
weight in both brandings, now deleted outright; the dir carries
Railway configs but no repo-side deploy wiring — chair confirmed
2026-07-20 that NO active Railway services exist (hosting moved to
Vercel); the whole directory is a dead deployment artifact, chipped
for cleanup. (2)
`agent_config.py` `project` default — zero consumers read
`.project` in src/; inert. (3) `.claude/PROJECT-CONTEXT.xml` —
zero consumers; stale artifact, future deletion candidate. All
three retired with grep receipts; the sweep's only correction was
replacing a fictional rebrand with an honest deletion.

## 2026-07-21 — G4(a)+(b) SHIPPED red-first (merge held for post-tag)

The kwarg/attr and MCP-config layers landed as new checkers behind
`audit_doc_imports.py`'s existing walk (per D6), opt-in via
`.claude/gates/doc-deep-check-allowlist.txt` (`<path> :: <reason>`,
reason REQUIRED — a bare path is itself a finding). Seeded with the
five getting-started pages.

**Red-first receipt (4 real findings on first run):**
`choose-your-path.md` documented the dead
`attune.socratic.mcp_server` module (the requirements' literal
example) plus a `socratic` server; `mcp-integration.md`'s
`.claude/mcp.json` fence drifted from the real file (server name
`attune` vs `attune-ai`, `python` vs `uv run python`, stale
`PYTHONPATH` env). All fixed; gate green over the full published
scope (446 imports / 383 fences / 93 files; 5 deep-checked).

**Checker-scope correction found by the red run:** the real-file
diff fired on Claude Desktop config examples too — the spec's
wording ("documented `.claude/mcp.json` fences") is now enforced
literally: the diff runs only when `.claude/mcp.json` is named
within 10 lines above the fence. Kwarg/attr checking is dataclass-
field + signature-bind only (non-dataclass instance attrs skipped —
instance-only attrs would false-positive); fences are still never
executed. The 07-11 red-first fix set had partially self-healed:
the kwarg/attr layer found ZERO live drift (those snippets were
fixed by interim passes) — the live drift was all MCP-config class.

**Remaining G4 scope:** (c) the CONTRIBUTING clean-venv CI lane —
a separate CI job by D6's own carve-out, staged advisory→required;
next G4 unit. G3 stays blocked on hook-timeout-budget Phase 0.2
values.

## 2026-07-21 — G4(c) SHIPPED red-first (same held PR): clean-venv lane

`scripts/extract_contributing_setup.py` extracts CONTRIBUTING.md's
LITERAL setup fence at run time (drift-guard seam: hardcoding the
commands in the workflow would itself be claim-drift), rewriting
only three contracted line classes — `git clone` / `cd attune-ai`
(commented; CI runs in the checkout under test) and the bare
`pytest tests/` verification line (gets `-x -k smoke`). Doc
restructuring fails LOUDLY (missing heading/fence/pytest line →
exit 1). `.github/workflows/contributing-smoke.yml` runs it in a
fresh venv, keyless (empty-string key), on PRs touching the
setup-relevant files + weekly + dispatch. **ADVISORY**
(`continue-on-error: true`); promote to required after two green
weeks per the ci-matrix-right-sizing precedent — promotion check
due ~2026-08-04.

**Red-first receipt (LOCAL live-fire, not simulated):** executing
the doc's then-current literal commands in a fresh venv died with
`pytest: error: unrecognized arguments: -n` (exit 4) — the exact
`[dev]`-extra/pytest-xdist drift the 07-11 fix set predicted: the
doc installed bare `pytest pytest-cov pytest-asyncio` while
pytest.ini's addopts require xdist. Fix: the setup fence now
installs `pip install -e ".[dev]"`. Green rerun: exit 0, 172
passed / 5 skipped in the fresh venv under the doc's own commands.

**G4 is now fully built (a+b+c, one held PR).** The gate family's
remaining unit is G3 only (blocked on hook-timeout-budget Phase
0.2 values).

## 2026-07-21 — G4 build receipt + design-phase waiver (chair)

G4 (a+b+c) is complete on branch `feat/claim-drift-g4` as **held
draft #1561** (`hold-until-07-27`); it merges after the 10.6.0 tag
per the standing merge hold. Recorded here so the spec's stage
reflects reality on main: built, pending merge — not un-started.

The chair ruled this session (AskUserQuestion, 2026-07-21) that the
design phase is waived: G4 was chair-ruled and built without a
design.md, and the requirements header already records every ruling
(D4, D7, D8). The stage ladder honors the marker line below.

PHASE-WAIVED: design (2026-07-21 — chair ruling this session; G4 built without a design phase, held #1561)

## 2026-07-28 — D4 round-tripped 20→19→20 and cost a red `main`

D4 was ratified 2026-07-12. On 2026-07-28 the count was changed
*back* to the rejected derivation, reddened `main`, and was restored
the same morning. Recorded here because the starter is not the home
for a ratified number, and because the failure was not in the gate —
the gate worked exactly as designed.

**Sequence.** #1703 (website-only, 06:33) set
`CAPABILITIES.workflows` 20→19, citing the "stage-filtered registry".
That is the derivation D4 rejected. Website-only PRs skip the Python
suite, so `test_workflows_count_matches_registry` never ran on the PR
that changed the number it guards. `main` went red on the next
full-suite PR — a docs-only lessons append whose diff touched nothing
related. #1704 (07:02) restored 20 and realigned the vitest counter to
`len(set(discover_workflows().values()))`, so both enforcers now share
one definition.

**Root cause was upstream of both guards.**
`.claude/rules/attune/website-content-accuracy.md` — the rule an agent
consults *before* touching a count — still prescribed the
stage-filtered command. #1703's author followed the rule correctly and
got 19. D4's original fix updated the guards and `features.ts` but not
the doc that teaches the derivation, so for sixteen days the rule kept
dispensing the pre-decision answer with full authority.

Fixed in #1706, which also audited the whole table rather than the one
broken row: a second command was dead (`WizardRegistry` no longer
exists — `ImportError`), a row pointed at a registry dropped from
`CAPABILITIES` in 2026-06, and three of the five live counts had no
row at all. The table now carries a precedence line — *if a command
here and the CI guard disagree, the guard wins and this table is the
bug* — so the doc can never again outrank its enforcer.

**Ruling (restates D4, does not amend it).** `CAPABILITIES.workflows`
is **20**: distinct workflow classes,
`len(set(discover_workflows().values()))`. 19 is the stage-filtered
count and is wrong. `release-prep`/`release-gate` and
`orchestrated-health-check`/`health-check` are deliberate alias pairs,
counted once each. `test_workflows_count_matches_registry` is the
authority; prose is not.

**All five counts, live-verified 2026-07-28** (each command executed,
not copied):

| Key | Value | Derivation |
|---|---|---|
| `workflows` | 20 | `len(set(discover_workflows().values()))` — D4 |
| `skills` | 26 | `plugin/skills/` directory count |
| `mcpTools` | 49 | `tool_schemas` `get_*_tools()` total — **core only** |
| `templateKinds` | 15 | `attune_author.generator._ALL_TEMPLATE_NAMES` |
| `wizards` | 5 | `attune.wizards.list_wizards()` |

`mcpTools: 49` counts core `tool_schemas` **only**. `attune_redis`
registers 11 more (5 `session_memory_*`, 6 `redis_*`) with zero
overlap, so the installed surface is **60 registered / 49 core** —
matching the projector figure. Any copy pairing "49 MCP tools" with
"five session_memory tools" is drawing from two registries and the
five are not inside the 49.

**Standing hazard for this spec (unfixed, by design).** Website-only
PRs emit `website_only=true` and the full-suite jobs report green
without running pytest. Claim guards therefore do **not** run on the
class of PR most likely to change a claim; the failure surfaces on
whichever unrelated PR runs the full suite next. Until that gap is
closed, a website-only PR touching a count is unguarded by
construction — run
`python -m pytest tests/unit/test_website_version_accuracy.py -q`
locally before merging one. Whether to close it (e.g. always run the
claim guards regardless of path filter) is a live question for this
spec, not a ruled decision.

## 2026-08-10 — G4(c) stays advisory; promotion check moved to 2026-09-07 (chair)

**Ruled** via the Monday chair-rulings form ("Keep advisory, new
check date"): `contributing-smoke.yml` keeps
`continue-on-error: true` past the original ~2026-08-04 promotion
check. New promotion check: **2026-09-07** (date lead-proposed at
recording time — a four-week window matching the original cadence;
chair may amend). At that check the same three-way fork applies:
promote to required, extend advisory again, or retire the lane.
