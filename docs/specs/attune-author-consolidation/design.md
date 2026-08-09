# attune-author Consolidation — Design

**Status:** complete (2026-07-27; flipped at 2026-08-08 triage) —
T1–T5 all executed: absorb + repoint (#1193/#1203/#1205), T5 docs +
script repoints (#1562/#1563), T3 polish machinery absorbed (#1574),
T2 resolver fold-in (#1586/#1699), T4 archive-without-yank executed
2026-07-27 (`[author]` extra removed from pyproject.toml;
help-freshness regen path retired). Residual, tracked separately:
`plugins/attune-author/hooks/help_post_commit.py` still imports
`attune_author.maintenance.run_hook` — never absorbed, now a
permanent no-op under its ImportError guard · pairs with
[requirements.md](requirements.md).

## The new home

A single internal package `src/attune/authoring/` holding the absorbed
distribution machinery:

```text
attune/authoring/
  projector.py        # from attune_author.projector (project_feature, validate_master_file)
  staleness.py        # from attune_author.staleness  (check_staleness)
  manifest.py         # from attune_author.manifest   (load_manifest, Manifest)
  fact_check/         # reliable checkers only:
    python_refs.py    #   — but import resolution defers to the authoritative resolver (R2)
    cli_refs.py
    tutorial_static_check.py
    doc_examples.py
    import_repair.py
  maintenance.py      # run_hook only (the deterministic post-commit hook)
  freshness/symbols.py
```

Not moved (deleted instead): `generator`, `polish`, `polish_prompts`,
`doc_gen`, `maintenance_batch`, `faithfulness`, the package `cli`/`mcp`,
`auth`, `editor_launcher`, `bootstrap`, `skill_export`, `meta_templates`
that exist only for the LLM path. (Audit each against the absorb list
before deleting — anything the absorbed modules import transitively comes
too; anything only the LLM path imports goes.)

## Step 1 — Absorb + repoint (the mechanical core)

Move the absorb-list modules into `attune/authoring/`, preserving public
callable names. Then repoint each consumer (requirements table):

| Consumer | Before | After |
|---|---|---|
| `project_features.py` | `from attune_author.projector import …` | `from attune.authoring.projector import …` |
| `help_post_commit.py` hook | `from attune_author.maintenance import run_hook` | `from attune.authoring.maintenance import run_hook` |
| staleness scripts | `from attune_author import check_staleness, load_manifest` | `from attune.authoring import …` |
| `regenerate_help_templates.py` | `from attune_author import load_manifest` | `from attune.authoring import load_manifest` |
| `ops/help_data.py` | parses `attune-author status` CLI | call the in-repo `check_staleness` directly (drop the CLI-text parse) |

The projector's output must be **byte-identical** pre/post move — a golden
test on an existing master is the guard.

## Step 2 — Fold in #1191 (the resolver, R2)

The absorbed `fact_check/python_refs.py` no longer resolves imports
against the editable mapping. Extract `audit_doc_imports.py`'s
src-on-`sys.path` resolver into a shared helper
(`attune.authoring.fact_check.imports`) and have both the audit script and
the absorbed checker call it. Result: one authoritative import verdict,
the line-115 false positive gone — #1191's T1, done where the code now
lives. (Supersedes #1191's "bolt a second resolver across the package
line" shape.)

## Step 3 — Retire the authoring machinery (R3)

Delete the LLM surface. Guard the deletion:

- `grep` attune-ai for any import of a to-be-deleted module — there must
  be none except `personal.py`'s `polish_template` (handled in Step 4)
  and `help_data.py`'s CLI parse (handled in Step 1).
- Remove the `[author]` extra's `anthropic` / `claude-agent-sdk` deps
  from the authoring path; confirm nothing else in attune-ai's base or
  `[author]` install needs them (workflows have their own SDK dep — leave
  that untouched).

## Step 4 — `polish_template` behavior change (R6)

`personal.py::_load_author` already returns `None` when the import fails.
Two clean options:

- **(a) Drop the polish hook** — delete `_load_author`'s polish call; rely
  on `_build_skeleton`. The driving session (or the authoring skill)
  polishes memory entries if wanted, consistent with the whole thesis.
- **(b) Keep a tiny in-repo `polish_template` shim** that is a no-op
  pass-through (returns input unchanged) for callers that still reference
  it.

Recommend **(a)** — it's the thesis applied (no API polish; the session is
the polish layer). Name it in the changelog as a behavior change.

## Step 5 — Retire the package (R7, reversible, separate)

After Steps 1–4, no attune-ai code imports `attune_author`. Then:

- **Archive** the `attune-author` repo (beta, no adopters — confirmed) and
  **yank/deprecate** the PyPI package, OR
- leave a **thin shim** release that re-exports the absorbed callables from
  attune-ai for any stray external user.

Given no adopters, archive is the simpler endpoint. Keep this a *distinct
PR/decision* from the code move so the irreversible step (yank) is
deliberate.

## Tasks / sequencing

1. **T1 — Absorb + repoint** (Steps 1): move modules, repoint the six
   consumers, golden projector test. Acceptance: `git grep attune_author`
   in attune-ai is clean except `personal.py`; projector output identical.
2. **T2 — Resolver fold-in** (Step 2 = #1191 T1): shared authoritative
   resolver; the line-115 regression test passes.
3. **T3 — Retire authoring machinery + drop deps** (Steps 3-4): delete the
   LLM surface, drop `anthropic`/`claude-agent-sdk` from the author path,
   handle `polish_template` per Step 4(a).
4. **T4 — Retire the package** (Step 5): archive repo / yank PyPI or ship a
   shim. Its own PR + decision.
5. **T5 — Docs** : update #1189's playbook lesson + any `attune-author`
   references in docs to the in-repo module; the
   [single-source-authoring](../single-source-authoring/) skill lands in
   parallel to cover the authoring half.

T1+T2 land first (they capture the architectural win and #1191). T3 is the
deletion. T4 is the deliberate, reversible package decision. T5 closes.

## Testing

- **Golden projector:** an existing master projects byte-identically
  before and after the move.
- **Resolver agreement:** the absorbed checker and `audit_doc_imports`
  agree on a fixture set (resolvable / unresolvable / skip-marked); the
  multi-line `from attune.elicitation import (…)` yields zero findings.
- **Consumer smoke:** `project_features.py`, the staleness scripts, and
  the post-commit hook run green against the in-repo module.
- **Dep guard:** a test (or CI grep) that the authoring path imports no
  `anthropic` / `claude_agent_sdk`.
