# Feature-Page Scaffolder — Requirements

**Status:** draft (2026-06-30) · **Owner:** Patrick + agent
**Born:** authoring the `elicitation-forms` feature page (PR #1188)
surfaced that adding one single-source page is a 5-step procedure with
enough tribal knowledge that it needed its own lessons entry (the
"API-free single-source feature-page playbook"). A procedure that needs
a playbook to remember is a procedure that should be a command.

Direct follow-on to
[help-docs-single-source](../help-docs-single-source/): that program
built the deterministic projector; this spec removes the friction of
*using* it for a new feature.

## Problem

Adding a new single-source feature page today means executing, in order
and from memory:

1. hand-author `content/features/<F>.md` with the exact frontmatter
   schema (`feature`/`summary`/`tags`/`source_globs`/`nav`) and the
   canonical section skeleton (Overview / Concepts / Quickstart / Tasks /
   Reference / …), copied from an existing page;
2. add a `.help/features.yaml` entry (`status: manual`, no `files:`);
3. run `python scripts/project_features.py <F>` — with the **main** venv
   python, because the worktree venv lacks `attune_author`;
4. run `python scripts/sync_help_bundle.py` — or
   `test_help_bundle_sync` fails;
5. verify with `audit_doc_imports.py`, `audit_docs_wiring.py`, and the
   help test suite.

Three costs:

1. **Knowledge cliff.** None of steps 1–5 is discoverable from the repo;
   they live in a lessons entry. A first-time contributor (or a fresh
   agent session) cannot add a page without that out-of-band knowledge.
2. **Silent-failure traps.** Forgetting step 4 produces a red CI that
   names a sync script, not a cause; running step 3 with the wrong venv
   produces a `ModuleNotFoundError` that looks like a missing dependency.
3. **Skeleton drift.** Hand-copying frontmatter and section headings from
   a sibling page invites subtle divergence (a dropped nav kind, a missing
   section the projector expects) that only surfaces at projection time.

The projector already proves the *distribution* is mechanizable. The
*authoring entry* is the remaining manual surface.

## Goal

One command scaffolds a correct, empty-but-complete feature master and its
manifest entry; a second mechanizes the project → sync → audit chain. The
human (or a verifying LLM) fills only the prose — never the plumbing.

## Requirements

- **R1 — Scaffold, never generate.** The tool creates the master's
  *frontmatter and section skeleton* and the `.help/features.yaml` entry.
  It MUST NOT write body prose. (Generation is the failure mode
  single-source exists to avoid; the master stays human/LLM-authored and
  fact-checked.)
- **R2 — Correct-by-construction frontmatter.** The scaffolded master
  carries valid frontmatter for the given slug: `feature`, a `summary`
  and `tags` from arguments, `source_globs` from arguments, and a `nav`
  block with exactly the kinds the projector emits (`how-to`,
  `architecture`, `reference` — **not** `tutorial`).
- **R3 — Section skeleton matches the projector contract.** The skeleton
  contains exactly the section headings the projector maps to kinds, in
  canonical order, each with a one-line placeholder comment, so a filled
  master projects without "missing section" surprises.
- **R4 — One mechanical build step.** A single invocation runs
  `project_features.py` → `sync_help_bundle.py` → the doc audits, and
  reports pass/fail per stage. It resolves the projector's `attune_author`
  dependency itself (or fails with an actionable message), so the
  main-venv gotcha never reaches the user.
- **R5 — Safe and idempotent.** Refuse to overwrite an existing
  `content/features/<F>.md` or a duplicate `features.yaml` entry; validate
  the slug (kebab-case, matches an allowed pattern). A re-run of the build
  step on an unchanged master is a no-op.
- **R6 — Self-verifying.** The tool's own output asserts the
  postconditions it can check (master exists, yaml entry present, N
  outputs projected, bundle in sync, audits clean) — it does not declare
  success on a tool-call that didn't verify its effect.
- **R7 — Documented as the playbook's replacement.** When R1–R6 ship, the
  lessons playbook entry is updated to point at the command as the
  canonical path, keeping the manual steps only as the "what it does
  under the hood" reference.

## Non-goals

- **Not a content generator.** No LLM, no API. (Same constraint that
  makes the projector trustworthy.)
- **Not a fact-checker upgrade.** Strengthening `validate_master_file`
  from warn-only to a gate is a *sibling* opportunity (see the
  single-source insights discussion), tracked separately — not this spec.
- **Not a docs-nav editor.** The mkdocs Features nav is auto-wired by
  `docs/hooks/feature_nav.py`; the scaffolder relies on that, doesn't
  touch `mkdocs.yml`.

## Acceptance

- A contributor with **no playbook knowledge** can run two commands
  (`scaffold`, then `build`) with a filled-in master between them and
  land a green feature-page PR.
- Running the build step omitting the bundle sync is impossible (it's one
  step), so the `test_help_bundle_sync` red can no longer be reached by
  forgetting.
- The `feature new` path spends zero API credits.
- A regression test drives the scaffolder on a throwaway slug and asserts
  the projected + synced outputs match the projector's own output.
