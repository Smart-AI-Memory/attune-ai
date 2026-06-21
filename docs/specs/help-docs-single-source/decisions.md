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
