# Decisions: Single-Source Help + Docs

Decisions recorded during the 2026-06-21 requirements
interview. Each is the agreed answer to a fork; rationale is
captured so later phases don't relitigate it.

---

## D1 — Direction: single-source, render to both

**Decided:** Author content once; render to BOTH the in-tool
`.help` corpus and the mkdocs site.

**Why:** The two corpora serve different consumers (in-CLI
help vs published site) but document the same features.
Single-sourcing ends the duplication while keeping both
consumers. Rejected: docs-canonical-only (loses the 11-kind
in-tool structure), keep-both-raise-quality (duplication
remains), one-off merges (doesn't fix the architecture).

---

## D2 — Source format: hand-authored structured markdown

**Decided:** One "master file" per feature — YAML frontmatter
plus a fixed set of named markdown sections.

**Why:** Patrick's bar is the hand-authored feel of today's
`docs/` (which the agent authored over time, not via
attune-author). Markdown keeps authoring ergonomic and
git-diffable; the "structure" is a convention over markdown,
not a new serialization. Rejected: YAML/TOML data files
(awkward for long-form prose).

---

## D3 — attune-author repurposed as projector + validator

**Decided:** attune-author's role shifts from *LLM
content-generator* to *deterministic projector + validator*.
It renders the master file into outputs and runs
fact-check/grounding; it does not author or rewrite
canonical prose.

**Why:** LLM authoring of canon is exactly what produced the
fiction (bare-module imports, hallucinated cross-refs).
Removing the LLM from the canonical path preserves the
hand-authored feel and kills the fiction at its root. The LLM
remains an optional drafting assist (D-linked to R9).

---

## D4 — Pilot-first

**Decided:** Prove the full chain on two features before
rollout: `spec-engine` and `models`.

**Why:** ~270 files + a repurposed engine + a new projector +
a help read-path change is too large to land blind.
`spec-engine` (Python-API shape, just worked this session)
and `models` (CLI-reference/tabular shape) give contrasting
content to stress the projector. The rollout playbook (R7) is
written from what the pilot teaches.

---

## D5 — RAG-grounding is a quality mechanism, not a pilot feature

**Decided:** "RAG grounding" means master-file claims are
RAG-grounded/cited against the codebase (via
`rag_knowledge_query`) and fact-checked — so hand-authored
content stays verifiably true to the code. It is NOT a
synonym for picking the `rag-grounding` feature as a pilot.

**Why:** Patrick clarified the intent is verifiable content
quality. This becomes R3; the second pilot feature is chosen
independently for content-shape coverage (`models`).

---

## D6 — FAQ is a sourced source-of-truth, not an authored section

**Decided:** The master file's FAQ is **not** a normal canonical
section that the feature owns and emits verbatim. The FAQ is a
**dynamic source of truth** fed by four channels — unmatched user
queries, telemetry error-frequency, GitHub issues, and
author-curated seeds — that the **FAQ Generator** merges,
deduplicates, and ranks by frequency before projecting to both the
in-tool `.help/faq` output and the global mkdocs FAQ page. In the
master file, the feature contributes **only its author-curated
seeds (channel 4)**, in a `## FAQ seeds` section explicitly marked
as input to the Generator — never a rendered FAQ.

**Why:** The earlier documentation-stack spec
(`.claude/plans/documentation-stack-spec.md`, decision **D3** —
"FAQ sourcing (four channels)", mirrored in
`plugin/help/generated/notes/decision-d3-faq-sourcing-four-channels.md`)
established the FAQ as a multi-channel, deduplicated,
frequency-ranked source of truth produced by a dedicated FAQ
Generator transformer. The first cut of this spec's master-file
schema (design.md) listed `## FAQ` as an ordinary section and the
T1 draft pasted the LLM-generated `.help/spec-engine/faq.md` into
it verbatim. That silently overrode D3 and produced three
regressions: (1) a **third copy** of FAQ content
(`docs/reference/FAQ.md` + `.help/<feature>/faq.md` + master file),
which is the duplication single-sourcing exists to end; (2) it
**discards three of the four channels** — a frozen authored block
can only ever be channel 4, so telemetry frequency, unmatched
queries, and issues have nothing to feed; (3) it **inverts the data
flow** — the Generator is a transformer that *pulls* from patterns
and projects outward, not something a feature file *emits*.

**Consequences:**

- The master-file schema's `## FAQ` section is renamed `## FAQ
  seeds` (author-curated channel-4 input only). design.md's schema
  and projection map are amended accordingly.
- The FAQ Generator remains the single producer of the `.help/faq`
  output and the global FAQ page; the projector does not render the
  master file's seeds as a finished FAQ.
- **Open — Failure modes may have the same shape.** doc-stack D3 /
  the architecture diagram route telemetry error-frequency into
  error *and* FAQ templates, so the master file's `## Failure modes`
  section may be the same "static copy vs dynamic source" problem.
  Flagged for a dedicated review before rollout (R7) — see the
  `failure-modes-sourcing-review` follow-up.

**Rejected:** FAQ-as-authored-section wins and the four-channel
Generator is retired — rejected because it throws away the
telemetry/issue/unmatched-query signal that makes the FAQ track
real user pain, and re-introduces the duplication the spec exists
to remove.

---

## D7 — FAQ projection is out of pilot scope

**Decided:** The pilot's projector renders the other 10 canonical
sections to the 10 non-faq `.help` kinds plus the 4 `docs/` pages.
It does **not** produce `.help/<feature>/faq.md` or the global FAQ
page. Those stay on their current path for the pilot; the
master file's `## FAQ seeds` is authored and committed but not yet
consumed. Building the four-channel **FAQ Generator** (D6) is a
separate post-pilot workstream.

**Why:** Verified 2026-06-21 that the FAQ Generator **does not
exist** — there is no implementation in attune-ai or attune-author,
and `.help/<feature>/faq.md` is produced today by attune-author's
LLM `generator.py` like every other kind. D6 reconciled the
*design* (FAQ is sourced, not authored) but the *system* to realize
it is unbuilt. The pilot's job (R6) is to prove the
master-file → projector → `.help` + `docs` chain end-to-end;
bolting on a brand-new multi-channel Generator (telemetry ingestion,
dedup, frequency ranking) would balloon pilot scope and couple the
projection proof to an unrelated subsystem. Authoring the seeds now
(D6) means the input is ready when the Generator is built; deferring
the Generator keeps the pilot focused.

**Consequences:**

- Projector pilot scope = 10 sections → {concept, reference, task,
  quickstart, comparison, error, troubleshooting, warning, note,
  tip} + {how-to, tutorial, architecture, reference} docs pages.
  `faq` is explicitly excluded.
- Pilot acceptance (R6) is read as "all non-faq targets render and
  the help system serves them"; faq is out of the acceptance set.
- New post-pilot workstream: **build the FAQ Generator** (four
  channels, dedup, frequency rank) that consumes the `## FAQ seeds`
  section. Tracked alongside FM1 in
  [follow-ups.md](follow-ups.md).
- DD5 (regen-overwrite defuse) still applies to the 10 projected
  kinds; `faq.md` continues to come from the LLM generator until the
  Generator replaces that path, so spec-engine's `faq` entry is **not**
  removed from the generator manifest during the pilot (only the 10
  projected kinds are).

---

## D8 — Projector lives in attune-author; both libraries kept; infra consolidation is separate

**Decided (confirms DD1):** The deterministic projector is a new
module in **attune-author**, not attune-help. Both libraries are
kept — attune-author is the build-time *produce* side, attune-help
the lightweight serve-time *runtime*. The duplicated
`manifest.py`/`staleness.py`/`freshness/` across the two libs is
real consolidation debt but is handled as a **separate cleanup**,
not inside the projector PR.

**Why attune-author, not attune-help (the option considered and
rejected):**

- The projector's dependencies already live in attune-author —
  `_extract_source_info` (AST), the `fact_check` package
  (`python_refs`, `cli_refs`, `md_links`), and `import_repair`.
  Putting the projector in attune-help would force either
  duplicating those or making attune-help depend on attune-author,
  re-coupling the two libraries that `attune-author 0.15.0`
  deliberately decoupled.
- The projector is **build-time**; attune-help is the **serve-time**
  runtime kept deliberately lightweight (`pip install attune-help`).
  An AST + fact-check projector there bloats the thing whose value
  is being minimal.
- attune-help's apparent overlap ("it already owns templates") was
  verified false: its `transformers.py`
  (`render_json`/`render_claude_code`/`render_marketplace`/
  `render_cli`) is **serve-time render of a populated template**, not
  build-time projection. No reuse to capture by moving in.

**Library roles, recorded so this doesn't get relitigated:**

- **attune-author** — produce: generator (LLM, now optional-assist
  per D3), **projector** (new, deterministic), `fact_check`,
  `import_repair`, manifest, staleness.
- **attune-help** — serve runtime: `HelpEngine`, progressive depth,
  serve-time transformers, mcp adapters. Reads `.help/templates/`
  unchanged (DD2/R4).
- **`attune.help`** (attune-ai internal facade) — re-exports
  `.generator`←attune_author, `.engine`←attune_help; what the live
  MCP server calls. Its hidden cross-dep is a known footgun, tracked
  separately.

**Build-shape consequence (verified during T2 scoping):** the
`meta_templates/*.j2` are AST-keyed jinja scaffolds feeding an LLM
polish phase — **not** reusable for projecting hand-authored prose.
The projector therefore does not reuse them: it parses the master
file's named sections and routes them to outputs, wrapping with the
generator's existing frontmatter/footer helpers. Simpler than the
generator (no AST-render, no LLM). The Reference section is
hand-authored in the master file; fact-check *verifies* it rather
than AST-deriving it (aligns with D3).

---

## D9 — DD5 defuse = remove the whole feature from the manifest (faq frozen)

**Decided (pilot execution, 2026-06-21):** To stop the weekly
help-freshness regen from overwriting the projected hand-authored
`.help` content, **remove the migrated feature entirely from
`.help/features.yaml`** (the LLM-generator manifest). The retained
`faq.md` stays on disk and is served as-is, but is **frozen** — no
longer auto-regenerated — until the four-channel FAQ Generator (D6/D7)
replaces that path.

**Why this supersedes D7's literal mechanism:** D7 said "only the 10
projected kinds are removed from the manifest; spec-engine's `faq`
entry is **not** removed, so faq keeps coming from the LLM generator."
Pilot execution proved that mechanism **is not expressible** with
attune-author 0.19.0:

- `.help/features.yaml` has **no per-`.help`-kind field**. Each
  feature is `description` + `files` + `tags` (+ optional doc-side
  `doc_kinds`/`doc_paths`/`arch_path`). There is no `help_kinds` /
  `skip_kinds` / `source: projected` to "remove 10 kinds, keep faq."
- The weekly regen (`​.github/workflows/help-freshness.yml`) runs
  `attune-author generate <feat> --help-dir .help --project-root .
  --all-kinds` per **stale feature** — **all-or-nothing per feature**.
  You cannot regenerate only `faq` while skipping the other 10; the
  same command produces all of them.

So the only two mechanisms that exist today are: **(A)** remove the
feature from the manifest (chosen), or **(B)** mark the 10 projected
files `maintenance: manual` so `generate --all-kinds` (no
`--overwrite`) skips them while `faq` (still `status: generated`)
regenerates. (B) honors D7's letter but has two real warts: the
feature reports **perpetually stale** (its projected `source_hash` is
the master-file hash, which never matches the code-derived hash
`check_staleness` expects), so the dashboard shows it stale forever
**and** the weekly job LLM-regenerates `faq` every week regardless of
whether anything changed — i.e. it keeps churning the very
LLM-authored FAQ the spec exists to retire (D6 calls LLM-authored FAQ
a regression). (A) avoids both warts and ends the churn; its only cost
is that `faq.md` is frozen, which is acceptable because the FAQ
Generator is its eventual owner and the file is still served.

**Patrick chose (A)** during pilot execution (2026-06-21).

**Consequences:**

- Migrating a feature to the projector = **remove its entire entry
  from `.help/features.yaml`** (not a per-kind edit). The projector
  (`scripts/project_features.py`) becomes the sole owner of that
  feature's `.help/templates/<feature>/*.md`.
- The feature's `faq.md` is retained on disk, served unchanged, and
  frozen until the FAQ Generator (FG1) ships. Do **not** delete it.
- **Recommended attune-author follow-up:** add a first-class
  `maintenance: projected` contract that (1) the generator skips like
  `manual` and (2) `check_staleness` **ignores** (so projected
  features don't report perpetually stale). That would let a future
  design keep `faq` on the LLM path per D7's original intent *without*
  the perpetual-stale wart — reopening (B) as the cleaner long-term
  mechanism. Tracked for R7 / rollout.

---

## D10 — Tutorial stays hand-authored; dropped from projection

**Decided (pilot execution, 2026-06-21):** The `tutorial` docs kind is
**not projected**. Tutorials remain hand-authored per feature. The
pilot driver (`scripts/project_features.py`) skips it via
`skip_kinds=("faq", "tutorial")`.

**Why (decided by inspecting the rendered page, per the T2 medium
risk):** design.md flagged that a guided tutorial may resist pure
projection, with the pilot slice `DOCS_PAGE_SECTIONS["tutorial"] =
["Tasks"]` to be judged on the rendered output. It was judged thin:

- The **projected** tutorial is the master file's `## Tasks` section
  verbatim — 4 independent task recipes (run / resume / approval /
  re-run-subset). It is a how-to list, and it **duplicates** the
  how-to page (which also consumes `Tasks`).
- The **hand-authored** tutorial is a true tutorial arc the Tasks
  section cannot reconstruct: a "What you will build" frame,
  Prerequisites, Step 1→6 progressively assembling **one**
  `run_pipeline.py` with narrative connective tissue and a per-step
  Verify, a "Complete script", and "What you learned" / "Next steps".

A tutorial is a *narrative over* the tasks, not a *slice of* them.
Projecting it loses the pedagogy and produces a how-to duplicate.

**Consequences:**

- `tutorial` is dropped from the pilot's projection set; the driver's
  `skip_kinds` is the working mechanism. `docs/tutorials/<feature>.md`
  stays hand-authored and is restored from the pre-projection version.
- **Recommended attune-author follow-up:** remove `"tutorial"` from
  `DOCS_PAGE_SECTIONS` in `attune_author.projector` so the *default*
  projection excludes it (rather than relying on every consumer's
  driver to pass `skip_kinds`). Until then the driver `skip_kinds` is
  the guard. Tracked for R7 / rollout.
- The projected docs set per feature is therefore **how-to,
  architecture, reference** (3 pages); `.help` is the 10 non-faq
  kinds. Tutorial + faq remain hand-authored / LLM-owned respectively.

---

## D11 — Per-feature hub page; tutorial-first by prominence, not by rule (P6)

**Decided (2026-06-21 design session):** Every feature gets a thin,
**projector-emitted hub page** at `docs/features/<feature>.md`. The hub
**leads with a prominent "Start here" callout** that points to the
**Tutorial** when one exists, then a scannable **card grid** of the
feature's other available kinds (how-to, reference, architecture,
concept). When no tutorial exists, the callout **degrades** to lead
with the how-to (or, absent that, concept) — never a dead link. Layout
**Variant 1 (hero callout + card grid)** is the locked convention.

**Why this shape (the coverage constraint drove it):** Patrick wants
the rich hand-authored tutorial front-and-center, but it is the **one
channel the projector cannot generate** (D10) and only ~9–11 of 25
manifest features — and a small minority of the ~270 rollout — will ever
have one (`models`, a pilot feature, does not). A literal
"tutorial-is-the-front-door" rule gives most features a dead entry and
taxes the frequent quick-answer lookup to serve the first-visit case
(Diátaxis treats the tutorial as a deliberate detour, not the hub).
Variant 1 resolves the tension **spatially**: the hero gives the
tutorial genuine prominence for first-visit readers, while the card
grid below serves the lookup reader in one scan. The hero is the only
part that varies by coverage; the grid is identical whether or not a
tutorial exists.

**Why a hub page rather than a banner on the how-to:** (1) it is the
**single nav entry per feature** (the unit P4 wires in, instead of 3–4
type-scattered lines × 270 features); (2) it is the **discovery
surface** the projected pages lack today — verified that
`docs/how-to/spec-engine.md` carries **zero cross-links** to the
tutorial, reference, or architecture pages, so without a hub there is
no path between a feature's pages; (3) the projector **knows each
feature's available kinds**, so it emits the hub and its card set
deterministically — no LLM, fully D10-compatible (the hub *links* the
tutorial, never reproduces it).

**Rejected:**

- **Variant 2 (numbered learning path)** — over-narrates a Diátaxis
  journey at the frequent quick-lookup user, the exact tax P6 warns
  against.
- **Variant 3 (minimal callout + bullet list)** — gives the tutorial
  the least visual weight, working against the front-and-center goal.
- **No hub; "Start here" admonition banner injected atop each how-to
  page** — leaves the nav problem unsolved (still 3–4 type-scattered
  entries per feature) and gives no home to features whose strongest
  page is reference, not how-to.

**Consequences:**

- The projector/driver gains a hub-emit step: given a feature's
  available kinds (and whether `docs/tutorials/<feature>.md` exists), it
  writes `docs/features/<feature>.md` in the Variant-1 shape. The
  card set renders only kinds that exist. Lands in attune-author
  (projector) + the repo driver; tracked under P6 in follow-ups.
- The hub's "Start here" target precedence is **tutorial → how-to →
  concept** (first that exists).
- In-tool surfaces (ops living-docs dashboard, `help_lookup`) are
  **out of scope here** — this decision is the published-site hub. Open
  P6 question of whether the in-tool surface should also lead with the
  tutorial is deferred (carried on the P6 follow-up).
- Pairs with **D12** (P4): the hub is the per-feature nav entry.

---

## D12 — mkdocs nav: one "Features" hub entry per feature (P4)

**Decided (2026-06-21 design session):** Projected pages enter the
published site through **one new top-level "Features" nav section**
(a feature-first axis) that sits alongside the existing type-first
Diátaxis sections (Getting Started / Tutorials / How-to / Reference).
**Each feature contributes exactly one nav line → its hub page**
(`docs/features/<feature>.md`, D11). The per-feature
how-to/architecture/reference pages stay **built but out of the top
nav**, reached via the hub and search. A **mkdocs `hooks:` Python hook**
(`on_config`) generates the Features section and adjusts `exclude_docs`
by scanning `docs/features/*.md` at build time. The wholesale
`architecture/` exclusion is **dropped**; only the genuine non-feature
orphans (e.g. `architecture/extending-composition-patterns.md`) are
excluded explicitly.

**Why a single hub entry per feature (not per-page nav entries):** the
existing nav is **type-first** — `Tutorials`, `How-to`, `Reference` are
flat lists, and features are scattered across them. Wiring ~270
features × 3–4 pages into those flat lists is ~1000 hand-maintained
nav lines that drift the moment a page is added (the
website-content-accuracy failure mode). Routing each feature through
**one hub line** keeps the nav legible and makes the hub — not a raw
page — the front door. The pilot's per-feature
`!architecture/<feature>.md` re-includes are the concrete thing that
**does not scale**; the hook replaces them.

**Why a Python hook, not a nav plugin (the mechanism fork P4 named):**

- The repo runs **only `search` + `mkdocstrings`** and keeps `nav:`
  explicit in `mkdocs.yml`. A `hooks:` entry is a **zero-dependency**
  ~30-line function (`on_config`: read `docs/features/`, append a
  `{"Features": [...]}` nav node, prune feature pages from
  `exclude_docs`). The projector/driver never edits `mkdocs.yml`.
- A nav plugin (`mkdocs-awesome-nav` / `literate-nav` + a generated
  `.nav.yml`) is conceptually cleaner but adds a **build dependency**
  and a per-directory file convention — a heavier commitment for a repo
  that deliberately keeps nav in one explicit place. Recommended as the
  fallback if the hook outgrows ~30 lines, not the default.

**Rejected:**

- **Hand-listed per-feature nav entries** — 270× manual, drifts
  immediately; the exact maintenance trap single-sourcing exists to
  end.
- **Keep the wholesale `architecture/` exclude + per-feature `!`
  re-includes** — the pilot's stopgap; one extra line per feature in
  `mkdocs.yml`, does not scale.

**Consequences:**

- New build artifact: `docs/hooks/feature_nav.py` (or equivalent),
  referenced from `mkdocs.yml`'s `hooks:`. It owns the "Features" nav
  node and the feature-page `exclude_docs` handling.
- `docs/features/<feature>.md` (D11 hub) becomes the routed page;
  `docs/features/index.md` is the section landing (migrate the current
  single-file `docs/FEATURES.md` content there). The blanket
  `features/` exclusion is replaced by the hook's selective handling.
- The "not in nav" mkdocs INFO for per-feature how-to/architecture/
  reference pages is **accepted by design** — they are intentionally
  reached through the hub, not the top nav. (This is already the
  systemic status quo for every feature page, so it is not a
  regression.)
- Decided **once at rollout**, applied uniformly by the hook — never
  per-feature. Unblocks the R7 rollout playbook's nav step.

---

## D13 — Failure modes are fully author-owned; project verbatim (FM1)

**Decided (2026-06-21, grounded in the doc-stack spec — not assumed):**
The master file's `## Failure modes` section is **canonical,
author-owned content**, not a sourced/dynamic source-of-truth like the
FAQ (D6). It projects **verbatim** to the `error`, `troubleshooting`,
and `warning` `.help` kinds per the existing design.md projection map.
**No re-cut to seeds, no Error Generator, no design.md amendment.** FM1
is **closed as option (a)**.

**Why (the evidence that settles it):** FM1 suspected failure modes had
the FAQ's "static copy vs telemetry-sourced" problem because the
documentation-stack spec
(`.claude/plans/documentation-stack-spec.md`) routes telemetry
error-frequency near error templates. Reading that spec's **own
source-mapping table** refutes the suspicion:

| Source | Produces | Template type |
| ------ | -------- | ------------- |
| Lessons Learned in CLAUDE.md | Error/Warning pages | Error, Warning |
| Error frequency from telemetry | FAQ candidates | FAQ |

Telemetry error-frequency feeds **FAQ candidates only** — it does **not**
author error/warning templates. Those are sourced from **Lessons
Learned (authored knowledge)**, and the spec's "Source of truth"
section states plainly: *"Error templates are authored in a canonical
format (source)."* So failure-mode prose (symptom / cause / fix) is
author-knowledge by the doc-stack spec's own design; telemetry's only
coupling to it is **prioritization** (which modes matter), expressed
through the separate FAQ channel — a far weaker coupling than the FAQ's,
where the *question phrasing itself* tracks how real users ask.

**Contrast with D6 (why the FAQ was different):** the FAQ regressed
because a frozen authored block can only ever be channel 4, starving
the three dynamic channels and inverting the pull-based Generator flow.
Failure modes have **no equivalent dynamic authoring channel** in the
doc-stack design — telemetry informs *selection*, not *content* — so
none of D6's three regressions (duplication, discarded channel,
inverted flow) apply.

**Rejected — (b) partly sourced (author seeds + Error Generator merge):**
would manufacture a coupling the doc-stack spec does not specify, add an
unbuilt subsystem (cf. the FAQ Generator, FG1), and re-cut
hand-authored failure-mode prose into seeds for no sourcing benefit.

**Consequences:**

- `content/features/spec-engine.md`'s `## Failure modes` section is
  **unchanged**; design.md's projection map (`Failure modes → error,
  troubleshooting, warning`) is **confirmed correct as written**.
- FM1 is closed; the R7 rollout playbook is unblocked on this axis.
- **Note:** follow-ups.md FM1 instructed recording this as "decision
  D7" — that label was already taken (FAQ projection scope) when FM1
  was written; recorded here as **D13**.
