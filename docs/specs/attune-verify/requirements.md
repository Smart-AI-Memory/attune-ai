# Spec: attune-verify — Generation Fact-Checker

> A standalone library that verifies the *named entities* in
> LLM-generated content actually exist — imports import, CLI flags
> are real, links resolve, counts match source — and, via an LLM
> layer, that the content is semantically faithful, so
> hallucinations that pass unit tests are caught before they reach
> a reader.

**Status:** draft (2026-06-02)
**Created:** 2026-06-02
**Owner:** TBD
**Related:** the "Discipline of Agent Collaboration" §7
(Verification) — this is the *output-side* fact-check mode pulled
out as its own product; complements **attune-rag** (input-side
grounding) and **subsumes attune-author**'s planned AST fact-check
(author#27).

---

## Problem statement

LLM generation pipelines in the attune family — attune-author's
doc polish, `rag-code-gen`, the `doc-gen` workflow — emit content
that *reads* correct and passes unit tests, yet invents named
entities that break any reader who follows the output literally.
Per the discipline's §7: "unit tests catch zero hallucinations."
Tests assert the function returned the expected *type*; they cannot
assert it returned something *true*.

A single attune-author doc regen (ops-dashboard, 15 templates + 4
docs, 2026-05-14) produced six distinct hallucination classes:

1. **Invented CLI flag** with inverted semantics (`--allow-run`
   when the real flag is `--read-only`).
2. **Private-module imports** that raise `ModuleNotFoundError`.
3. **Dead cross-references** — "See also" links to docs that don't
   exist.
4. **Wrong numeric count** (`498 templates` vs. real 259).
5. **Wrong route paths** (`POST /run` vs. real
   `POST /workflows/{name}/run`).
6. **Insecure example** (`host="0.0.0.0"` with no auth callout).

Three of the six actively break readers who follow the docs. The
root cause: a polish/generation pass has source as *context* but
isn't *constrained* to it — the model fills surrounding scaffolding
from priors that "sound right."

Today the only defense is a *planned* AST fact-check buried inside
attune-author (author#27). It is neither built nor reusable. Every
other generation pipeline in the family ships unverified.

### Why this is distinct from attune-rag (the "not combined" point)

attune-rag grounds generation in **accurate retrieved sources** and
citation-forces each claim, so claims are *supported by* real data
("is this claim *supported*?"). attune-verify checks the
**output**: the named things in the produced artifact actually
exist ("is this *real*?").

Grounding can be perfect and the output still invent a flag that
was never in the retrieved context. The two checks *bracket*
generation — complementary, not redundant — which is why this is a
separate product, not a feature of attune-rag.

---

## Scope

### In scope

- A standalone, dependency-light library **`attune-verify`** with a
  small public API: given generated content + a `VerifyContext`
  declaring the truth sources, return typed findings naming each
  unverifiable entity.
- Deterministic (no-LLM) checkers for the resolvable classes:
  - **Imports** — every `import`/`from … import …` in code fences
    resolves against the target environment.
  - **CLI flags** — flags referenced for a command exist in its
    `--help` output.
  - **Links** — markdown link targets resolve to real files/anchors.
  - **Counts** — numeric/quantitative claims match a source value
    the caller supplies.
- An **LLM semantic layer** — ships in v1, flag-controllable —
  reusing attune-rag's `FaithfulnessJudge` to catch the
  meaning-level class the deterministic checkers cannot: a missing
  security callout, an insecure example, claims unsupported by
  source.
- A clean integration surface so any pipeline (attune-author
  polish, `rag-code-gen`, `doc-gen`) can call it as a
  post-generation gate: returns structured findings; an opt-in
  `raise_if_failed()` helper is available for callers wanting a
  hard gate.
- Family packaging per the sibling pattern: full source at
  `../attune-verify/`, pointer stub at
  `packages/attune-verify/README.md`, a `[tool.uv.sources]` entry,
  own PyPI publish + `pypi` env — **publish 0.1.0 early** so the
  first consumer's integration is CI-testable.

### Out of scope

- **Executing** LLM-generated code to test it — explicit security
  boundary; deferred. attune-verify reads and statically resolves;
  it never runs generated code.
- **Retrieval grounding / citation enforcement** — that is
  attune-rag's input-side job and is *not* duplicated here.
- **Auto-fixing** hallucinations — attune-verify *reports*; repair
  is the calling pipeline's decision.
- **Prompt-side prevention** (injecting ground truth into the
  generation prompt) — a pipeline concern, not a verifier.
- **`mypy --strict` type-checking of code fences** (design D) —
  deferred past v1.

---

## Design alternatives

The four interventions surfaced by attune-author's hallucination
analysis, recast as build options.

### A — Deterministic AST / static entity-resolver (v1 core)

A no-LLM library that parses generated content and resolves named
entities against ground truth: AST-walk code fences for imports,
shell out to `--help` for flags, stat link targets, compare counts.

- **Catches:** five of the six classes (imports, flags, links,
  counts; route paths via link/flag resolution).
- **Misses:** the semantic class (insecure example with a missing
  callout) — there is no entity to resolve.
- **Cost:** cheap, fast, no API spend, fully testable.

### B — Inject ground truth into the generation prompt

Prevention upstream: feed rendered `--help`, `__all__`, dataclass
fields into the prompt so the model is constrained.

- **Nature:** a *pipeline* change, not a verifier. Reduces the
  hallucination rate but cannot *prove* the output is clean.
  Out of scope — belongs to the consuming pipeline.

### C — attune-rag `FaithfulnessJudge` LLM layer (adopted in v1)

An LLM-backed layer (forced tool-use → schema) that catches the
semantic class A cannot — missing content, insecure examples,
unsupported claims — by judging the artifact against source.

- **Catches:** the sixth class and other meaning-level gaps.
- **Cost:** API spend per check; reuses proven rag machinery.
- **Decision:** adopted in v1 (flag-controllable, so
  deterministic-only runs still cost nothing). Phase 2 must verify
  the `FaithfulnessJudge` API in the installed attune-rag before
  depending on it.

### D — Static analysis (`mypy --strict`) of code fences

Type-check tutorial code fences to catch wrong code that
import-resolution alone misses. A future checker; deferred past v1.

---

## Recommendation

**Build `attune-verify` as a standalone sibling package whose v1
covers all six hallucination classes** — intervention A (the
deterministic entity-resolver for imports, flags, links, counts)
**plus** intervention C (an LLM layer reusing attune-rag's
`FaithfulnessJudge`) for the semantic class A cannot reach. The LLM
layer is flag-controllable so deterministic-only runs cost nothing,
but it ships in v1 (decided 2026-06-02 — accuracy over a cheaper
partial v1). **Defer D** (mypy-fence); treat **B** as out of scope
(a pipeline change). Standalone over a module inside rag/author
because the check is reusable across all three pipelines and is a
distinct concern from both grounding and generation.

attune-verify is the output-side complement to attune-rag's
input-side grounding; together they bracket generation in the §7
verification story.

---

## Acceptance criteria

For Phase 4 implementation to be considered complete:

1. `attune-verify` exists as a sibling package (full source at
   `../attune-verify/`, pointer stub at
   `packages/attune-verify/README.md`, `[tool.uv.sources]` entry,
   PyPI-ready `pyproject.toml`) and **0.1.0 is published to PyPI**
   before the consumer integration, so CI can exercise it rather
   than `importorskip` it.
2. A small public API — e.g.
   `verify(content, context: VerifyContext) -> VerifyResult` —
   returning typed finding kinds (`unresolved_import`,
   `unknown_flag`, `dead_link`, `count_mismatch`, `semantic`),
   plus an opt-in `raise_if_failed()` helper.
3. Deterministic checkers for all four resolvable classes **and**
   the LLM semantic layer, each with tests **and** a regression
   fixture drawn from the author-#351 known-hallucination case, so
   a real past failure is provably caught.
4. **attune-author polish** wired to call attune-verify as a
   post-generation gate (the first-consumer integration).
5. attune-verify never executes generated code (security boundary
   asserted by test).
6. **Docs accuracy:** family READMEs/docs describe attune-verify as
   a real capability **only once it ships**; until then any mention
   is labeled roadmap/planned — per the website-content-accuracy
   rule and the "fictional workflows" lesson.
7. **attune-author#27 is closed** and repointed to this spec; the
   fact-check capability no longer lives inside author.

---

## Decisions (Phase-1 alignment, 2026-06-02)

All six Phase-1 questions were walked with Patrick and decided:

1. **v1 LLM layer** → ship **A + C in v1** (all six classes from
   day one; LLM layer flag-controllable but present). Accuracy over
   a cheaper deterministic-only v1.
2. **Ground-truth provenance** → an explicit **`VerifyContext`**
   the caller supplies (project root, env/command, count sources);
   attune-verify performs the resolution.
3. **Findings surface** → **return structured findings**; the
   consumer decides warn/gate/fix. Opt-in `raise_if_failed()` for a
   hard gate.
4. **First consumer** → **attune-author polish** (the origin case).
5. **attune-author#27** → **subsumed**; verify owns the capability,
   #27 closes and repoints here, author becomes a consumer.
6. **Repo bring-up** → standard sibling pattern; **publish 0.1.0
   early** so the author integration is CI-testable.

### Remaining open for Phase 2 design

- The exact `VerifyContext` shape — how much attune-verify
  auto-resolves (env import resolution, `--help` capture) vs.
  requires the caller to declare explicitly.
- Whether the `FaithfulnessJudge` reuse is a hard dependency on
  attune-rag or a duck-typed optional integration (and how it
  degrades when rag isn't installed).
