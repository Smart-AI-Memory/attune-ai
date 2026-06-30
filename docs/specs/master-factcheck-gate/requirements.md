# Master Fact-Check — Reconciliation & Trust

**Status:** draft (2026-06-30) · **Owner:** Patrick + agent
**Born:** the single-source insights discussion. The claim on the table
was "the projection is deterministic and trusted, but the master's
verification is warn-only and pointed backwards." Verifying that claim
before speccing (the spec-premise discipline) **partly refuted it** — and
the refutation is the spec.

## What verifying the premise found

The master's verification is split across two mechanisms with
**overlapping scope and opposite reliability**:

| Mechanism | Where | Scope | Reliability | Status |
|-----------|-------|-------|-------------|--------|
| `audit_doc_imports.py` | attune-ai | `attune` imports in `content/features/**` + served docs | **authoritative** — adds repo `src/` to `sys.path` | **REQUIRED** (promoted from advisory) |
| `check_python_refs` (via `validate_master_file`) | `attune_author`, run by `project_features.py` | python refs in master fences | **flaky** — resolves against the editable-install mapping | warn-only |

So the part everyone worried was ungated — *do the master's imports
resolve?* — **is already gated and required**, and it covers masters. The
real problem is the *other* checker: it is (a) **partly redundant** with
the required gate, and (b) **unreliable** in a way that actively erodes
trust — authoring `elicitation-forms.md` it flagged a valid multi-line
`from attune.elicitation import …` as "module not importable" while the
required gate passed the same line. An author who believes the scary
warning either chases a non-bug or learns to ignore the checker entirely
— the worst outcome for a verification tool.

## Problem

1. **A false-positive checker is worse than no checker.** The projector's
   warn-only fact-check emits "not importable" on imports that *do*
   resolve, because it imports against the main venv's editable mapping
   (possibly-stale `src`) instead of the authoritative repo-`src`-on-path
   mechanism the required gate uses. The fix the editable-mapping lesson
   already prescribes — "trust the audit, not the convenient import" —
   should be *built into the tool*, not left to the author to know.
2. **Two checkers, one question, no single source of truth on imports.**
   Imports are checked twice (authoritatively by the required gate,
   flakily by the projector). The author shouldn't reconcile two answers.
3. **The genuinely-incremental coverage is undefined.** Whatever
   `check_python_refs` does *beyond* import resolution (symbol refs in
   prose, method names) is the only part with marginal value — and it has
   never been separated from the redundant import check or assessed for
   false-positive rate. Per the doc-import-gate lesson, deeper-than-import
   checking is high-false-positive and was deliberately left ungated.

## Goal

One trustworthy verification story for a master: **the required gate is
the authority on imports; the projector's advisory check is either made
to agree with it or defers to it; and any check beyond imports is gated
only if it is reliable, advisory otherwise.** When a master is wrong, the
author gets one correct message, at the master, before projection fans
the error to 14 outputs.

## Requirements

- **R1 — Kill the false positive.** The projector's pre-projection
  python-ref check MUST resolve imports the authoritative way (repo `src/`
  on `sys.path`, as `audit_doc_imports.py` does) — never against the
  editable-install mapping. A valid import must never be flagged.
- **R2 — No double jeopardy on imports.** The projector does not
  re-adjudicate what the required gate already authoritatively checks. It
  either reuses the gate's resolver or defers imports to it, so there is a
  single source of truth on "do the imports resolve."
- **R3 — Separate and characterize the incremental checks.** Identify what
  `check_python_refs` asserts *beyond* import resolution. For each such
  check, measure its false-positive behavior on the existing 27 masters
  before deciding its fate.
- **R4 — Gate only the reliable subset.** Promote to blocking (or fold
  into the required gate) only checks with a demonstrated near-zero
  false-positive rate. Genuinely-ambiguous checks (method-call accuracy,
  prose-claim accuracy) stay **advisory by design** — the same line the
  doc-import-gate drew, for the same reason.
- **R5 — One author-facing message.** A master that fails verification
  produces a single, actionable error at the master (file + line + what
  doesn't resolve), at authoring/projection time — not 14 downstream
  failures and not a contradictory pair of warnings.

## Non-goals

- **Not method-signature or claim-accuracy gating.** High false-positive,
  deliberately ungated (doc-import-gate precedent). May stay advisory;
  never blocking on the strength of an LLM-grounded fact-checker alone.
- **Not a rewrite of `attune_author`.** Prefer fixing the resolution in
  the attune-ai-side driver (`project_features.py`) — e.g. calling the
  in-repo authoritative resolver — over re-engineering the sibling
  package, unless R1/R2 genuinely require a sibling change.
- **Not the scaffolder.** Sibling spec
  [feature-page-scaffolder](../feature-page-scaffolder/) (PR #1190);
  independent.

## Acceptance

- Re-authoring any of the 27 existing masters surfaces **zero** false
  "not importable" warnings.
- The projector and the required gate never disagree on whether a
  master's imports resolve.
- Any check that beyond-imports verification gates has a documented
  false-positive measurement on the current corpus justifying the
  promotion; everything unproven stays advisory.
