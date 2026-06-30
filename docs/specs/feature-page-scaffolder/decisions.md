# Feature-Page Scaffolder — Decisions

**Status:** draft (2026-06-30) · log for
[requirements.md](requirements.md) / [design.md](design.md).

## D1 — Scaffold the skeleton, never generate the body

**Decided.** The tool writes frontmatter + section headings + the
manifest entry; it does NOT write prose. The master stays human/LLM-
authored and fact-checked against live code. This is non-negotiable: it
is the exact property that makes single-source trustworthy (the
generation path emits systematic fiction — that lesson is why the
projector is deterministic and why this tool stays out of the body). A
"helpful" content stub would reintroduce the failure mode.

## D2 — Insert the `features.yaml` entry by append, preserving comments

**Decided.** `.help/features.yaml` is heavily commented (each entry has a
paragraph explaining `status: manual`). A naive parse-and-re-emit YAML
round-trip drops those comments. So `scaffold` appends a well-formed
block under `features:` textually (anchored on the `features:` key /
last entry), then re-parses to validate — rather than rewriting the whole
file. Correctness is checked by the re-parse; comments survive.

## D3 — Two verbs (`scaffold` then `build`), not one command

**Decided.** The flow has an irreducible human step — filling the prose.
A single command would either (a) generate the body (violates D1) or
(b) stop and require resumption anyway. Two explicit verbs make the human
gap a first-class part of the contract: `scaffold` sets up, the author
writes, `build` distributes + verifies.

## D4 — The skeleton lives in a versioned `_TEMPLATE.md`, not a string

**Decided.** The canonical section contract (which headings, in what
order, that the projector maps to kinds) is the thing most likely to
drift. Keeping it as `content/features/_TEMPLATE.md` makes it reviewable
and diff-able like any content, and gives the projector's contract one
visible home. Leading underscore keeps it out of feature enumeration.

## D5 — A script for v1, a CLI wrapper later

**Decided.** `scripts/new_feature.py` beside `project_features.py` /
`sync_help_bundle.py` — the trio it composes. A `attune feature new` CLI
subcommand is a thin future wrapper; coupling to the CLI router now would
widen the blast radius for no v1 benefit. Out of scope, not rejected.

## D6 — `build` verifies postconditions, not exit codes

**Decided.** Per R6 and the "registered ≠ working" discipline, each stage
asserts its real effect: project → the output files exist; sync →
`sync_help_bundle.py --check` exits 0 (re-verified, not inferred from the
write); audits → exit 0 on the actually-new pages. A green wrapper means
the artifacts are provably coherent, not that four subprocesses returned
zero.

## Open

- **Fact-check gate (sibling, not here).** Promoting
  `validate_master_file` from warn-only to blocking — and making it
  robust across the editable-install mapping confusion — is the natural
  partner improvement (the master is the single point of truth *and*
  failure). Tracked as its own effort; this spec assumes the fact-check
  stays advisory.
- **`source_globs` → drift-propose (future vision).** The richer prize is
  the fact-checker proposing diffs to the master's API tables when the
  globbed code moves — the "staleness-aware mirror" realized. Far out of
  this spec's scope; noted so the scaffolder's template leaves the API
  tables in a shape that a future drift-proposer can target.
