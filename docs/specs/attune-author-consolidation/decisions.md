# attune-author Consolidation — Decisions

**Status:** active (2026-07-21; opened 2026-06-30) · log for
[requirements.md](requirements.md) / [design.md](design.md).

## D1 — The split is authoring vs. mechanics, not "the package"

**Decided.** The unit of the retire/absorb decision is not the package but
the *kind of work* each part does. Authoring (judgment) → the driving
session + a skill; mechanics (deterministic transform/hash/verify) → code
in attune-ai. A model is the right tool for the first and the wrong tool
for the second, because the second's value is invariance. This is the line
the whole spec follows; everything else is bookkeeping.

## D2 — Absorb the projector/staleness/fact-check; do NOT replace them with instructions

**Decided.** Pushback resolved: "replace code with instructions" is right
for the LLM authoring machinery and *wrong* for the deterministic
distribution machinery. The projector's value is that the fan-out can't
vary; staleness is a hash comparison; the import gate is deterministic
truth. Replacing any of these with model judgment reintroduces the drift
single-source exists to eliminate. They move as code.

## D3 — Retire the authoring machinery; the session replaces it

**Decided.** `generator`/`polish`/`doc_gen`/`maintenance_batch`/
`faithfulness` and the `ai` deps are deleted, not absorbed. The lesson is
empirical: the keyless regen is a content-*stripping* regression and the
driving session is a *superior* polish layer that also catches correctness
bugs the API polish cannot. We are deleting a measured-worse path.

## D4 — Fold #1191's T1 into the move, don't bolt it on

**Decided.** #1191 (merged spec) called for an authoritative resolver. Its
T1 originally meant "wire attune-ai's resolver across the package line."
Once the fact-check moves *into* attune-ai (D2), the resolver is just a
shared in-repo helper — strictly cleaner. So #1191's implementation
happens *inside* this consolidation (design Step 2 / T2), not as a separate
cross-package patch. The merged #1191 spec stays the rationale; this spec
is its execution venue.

## D5 — Code move and package retirement are SEPARATE decisions

**Decided.** Moving the code into attune-ai (reversible, low-risk) and
yanking the `attune-author` PyPI package (irreversible-ish) are decoupled.
Capture the architectural win first (T1–T3); make the package's fate a
deliberate, later step (T4). Because there are no adopters (confirmed
beta), archive-and-yank is viable — but it's still its own PR so the
irreversible action is intentional.

## D6 — `polish_template` degrades, by design

**Decided.** `personal.py`'s optional polish (the one non-docs consumer of
the LLM path) drops to its existing `_build_skeleton` fallback. It is safe
(already `try/except → None`) and consistent with the thesis (no API
polish; the session is the polish layer). Named as a behavior change in
the changelog, not discovered silently later.

## D7 — Absorb staleness as-is; fixing it is a separate spec

**Decided.** `staleness.py`'s known weaknesses (single-file hash, no
completeness check — lessons corpus) are real but out of scope. Absorbing
and then rewriting in one move would balloon the change and couple a
mechanical migration to a behavioral redesign. Absorb first; the staleness
hardening is a tracked follow-on.

## D8 — Dogfooding the absorb reframes T2: it is a bug-fix + design call, not a mechanical repoint

**Decided (2026-07-01).** Refines D7. Copied `staleness.py` +
`manifest.py` + `freshness/symbols.py` verbatim into `attune.authoring`
(imports repointed, provenance headers, imports clean). Then dogfooded the
absorbed `check_staleness` against this repo's real `.help/` — and against
the *current* live behavior of the `help_data` consumer — and found two
facts that make a "behavior-preserving repoint" of `help_data` impossible:

1. **The current dashboard staleness signal is a masked crash.** The
   `attune-author` CLI shim on this machine points at a Python without
   `attune_author` installed → `ModuleNotFoundError`. `help_data`'s
   `_attune_author_stale_features` runs it via `subprocess.run(check=False)`,
   the subprocess exits non-zero with an empty stdout, and
   `_parse_status_output("")` returns `frozenset()`. So a **crash reads as
   "nothing stale"**, and because the return is an empty set (not `None`),
   callers never reach the age-based fallback. This is a latent bug the
   absorb surfaced — a broken CLI silently reports every feature fresh.
2. **Hash-staleness is N/A for this repo.** Post single-source rollout all
   27 features are `status: manual` with **no `files:` globs**
   (projector-owned from `content/features/*.md`). `manifest.py` doesn't
   even parse the `status` field — manual-skip lives in the generator layer,
   not in `check_staleness`. So a faithful `check_staleness` computes the
   empty-input hash for every feature and flags **all 27 stale** (leftover
   stored hash ≠ empty). Faithful behavior is pure noise here.

So T2 is not "absorb → repoint, behavior-preserving." The current behavior
is a bug; the faithful behavior is noise. Doing it right means teaching
staleness to treat glob-less/manual features as **untracked (N/A)** — a
product-semantics decision. **Parked** (Patrick, ~5am) to make that call
rested. The three absorbed modules live on branch `feat/authoring-staleness`
(WIP, no PR) for the next session. Pairs with the "registered ≠ working /
dogfood the real path" and "should-this-exist" (removing-dead-code) lessons.

## D9 — Both D8 blockers resolved

**Decided (2026-07-01).** The two facts D8 parked on are now settled, and
T2a executes the absorb on top of both.

- **(a) Masked-crash: FIXED + SHIPPED standalone in #1203** (merged,
  `383a252c1`). `help_data`'s subprocess wrapper now treats an
  `attune-author status` non-zero exit as "unknown" (→ `None` → age
  fallback), not "clean" (→ `frozenset()`). T2a then removes that
  subprocess path entirely (the CLI is severed), so the class of bug is
  gone at the root, not just guarded.
- **(b) Glob-less/manual staleness semantics: DECIDED — filter in the
  `help_data` consumer.** Manual features with no `files:` globs report as
  *untracked (N/A)*, not *stale*: `_stale_features` excludes glob-less
  features from the drift check (and from the result), so the all-manual
  repo reports zero drift instead of a wall of 27 false positives. The
  absorbed `check_staleness` / `manifest.py` stay **byte-identical to
  upstream** (preserves golden verification). **Rejected:** teaching the
  module itself to skip glob-less features — the semantics belong to the
  consumer, not the shared hashing primitive.

## D10 — LLM polish is preserved but moves UPSTREAM onto the master

**Decided (2026-07-01).** Reverses D6; refines the D3 / Step-4 "retire"
scope. The pipeline is `content/features/<slug>.md` (reviewed prose master
= single source of truth) → deterministic golden projector →
`.help/templates/...` (served). LLM polish runs at **authoring time on the
master** (reviewed, committed), NOT on the projected output — serve-time
polish would break single-source (served ≠ reviewed master) and golden
reproducibility (the −207/+149 regen churn). Concretely: **absorb** the
generator/polish machinery into `attune.authoring` (do NOT delete it),
repoint its LLM calls to **`attune.models`** (tier routing +
subscription-first auth + telemetry), and wire it into the
master-authoring flow (`author-feature` skill / a polish-master action
producing a reviewable diff). Keep `anthropic` / `claude-agent-sdk`
(workflows already carry the SDK). Splits cleanly on the thesis seam:
*authoring* = LLM polish on the master; *mechanics* = deterministic
projection. This supersedes the earlier Stop-hook-stashed "retire the LLM
regen backend" finding. **Executed by T3**, not T2a.

## D11 — T1 acceptance + T5 docs repoints executed (2026-07-21)

**Decided/executed.** The three remaining script consumers of the
external `attune_author` package are repointed to `attune.authoring`
in PR #1562 (**held draft** per the 10.6.0 merge hold; joins #1559,
#1561):

- `scripts/regenerate_help_templates.py`,
  `scripts/list_stale_help_features.py`,
  `scripts/help_aggregator_prototype.py` — the two
  staleness-consuming scripts also gain the D9 glob-less filter
  (manual features report untracked, not stale; the weekly
  freshness report now says 0 stale on the all-manual repo instead
  of 27 false positives).
- Receipts: live-fire of all three (0 stale / 27 untracked, regen
  exit 0) + 41 tests serial-pass. The freshness workflow installs
  `-e '.[author]'`, so `attune.authoring` resolves in CI.
- Deferred to T3 (D10 scope): `src/attune/memory/personal.py`
  (`attune_author.polish`) and `test_website_version_accuracy.py`
  (`attune_author.generator._ALL_TEMPLATE_NAMES`) — generator/
  polish not yet absorbed.
- Residual found: `src/attune/ops/help_regen.py` invokes the
  `attune-author` CLI by *path* (non-import consumer); retire with
  the CLI at T3/T4, not in T1.

T5 docs triage (doc-fiction buckets): only two stale API refs
existed outside specs/archive — `help-system-maintenance.md`
(`attune_author.check_staleness`, `attune-author status`) and the
`feature_nav.py` projector comment; repointed in the docs PR.
KEPT as live/accurate: every `attune-author generate` mention (the
freshness workflow's regen path still runs that CLI, and
`help/generator.py`'s deprecation text names it), the `[author]`
extra references (extra still ships), tutorial "Auto-generated by
attune-author fact-check" audit blocks (generated provenance), and
package-family/history docs.

## D12 — T4 ruled: archive without yank, executed after T3

**Decided (Patrick, 2026-07-21).** The package's fate is **archive
without yank**: archive the GitHub repo and mark the project
archived on PyPI (supported since early 2025 — signals "no further
releases" without breaking resolution). All 42 published versions
stay installable, so pinned installs and the interim `[author]`
extra never break. No shim release — the download numbers
(pypistats without-mirrors 2026-07-21: 7/day, 86/week,
1,540/month, confounded by attune-ai's own CI, `[author]`-extra
installs, and bot noise) show no evidence of a human adopter
outside the ecosystem to build one for. Yank was rejected: it
breaks pinned installs with no security motive.

**Sequencing (binding):** execution waits for T3. The `[author]`
extra still ships and the freshness workflow's regen path still
runs `attune-author generate`, so archival before the
generator/polish absorb would strand live tooling. T3 lands →
drop the `[author]` extra + retire the CLI paths (including the
D11 `help_regen.py` residual) → then archive repo + PyPI status
in one deliberate pass.

## T3 executed — polish machinery absorbed upstream (2026-07-21)

**Built** (session-f4b4f3, held draft under the 10.6.0 hold; D10 scope,
issue #1567). Absorbed from attune-author 0.25.0 into
`attune.authoring`: `generator.py`, `polish.py`, `polish_prompts.py`,
`maintenance_contract.py`, `rag_hook.py`, `faithfulness/`,
`ground_truth/`, `meta_templates/` (package-data entry added for
`*.j2`). LLM calls repointed to the new `attune.models.single_turn`
(absorbs attune-author's `auth.py` + `doc_gen/_anthropic.py`
essentials): subscription-first routing reusing
`sdk_isolation_kwargs()` + the #1534 `iter_agent_messages` teardown
guard, tier routing via `attune.model_tiers.resolve_model`, API route
via `attune.llm.fable_call.create_with_fable`, per-process auth
counters (kept out of `UsageTracker` — telemetry-models-layering OQ-2
is open). Version skew found and fixed during the absorb:
in-repo `manifest.py`/`staleness.py` predated 0.25.0's
`Feature.status` (`auto`/`manual`) + `manual_features` skip — ported.
The D10 wiring artifact is `scripts/polish_master.py` (reviewable
diff, `--apply` opt-in) + the author-feature skill's new Step 3.5;
polish of projected output stays forbidden. T3-deferred consumers
migrated: `memory/personal.py` lazy import,
`test_website_version_accuracy` `_ALL_TEMPLATE_NAMES` (importorskip
dropped). attune-author test suites absorbed (~700 tests green
serially); the syrupy golden-template file was NOT absorbed (no
syrupy dep) — guidance/problem template assertion tests +
in-repo projector goldens cover rendering. Scripts and the
aggregator test were left untouched — they are held PR #1562's
surface. **T4 is now unblocked** per D12.

## 2026-07-27 — Resolver fold-in EXECUTED (spec T2 / #1191, issue #1586)

**Built** (post-#1561 lift, per the build-slot order). New shared
`fact_check/imports.py` owns the authoritative import verdict:
`find_repo_root` + `ensure_src_on_path` (repo `src/` first on
`sys.path` — the audit script's mechanism, extracted), plus the
resolution primitives (`resolve_import_statement` moved verbatim from
`audit_doc_imports.py::_resolve`; `try_import` / `resolve_attr` /
`resolve_dotted` moved from `python_refs.py`). `python_refs.check()`
now preps the checked repo's src before resolving (kills the line-115
false-positive class for fresh processes; a `sys.path` insert cannot
rebind already-imported modules — documented limit). The audit
script's `_resolve` delegates lazily (its `main()` bootstrap stays —
it must run before any attune import). Regression test:
`tests/unit/authoring/fact_check/test_imports.py::TestLine115Regression`
— a symbol existing ONLY in the checked repo's src resolves, with a
no-repo-layout negative control. 127 fact_check + audit-gate tests
serial-green.

## D13 — Residual ruled: delete the plugin vestige, don't repoint the hook

**Decided (2026-08-09).** The 2026-08-08 triage residual —
`plugins/attune-author/hooks/help_post_commit.py` still importing
`attune_author.maintenance.run_hook` — is resolved by deleting the
whole `plugins/attune-author/` marketplace-plugin vestige, not by
repointing the hook. Evidence (all live-fired, not assumed):

- **Repoint has no target.** `run_hook` was never absorbed:
  `attune.authoring` exposes no `run_hook` (checked `hasattr` +
  `maintenance_contract.py` names). The live post-commit surface is
  `plugin/hooks/help_post_commit.py` →
  `attune.help.maintenance.run_hook` (`help/maintenance.py:152`),
  which already ships in the main attune-ai plugin — a repointed
  attune-author hook would be a duplicate that additionally breaks
  the plugin's standalone premise (its users need not have attune-ai
  installed, so `attune.help` wouldn't import).
- **The hook was a permanent silent no-op.** Live-fired with a
  `git commit` payload in the repo venv: `attune_author`
  ImportError → exit 0, no output.
- **The plugin's only function wraps the archived package.** Its
  MCP server is `uvx --from attune-author[plugin] python -m
  attune_author.mcp.server`; its skills/README instruct
  `pip install 'attune-author[plugin]'`. D12 archived that package;
  D1/D3/D10 moved authoring into the session + `attune.authoring`.
  Keeping a marketplace entry that advertises the retired product is
  claim drift.
- **Nothing in-repo executes it.** Only references were the root
  `.claude-plugin/marketplace.json` entry, this spec's docs, and an
  archived 2026-04 plan. No test enumerates the plugin dir; the
  `.agents/skills` mirror doesn't source from `plugins/`;
  `plugin/.claude-plugin/marketplace.json` never listed it.

Executed in the same PR: `plugins/attune-author/` deleted (14
files), marketplace entry removed, attune-help plugin cross-refs and
README install/migration text updated, design.md residual note
flipped to resolved. Existing installs keep their local copy;
archive-without-yank (D12) means nothing breaks for them — the entry
simply stops resolving for new installs. Website product-catalog
cleanup (features.ts entry, product cards, footer PyPI link) is
tracked as a follow-up, per the website-only-change policy.

## Open

- (none — T4 executed 2026-07-27 per D12: `[author]` extra dropped
  from pyproject.toml, CLI invocation paths retired, repo archived
  without yank. Closed at the 2026-08-08 triage. D13 closed the
  last residual 2026-08-09.)
