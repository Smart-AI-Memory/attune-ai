# Follow-ups: Single-Source Help + Docs

Tracked items deferred out of the T1 pilot. Each is a real piece of
work with enough context to act on cold.

---

## FG1 — Build the FAQ Generator (post-pilot)

**Status:** Phase 1 SHIPPED 2026-07-14 (channel-4 seeds projection);
remainder re-scoped to the dynamic channels + global FAQ page ·
**Raised:** 2026-06-21 (D6/D7) · **Blocks:** FAQ single-sourcing
(not the pilot)

**Phase 1 (shipped 2026-07-14):** the deterministic projector now
renders the `faq` kind from each master's `## FAQ seeds` section
(channel 4 only, no LLM) — `_render_faq` in
`src/attune/authoring/projector.py` parses both seed bullet shapes,
drops the disclaimer blockquote, and emits an H2-per-question page
with the standard 7-key generated frontmatter, ending the
frozen-file drift for all 27 FAQs. The 3 curated FAQs (memory,
code-quality, elicitation-forms) were folded into their masters'
seeds first (no Q lost; code-quality's drifted answers corrected
against the master); the other 24 features' stale LLM-generated
FAQs were replaced by their seeds projections (Patrick-approved —
old Q/As remain in git history; the dynamic channels resurface
genuinely-asked questions when signal exists).

**Remaining scope:** the dynamic channels — unmatched user queries
(Phase 2: log unmatched `help_lookup` queries locally, cheap, do
soon), telemetry error-frequency, GitHub issues — merged,
deduplicated, and frequency-ranked into the seeds-projected FAQ,
plus the global mkdocs FAQ page. Deferred until real user signal
exists (telemetry ~0 as of 2026-07-14).

**Why the remainder is deferred:** the ranker/merger is a distinct
subsystem (telemetry ingestion, dedup, ranking) with no input data
today.

**Where to look:** doc-stack spec
(`.claude/plans/documentation-stack-spec.md`) D3 (~line 659), the
architecture diagram's "FAQ Generator" transformer (~line 590), the
"Error frequency from telemetry | FAQ candidates" mapping (~line
459); this spec's decisions.md D6 + D7;
`plugin/help/generated/notes/decision-d3-faq-sourcing-four-channels.md`.

**Done when:** the Generator produces `.help/faq` + the global FAQ
page from seeds + dynamic channels, and spec-engine's `faq` entry is
removed from the LLM generator manifest (completing DD5 for the
faq kind).

---

## FM1 — Failure-modes sourcing review (before rollout)

**Status:** CLOSED — decided (a) fully author-owned · **Decision:** D13
(decisions.md) · **Resolved:** 2026-06-21 · **Was blocking:** R7

**Resolution:** Grounded in the doc-stack spec's own source-mapping
table — `Lessons Learned → Error/Warning` (authored),
`telemetry error-frequency → FAQ candidates` only — failure modes are
**fully author-owned** and project verbatim to error/troubleshooting/
warning. No re-cut, no Error Generator, no design.md change. None of
D6's three FAQ regressions apply (telemetry informs *selection* of
modes, not *content*). See **D13** for the full rationale. The original
content below is retained as the investigation record.

---

**The question:** Is the master file's `## Failure modes` section the
same "static copy vs dynamic source-of-truth" problem we just fixed
for the FAQ (decisions.md D6)?

**Why it's suspect:** The earlier documentation-stack spec
(`.claude/plans/documentation-stack-spec.md`) routes **telemetry
error-frequency** into *both* error templates *and* FAQ candidates
(see its decision D3 and the architecture diagram's "FAQ Generator
<- Dynamic FAQ from patterns", plus the line "Error frequency from
telemetry | FAQ candidates"). If error/troubleshooting/warning
content is meant to be partly sourced from live telemetry —
"errors that appear frequently get promoted" — then the master
file's hand-authored `## Failure modes` section has the same three
regressions D6 names for the FAQ:

1. duplication (a frozen copy alongside the telemetry-sourced one),
2. discards the dynamic channel (telemetry frequency can't feed a
   static block),
3. inverts the data flow (the feature emits what should be pulled).

**What to decide:** One of —

- **(a) Failure modes is fully author-owned** (canonical, static):
  telemetry error-frequency informs *which* failure modes the author
  documents, but the rendered content is authored, not generated.
  No regression; close the item.
- **(b) Failure modes is partly sourced** (like the FAQ): the master
  file contributes author-curated seed failure-modes (channel 4),
  and an Error Generator merges them with telemetry-frequency signal,
  dedupes, and ranks. Then re-cut `## Failure modes` to seeds and
  amend design.md's projection map (mirror the D6 treatment).

**Recommended starting hypothesis:** lean toward (a). Failure-mode
*prose* (symptom / cause / fix) is genuinely author-knowledge, unlike
FAQ phrasing which tracks how real users ask. Telemetry's role is
likely *prioritization* (which failure modes matter most), not
*authoring* — which is a weaker coupling than the FAQ's. But verify
against the doc-stack spec's actual intent before committing; do not
assume.

**Where to look:**

- `.claude/plans/documentation-stack-spec.md` — Feature 1 (error
  templates, "Source of truth" section ~line 241), the architecture
  diagram (~line 575), D3 (~line 659), and the "Error frequency from
  telemetry | FAQ candidates" mapping (~line 459).
- `plugin/help/generated/notes/decision-d3-faq-sourcing-four-channels.md`
- This spec: `decisions.md` D6, `design.md` projection map + FAQ
  exception note.
- The current `## Failure modes` section in
  `content/features/spec-engine.md` (the thing under review).

**Done when:** a decision (D7) is recorded choosing (a) or (b); if
(b), `content/features/spec-engine.md`'s `## Failure modes` section is
re-cut to seeds and design.md amended to match.

---

## Starter prompt for a fresh session (FM1)

> Paste this into a new Claude Code session rooted in the attune-ai
> worktree to pick up FM1 cold.

```text
Resume the help-docs-single-source spec: do the Failure-modes
sourcing review (follow-up FM1 in
docs/specs/help-docs-single-source/follow-ups.md).

Context: In T1 we found the master file's FAQ section was a static
copy that regressed the FAQ-as-source-of-truth design (four-channel
FAQ Generator). We fixed it (decisions.md D6) by re-cutting FAQ to
author-curated channel-4 seeds. FM1 asks whether `## Failure modes`
has the same problem, because the doc-stack spec
(.claude/plans/documentation-stack-spec.md, D3 + architecture
diagram) routes telemetry error-frequency into error/FAQ templates.

Task:
1. Read follow-ups.md FM1, decisions.md D6, and design.md (FAQ
   exception note + projection map) in
   docs/specs/help-docs-single-source/.
2. Read the doc-stack spec's error-template / source-of-truth design
   (Feature 1, ~line 241; architecture ~line 575; D3 ~line 659; the
   "Error frequency from telemetry | FAQ candidates" mapping
   ~line 459). Establish the ACTUAL intended coupling between
   telemetry error-frequency and authored failure-mode content — do
   not assume; ground it in the spec text.
3. Decide (a) Failure modes is fully author-owned (telemetry only
   prioritizes which modes to document) OR (b) it is partly sourced
   like the FAQ (author seeds + Error Generator merge/dedupe/rank).
   Recommended starting hypothesis is (a) — failure-mode prose is
   author-knowledge, telemetry's role is likely prioritization not
   authoring — but verify.
4. Record the outcome as decision D7 in decisions.md. If (b), re-cut
   the `## Failure modes` section in content/features/spec-engine.md
   to seeds (mirror the D6 FAQ treatment) and amend design.md's
   projection map + add a Failure-modes exception note.

Done when: D7 recorded; if (b), spec-engine.md and design.md amended
to match. This unblocks the R7 rollout playbook.
```

---

## P1 — Projector `_wrap_help` should emit an H1 title (attune-author)

**Status:** open · **Raised:** 2026-06-21 (pilot execution) ·
**Lands in:** attune-author

`attune_author.projector._wrap_help` writes the `.help` frontmatter +
body but **no `# H1`**, so projected bodies open at `## `. The ops
living-docs dashboard derives a template-card title from the first
`# H1` (`attune.ops.help_data._title_from_content`); with no H1 it
falls back to `"<feature> / <kind>"` (e.g. `"spec-engine / concept"`)
instead of a clean title. The OLD LLM-generated files carried
`# <Feature>`, so this is a visible regression on **every** projected
kind. `_wrap_docs` already emits `# {title}` — mirror it in
`_wrap_help` (derive from `frontmatter.summary` or the feature name).
Low-risk one-liner; needs an attune-author release + pin bump.

---

## P2 — Drop `tutorial` from `DOCS_PAGE_SECTIONS` (attune-author)

**Status:** open · **Raised:** 2026-06-21 (D10) · **Lands in:**
attune-author

Decision D10 keeps tutorials hand-authored — a guided "what you'll
build" arc resists pure section projection (the projected version is
the `Tasks` list verbatim and duplicates the how-to). The pilot guards
this in the **driver** (`skip_kinds=("faq", "tutorial")`), but the
canonical fix is to remove `"tutorial"` from `DOCS_PAGE_SECTIONS` in
`attune_author.projector` so the default projection excludes it and no
consumer has to remember the skip. Until then, every driver must pass
the skip list.

---

## P3 — First-class `maintenance: projected` contract (attune-author)

**Status:** partially done (feature-level `status: manual` landed,
2026-06-21) · **Raised:** 2026-06-21 (D9) · **Lands in:** attune-ai
(`attune.help`) + attune-author

D9 defused the regen-overwrite trap by **removing** a migrated feature
from `.help/features.yaml` entirely — but that also dropped the
feature's name/description/tags from the manifest, so `resolve_topic`
could no longer route to it and the `models`/`spec-engine` golden
queries (`md-001`, `md-002`, `sp-001`, `sp-002`) regressed to
`None`/wrong-feature. Removing the entry threw out the resolution index
along with the regen trigger.

**Landed (this PR):** a feature-level `status: manual` flag on the
manifest `Feature`. `resolve_topic` still indexes the entry
(name/description/tags), so topic resolution is restored, while
`check_staleness` **skips** manual features entirely — sidestepping the
perpetual-stale wart (no code-derived hash is ever compared, so a
projected `source_hash` can't read as stale) and `maintenance`
reports them under `skipped_manual`. The `models`/`spec-engine` entries
are re-added with `status: manual` and **no `files:`**.

**Still open:** the finer-grained *per-kind* `maintenance: projected`
page contract that would let a projected feature keep just its `faq`
on the LLM path per D7's original intent (feature-level `manual` freezes
the whole feature, including `faq`, which is acceptable today only
because `faq` is frozen until the FAQ Generator ships). With that,
DD5 could mark the 10 projected kinds `projected` while leaving `faq`
generated — the option D9 rejected for tooling reasons.

---

## P4 — mkdocs nav-wiring convention for projected pages

**Status:** IMPLEMENTED — hook wired, build verified · **Decision:** D12
(decisions.md) · **Decided:** 2026-06-21 · **Implemented:** 2026-06-21
via the help-docs-rollout-gate spec (T3) · **Landed in:** attune-ai
(`docs/hooks/feature_nav.py` + `mkdocs.yml` `hooks:` entry)

**Implementation note (what actually shipped):** `docs/hooks/feature_nav.py`
is an `on_config` hook scoped to **nav injection only** — it builds the
top-level `Features` section (Overview → `features/index.md`, then one
entry per `docs/features/*.md` hub, H1-derived labels, sorted) and
idempotently replaces any prior `Features` node. The `exclude_docs`
cleanup is a **static `mkdocs.yml` edit**, not a runtime PathSpec
mutation (keeps the hook side-effect-free beyond `config["nav"]`): the
blanket `architecture/` + `features/` excludes and the per-feature
`!architecture/{spec-engine,models,ops-dashboard}.md` re-includes are
removed, so a newly-projected feature's hub/architecture pages build with
**no per-feature `mkdocs.yml` edit**. Genuine non-feature
architecture-concept orphans and legacy pre-pilot feature pages are
excluded explicitly (a one-time enumeration that shrinks as features
migrate). `mkdocs build --strict` is clean and the Features section lists
both pilot hubs. `docs/FEATURES.md` migrated to `docs/features/index.md`.

**Convention (D12):** projected pages enter via **one new "Features"
nav section** alongside the type-first Diátaxis sections; each feature
contributes **one nav line → its hub page** (`docs/features/<feature>.md`,
D11). Per-feature how-to/architecture/reference stay built-but-out-of-nav
(reached via hub + search). A **mkdocs `on_config` hook** generates the
Features section and prunes feature pages from `exclude_docs` by scanning
`docs/features/*.md` — **zero new plugin dependency**. The wholesale
`architecture/` exclude is **dropped** (exclude only genuine non-feature
orphans); the pilot's per-feature `!architecture/<feature>.md`
re-includes are removed. Plugin route (`awesome-nav`/`literate-nav` +
`.nav.yml`) is the fallback only if the hook outgrows ~30 lines.

**Implementation TODO (R7):** write `docs/hooks/feature_nav.py`
(`on_config`: append `{"Features": [...]}` nav node from
`docs/features/`, drop feature pages from `exclude_docs`); migrate
`docs/FEATURES.md` → `docs/features/index.md` (section landing); remove
the `architecture/` blanket exclude + the `!spec-engine`/`!models`
re-includes from `mkdocs.yml`.

**Original framing (retained):**

Projected docs pages are not auto-wired into the published site:

- `docs/architecture/<feature>.md` is **excluded from the build** by
  the wholesale `architecture/` rule in `mkdocs.yml`'s `exclude_docs`.
  The pilot re-includes per-feature (`!architecture/spec-engine.md`,
  `!architecture/models.md`) — does not scale to ~270 features.
- `docs/how-to/<feature>.md`, `docs/tutorials/<feature>.md`,
  `docs/reference/<feature>.md` **build but are "not in nav"** (an
  mkdocs INFO) — the same is true for every existing feature, so this
  is systemic, not pilot-specific.

R7 must define the convention: either (a) drop the wholesale
`architecture/` exclusion and exclude only the genuine orphans, plus a
nav section that lists projected per-feature pages; or (b) a generated
nav fragment the projector/driver emits. Decide during rollout, not
per-feature.

---

## P5 — Code examples need EXECUTION-based verification

**Status:** check landed (2026-06-21, attune-author 0.20.0); R7 process
rule still open · **Raised:** 2026-06-21 (pilot review) · **Lands
in:** attune-author fact_check + R7 process

The pilot review proved that neither the static fact-checker nor
adversarial LLM review reliably catches **runtime/async correctness**
in code examples. `fact_check` (`python_refs`/`cli_refs`) verifies that
symbols exist and imports resolve — it does NOT run the code. Two
independent adversarial LLM reviewers, given the source and told to
refute, ALSO missed that `PipelineOrchestrator.run_all` is `async`
while `spec-engine.md`'s Quickstart + three Task examples called it
synchronously (no `await`, sync callbacks, not in an event loop) and
the Comparison table labeled the pipeline layer "Synchronous call."
The bug was systematic across the file; it was caught only by a human
reading `async def run_all` and tracing the call sites.

A working prototype already exists in attune-ai:
**`scripts/check_doc_examples.py`** — it extracts fenced `python`
blocks, compiles each (catching `await`-outside-async and syntax
errors), and flags any coroutine function called without `await`,
grounding "is this async?" in the real code via
`inspect.iscoroutinefunction` over the attune packages. Verified
against the pilot: 0 problems on the fixed masters + projected
outputs, and it flags a deliberately sync `run_all()` (negative
control). It would have caught the original `run_all` bug.

Concrete follow-ups:

- **Promote `scripts/check_doc_examples.py` into `attune_author.fact_check`**
  as a first-class check (`check_doc_examples`) so it runs in the same
  warn/gate pass as `python_refs`/`cli_refs`, for every consumer — not
  just this repo's driver. The prototype is the spec.
  **DONE (attune-author 0.20.0):** landed as `fact_check.check_doc_examples`,
  wired into `check_polished_file`. The promoted version derives
  async-ness generically from each block's own imports (no hardcoded
  package list) to stay consumer-agnostic; the repo driver keeps the
  prototype (`scripts/check_doc_examples.py`) as an attune-specific
  second layer that also catches async misuse when an example omits the
  import.
- **R7 process rule:** the per-feature checklist's adversarial review
  step must explicitly verify, for every public callable used in an
  example, whether it is `async` (grep `async def`) and whether the
  example awaits it correctly. Treat "is this example runnable as
  written?" as a distinct check from "do these symbols exist?".

---

## P6 — Tutorial-as-landing / per-feature hub page

**Status:** IMPLEMENTED (published-site hub) — in-tool surface still open ·
**Decision:** D11 (decisions.md) · **Decided:** 2026-06-21 ·
**Implemented:** 2026-06-21 via the help-docs-rollout-gate spec (T1
attune-author 0.21.0 hub-emit; T2 pilot projection; T3 nav) · **Landed
in:** attune-author `projector._render_hub` + repo driver
`scripts/project_features.py`

**Implementation note (what actually shipped):** `project_feature` now
emits a 14th output — the Variant-1 hub at `docs/features/<feature>.md`:
a `!!! tip "Start here"` hero linking the first present of
**tutorial → how-to → reference** (concept is `.help`-only, so the
on-site precedence ends at reference, not concept), plus a Material
`grid cards` block over the remaining present {how-to, reference,
architecture}; the hero kind is removed from the grid so it is never
listed twice. Verified on both pilots: `spec-engine` heroes the tutorial
(cards: how-to/reference/architecture); `models` degrades to the how-to
hero with no tutorial card (cards: reference/architecture). Deterministic,
no LLM/AST. Features with no `nav.mkdocs` pages record a skip
("hub (no docs pages)"), never an error.

**Convention (D11):** a thin **projector-emitted hub** at
`docs/features/<feature>.md` in **Variant 1 (hero callout + card grid)**.
Leads with a "Start here" hero → **tutorial when one exists**, degrading
to how-to → concept (first that exists); then a card grid of the
feature's available kinds. Tutorial is prominent by **placement**, not by
rule — resolving the coverage gap (only ~9–11/25, a minority of ~270,
have tutorials) without dead front doors and without taxing the
quick-lookup reader. Fully D10-compatible (hub *links* the tutorial,
never reproduces it).

**Implementation TODO (R7):** projector/driver gains a hub-emit step —
given a feature's available kinds + whether `docs/tutorials/<feature>.md`
exists, write the Variant-1 hub (cards render only for kinds that exist;
hero target precedence tutorial → how-to → concept). The mockup in the
2026-06-21 design session is the visual spec.

**Still open (carried):** in-tool surface — should the ops living-docs
dashboard / `help_lookup` also lead with the tutorial? D11 scoped this to
the published site only. And whether to invest in generating more
tutorials (LLM channel) to widen the marquee-entry coverage.

**Original framing (retained):**

Patrick wants a feature's **tutorial** to be the first thing a user of
that feature sees — the rich, narrative `docs/tutorials/<feature>.md`
(e.g. spec-engine's "Build a Spec Engine Pipeline Runner"), not the
concept/reference. This is a placement/nav decision and is fully
compatible with D10 (tutorials stay hand-authored/LLM-generated, never
projected — see [keep-rich-tutorials feedback]).

**Constraint that shapes the design — coverage.** Tutorials are the one
channel the projector cannot generate. Today only **11 of 25** manifest
features have a tutorial (`models`, a pilot feature, does NOT); the
~270-feature rollout will have a tutorial for a small minority. So a
literal "tutorial is the first/only page" rule gives most features a
dead front door, and it taxes the frequent quick-answer lookup to serve
the first-visit case (Diátaxis puts tutorials as a deliberate detour,
not the hub).

**Proposed design (decide at rollout, with P4):** a thin per-feature
**landing/hub page** that **leads with a prominent "Start here →
Tutorial" CTA when a tutorial exists**, then routes to how-to /
reference / concept; degrades gracefully to concept/how-to-first when
no tutorial exists. The projector/driver can emit the hub (it knows the
feature's available kinds) and the nav fragment P4 needs. Open
questions: in-tool surface (does the ops dashboard / `help_lookup`
also lead with the tutorial?), and whether to invest in generating more
tutorials (LLM channel, rich) to widen coverage before making them the
marquee entry.
