# attune-author Consolidation & Retirement — Requirements

**Status:** complete (2026-07-27; flipped at 2026-08-08 triage —
T1–T5 executed, T4 archive-without-yank done; receipts in
design.md status) · **Owner:** Patrick + agent
**Absorbs:** single-source-authoring (merged 2026-07-14 at triage —
same domain; archived copy retains its draft reqs/design)
**Born:** the single-source insights discussion. Patrick: "attune-author
is going to have to be either retired or redesigned." Verification of the
package's scope (it is beta, no real adopters, retire-able) plus the
authoring-vs-mechanics analysis resolved the framing: **absorb the
deterministic distribution machinery into attune-ai, retire the LLM
authoring machinery and the standalone package.**

Sibling spec: [single-source-authoring](../single-source-authoring/) —
the skill that *replaces* the authoring machinery this spec deletes. The
two are one move seen from two sides: delete the authoring code there →
absorb the distribution code here.

## The principle this rests on

**Instructions/the driving session for AUTHORING (judgment — what to say,
how to say it well); code for MECHANICS (transform, hash, verify —
anything that must be byte-identical every run).** attune-author's
original error was using an LLM for authoring (it hallucinated — six
documented shapes) while bundling that with genuinely-deterministic
machinery. The split below follows that line exactly.

## What the assessment found

attune-author is ~15k LOC across three subsystems with opposite verdicts:

- **Authoring machinery (DELETE):** `generator.py` (1,754), `polish.py`
  (882), `polish_prompts.py` (652), `doc_gen/_anthropic*` (~600),
  `maintenance_batch.py` (727, LLM batch), `faithfulness/` (323), the
  package's own `mcp/` + LLM `cli` commands, and the `ai` extra
  (`anthropic`, `claude-agent-sdk`). The driving session + a skill
  replace it (the lesson: the session is a *superior* polish layer and
  the only one that catches correctness bugs).
- **Distribution machinery (ABSORB as code):** `projector.py` (508,
  deterministic fan-out), `staleness.py` (514, sha256 drift), `manifest.py`
  (348), the reliable `fact_check/*` (`python_refs`, `cli_refs`,
  `tutorial_static_check`, `doc_examples`, `import_repair` ≈ 1,060), the
  maintenance *hook* (`maintenance.py` run_hook, 356), `freshness/symbols`
  (233). Deps: just `jinja2`.

**Net: the delete list is larger than the absorb list** — the
consolidation simplifies, it doesn't grow attune-ai.

## attune-ai's actual consumption surface (the repoint targets)

| Consumer in attune-ai | Imports from attune_author |
|---|---|
| `scripts/project_features.py` | `projector.project_feature`, `validate_master_file` |
| `plugins/attune-author/hooks/help_post_commit.py` | `maintenance.run_hook` |
| `scripts/help_aggregator_prototype.py`, `scripts/list_stale_help_features.py` | `check_staleness`, `load_manifest` |
| `scripts/regenerate_help_templates.py` | `load_manifest` |
| `src/attune/memory/personal.py` | `polish.polish_template` (lazy, optional) |
| `src/attune/ops/help_data.py` | parses `attune-author status` CLI output |

## Requirements

- **R1 — Absorb the distribution machinery into attune-ai** as an internal
  module (e.g. `attune.authoring` / `attune.single_source`), behind the
  same callables the consumers already use, so the driver and hooks barely
  change.
- **R2 — One resolver.** The absorbed import fact-check uses attune-ai's
  authoritative repo-`src`-on-`sys.path` resolver (the `audit_doc_imports`
  mechanism), not the editable-mapping import. This *is* #1191's T1, now
  done in-repo where it belongs (D-ref).
- **R3 — Retire the authoring machinery,** not absorb it. Delete the LLM
  generator/polish/doc_gen/batch/faithfulness/MCP/CLI-generation surface;
  the [single-source-authoring](../single-source-authoring/) skill
  replaces its function.
- **R4 — Repoint every consumer** (the table above) to the in-repo module;
  no attune-ai code path imports `attune_author` after this lands.
- **R5 — Drop the heavy deps.** `anthropic` / `claude-agent-sdk` leave the
  authoring path entirely (they remain only where attune-ai already needs
  them for workflows); `jinja2` is the only dep the absorbed projector
  needs.
- **R6 — Graceful behavior-change naming.** `personal.py`'s optional
  `polish_template` degrades to its existing raw-skeleton fallback
  (`_build_skeleton`); name this change explicitly — it is safe (already
  `try/except → None`) but it is a behavior change, not a silent one.
- **R7 — Retire the *package* as a separate, reversible step.** After the
  code moves and consumers repoint, attune-author the PyPI package either
  becomes a thin shim (re-export from attune-ai) or is yanked/archived.
  Because there are no adopters (confirmed), full retirement is on the
  table; keep it a distinct decision from the code move (D-ref).

## Non-goals

- **Not a staleness rewrite.** `staleness.py` is absorbed *as-is*. Its
  known weaknesses (hash-on-one-file, no completeness check — see lessons)
  are a separate, scoped follow-on, not this spec.
- **Not the authoring skill.** That is the sibling spec; this spec only
  *deletes* the machinery it replaces and assumes it exists.
- **Not a re-test of every absorbed line.** Absorb with its existing test
  intent; add tests only where the move changes a surface (the resolver
  swap, the consumer repoints).

## Acceptance

- `git grep attune_author` in attune-ai returns only history/specs — no
  live import.
- `project_features.py`, the help hooks, and the staleness scripts run
  against the in-repo module with unchanged behavior (the projector's
  output is byte-identical pre/post move).
- The `anthropic` / `claude-agent-sdk` deps no longer enter via the
  authoring path.
- `#1191`'s T1 is satisfied *inside* this move (one authoritative
  resolver; the line-115 false positive gone).
- A decision is recorded on the package's fate (shim vs. archive).
