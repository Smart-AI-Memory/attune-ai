---
name: author-feature
description: "Author a single-source feature page — a code-verified master that projects to .help kinds + docs pages, no API credits. Triggers on: author a feature page, single-source doc, new feature master, draft docs without an api."
---
# Author-feature — single-source authoring, verified

**IMPORTANT: Start your response by telling the user:**

> **Author-feature** — I'll author a single-source master for this
> feature, grounding every claim in live code and running the gates as
> I go, then project it to the help kinds + docs pages. No LLM
> generation, no API credits.

This skill makes the driving session a disciplined author of a
**single-source master** (`content/features/<feature>.md`). One master
projects deterministically to 10 `.help` kinds + 4 `docs/` pages — no
generator, no API. The empirical result that motivates it: the session
is a *superior* polish layer to an LLM pass and the only one that
catches correctness bugs (PR #1188). The risk it manages: a master is a
single point of *failure*, so **verification is the spine** — grep the
symbol before you write it, run the audit before you commit, fix the
master not the output.

This is *judgment*, not plumbing. It calls the deterministic tools (the
in-repo projector, the audits); it never re-implements them and never
emits prose for blind rubber-stamping.

## The flow

```text
locate/scaffold  →  author section-by-section (grounded in code)
                 →  verify continuously  →  project  →  preview  →  commit
```

### Step 1 — locate or scaffold the master

The master lives at `content/features/<feature>.md`. If it exists,
you're revising — open it. If not, create it by **copying a canonical
projected page for structure** — e.g. `content/features/security-audit.md`
— then replacing its content. Do not invent the layout; the projector
expects a fixed section contract (below).

Frontmatter (required):

```yaml
---
feature: <slug>
summary: <one line>
tags: [<tag>, <tag>]
source_globs:
  - src/attune/workflows/<feature>.py
nav:
  help: <slug>
  mkdocs:
    how-to: how-to/<slug>
    architecture: architecture/<slug>
    reference: reference/<slug>
---
```

Declare `how-to` / `architecture` / `reference` but **not** `tutorial`:
the projector drops tutorial (a guided tutorial resists pure section
projection — it stays hand-authored).

Then add a `.help/features.yaml` entry under `features:` with
`description`, `tags`, and **`status: manual`** — and **no `files:`**.
`manual` means projector-owned, so staleness/maintenance never
overwrites it with LLM output.

### Step 2 — author section by section, grounded in code

Write each section the projector expects (the **section contract**):

| Heading | Holds |
| --- | --- |
| `## Overview` | what the feature is, 1–2 paragraphs |
| `## Concepts` | the model — `### subsections` for each idea |
| `## Quickstart` | the shortest real path to using it |
| `## Tasks` | `### task` blocks with runnable CLI / Python |
| `## Reference` | API tables — classes, params, entry points |
| `## Comparison` | when to use this vs the alternatives |
| `## Failure modes` | risk areas + diagnosis order |
| `## FAQ seeds` | seed Q&A (the FAQ kind is projector-skipped today) |
| `## Notes & tips` | operational asides |
| `## Design & extension` | design decisions + extension points |

**Verification is the spine of this step (D2).** Before you write a
claim, find the truth:

- **Before an API table** — `grep` the `__all__`, the class, the enum,
  the tool schema. Never confabulate a symbol or a field.
  - `grep -rn "class <Name>" src/attune/`
  - `grep -n "<Name>" src/attune/workflows/__init__.py` (re-exports)
  - `python -c "import inspect, attune.X as m; print(inspect.signature(m.Cls.__init__))"`
- **Before a CLI example** — confirm the flag actually exists
  (`attune <cmd> --help`, or grep the argparse).
- **Symbols re-exported at the package** must be cited at the package,
  not the submodule — `import_repair` canonicalizes
  `from attune.workflows.foo import Bar` → `from attune.workflows import
  Bar` and the fact-check flags the un-canonical form. Write the
  package-level import.

### Step 3 — verify continuously (fix the master, never the output)

Run the gates as you author, not at the end. A fact-check finding means
**fix the claim in the master** — never "ship the warning."

```bash
# Dry-run the projection: fact-check + example check + plan, no writes.
python scripts/project_features.py <feature> --dry-run

# Authoritative import resolution (repo src on sys.path).
python scripts/audit_doc_imports.py --paths content/features/<feature>.md
```

The dry-run runs the in-repo projector
(`attune.authoring.projector.validate_master_file` + `project_feature`)
and prints fact-check findings + runnable-example problems alongside the
planned outputs. Resolve every `error`-severity finding before building.

### Step 3.5 — optional: polish-master pass (reviewable diff)

When the prose needs a quality pass beyond your own editing, the D10
polish action runs the absorbed LLM polish **on the master** and shows
a reviewable diff — never a silent rewrite, never on projected output:

```bash
PYTHONPATH=src python scripts/polish_master.py <feature> [--apply]
```

Diff-only by default; `--apply` writes the master (then re-run the
Step 3 gates). **This is a billable premium-tier LLM call** —
subscription-first via `attune.models.single_turn`, cached in
`~/.attune/polish_cache` — so name the spend to the user before
running it. You remain the judge: reject diff hunks that drift from
code truth; the fact-check gates re-verify whatever you keep.

### Step 4 — project for real, then sync the served bundle

```bash
python scripts/project_features.py <feature>     # writes 10 .help kinds + 4 docs pages
python scripts/sync_help_bundle.py               # copy templates → served bundle
```

`sync_help_bundle.py` is **required** — it copies the projected
templates into `plugin/help/generated/` (the bundle that reaches pip
users; `.help/templates` is only the source). Skipping it fails
`tests/unit/help/test_help_bundle_sync.py` ("N bundle file(s) out of
sync"). The mkdocs `build` job auto-wires the new hub via
`docs/hooks/feature_nav.py` — no manual `mkdocs.yml` nav edit.

### Step 5 — preview, then verify green, then commit

Show the projected hub + pages to the user **before staging** (the
"show generated output sooner" discipline), then confirm the gates:

```bash
python scripts/audit_doc_imports.py
python scripts/audit_docs_wiring.py
pytest tests/unit/help
```

## Gotchas (these bit #1188)

- **ENV — make `attune` importable.** The projector is in-repo
  (`attune.authoring`, pure — no jinja/anthropic), so from a worktree the
  robust invocation is `PYTHONPATH=src python scripts/project_features.py
  <feature>` — it puts the worktree's own `src/` ahead of the editable
  mapping. (The audits already do this themselves.) If you skip
  `PYTHONPATH=src`, a bare `python` resolving via the editable mapping
  can miss worktree-only modules.
- **Trust the audit, not a bare `python -c`.** From a worktree a bare
  `python -c "from attune.X import …"` can falsely `ModuleNotFoundError`
  (the editable MAPPING points at main's possibly-older `src/`) WHILE
  `scripts/audit_doc_imports.py` (which puts the worktree `src/` on
  `sys.path`) correctly reports all imports resolve. The audit is
  authoritative.
- **Zero API credits by default.** The core flow is deterministic
  projection + hand-authored prose. The one sanctioned LLM surface is
  the optional Step 3.5 polish-master diff (D10) — on the MASTER,
  reviewable, spend named first. If you find yourself reaching for
  `attune-author generate` or any polish of *projected output*, stop —
  those paths are retired; the session is the author.

## What this skill does NOT do

- It does **not** generate prose for blind approval — you author *with*
  verification, grounded in code; even the optional polish-master pass
  lands as a diff you judge.
- It does **not** call any LLM path silently — the only LLM surface is
  Step 3.5, explicit and spend-named.
- It does **not** re-implement the projector, the audits, or the (future)
  scaffolder — it *calls* them.

## Acceptance (self-demonstration)

The skill is "done" for a feature when a fresh session, given only this
skill, authors a master that **projects byte-clean and passes
`doc-import-audit` + the bundle sync on the first real attempt** — the
#1188 outcome, reproduced without out-of-band knowledge. Registered ≠
working: dogfood the real flow; the green projection is the receipt.
