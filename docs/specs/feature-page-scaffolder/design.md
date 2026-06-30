# Feature-Page Scaffolder — Design

**Status:** draft (2026-06-30) · pairs with
[requirements.md](requirements.md).

## Shape: two verbs, a human gap between them

The authoring flow has a deliberate human step in the middle — filling
the prose. So the tool is two verbs, not one:

```text
scaffold  →  [ human/LLM fills the master's prose ]  →  build
```

- **`scaffold <slug> --summary … --tags … --globs …`** — writes
  `content/features/<slug>.md` (frontmatter + empty section skeleton) and
  inserts the `.help/features.yaml` entry. Stops. Prints "now fill the
  master, then run `build <slug>`."
- **`build <slug>`** — runs `project_features.py <slug>` →
  `sync_help_bundle.py` → `audit_doc_imports.py` (scoped to the new
  pages) → `audit_docs_wiring.py`, asserting each stage's postcondition,
  and prints a per-stage report.

This keeps R1 honest: the tool never authors prose; it brackets the
human's authoring with correct setup and correct distribution.

## Where it lives

A single script `scripts/new_feature.py` with `scaffold` / `build`
subcommands (argparse), mirroring the existing
`scripts/project_features.py` and `scripts/sync_help_bundle.py`. Reasons:

- It composes those two scripts; living beside them keeps the trio
  discoverable.
- Repo-root resolution copies `project_features.py`'s
  `Path(__file__).resolve().parent.parent` idiom, so it works from any
  worktree.
- A CLI subcommand (`attune feature new`) is a thin future wrapper, not a
  v1 requirement (kept out of scope to avoid coupling to the CLI router).

## `scaffold` internals

1. **Validate the slug** (R5): kebab-case `^[a-z][a-z0-9-]*$`, and
   `content/features/<slug>.md` must not already exist, and `<slug>` must
   not already key `features:` in `.help/features.yaml`. Any violation →
   exit non-zero with the reason.
2. **Render the master from a template** (R2/R3). The template is a
   constant in the script (or a `content/features/_TEMPLATE.md` the script
   reads — preferred, so the canonical skeleton is itself reviewable and
   versioned). Substitute `feature`, `summary`, `tags`, `source_globs`.
   The `nav` block is fixed (`how-to`/`architecture`/`reference`). The
   body is the section headings the projector maps to kinds, each followed
   by a single `<!-- fill: … -->` placeholder line.
3. **Insert the manifest entry** (R2). Append under `features:` in
   `.help/features.yaml`:

   ```yaml
     <slug>:
       description: <summary>
       tags: [<tags>]
       status: manual
   ```

   Insertion is structural (parse YAML, add key, re-emit) to avoid
   brittle text splicing; preserve the file's comment header by appending
   the block rather than rewriting the whole file if the YAML round-trip
   would drop comments. (Decision: see decisions.md D2.)

## `build` internals

Run the four stages as subprocesses (or in-process where the module is
importable), capturing each stage's result:

| Stage | Command | Postcondition asserted |
|-------|---------|------------------------|
| project | `project_features.py <slug>` | N output files exist on disk |
| sync | `sync_help_bundle.py` | `sync_help_bundle.py --check` exits 0 |
| imports | `audit_doc_imports.py --paths <the 4 new docs pages>` | exit 0 |
| wiring | `audit_docs_wiring.py` | exit 0 |

R6: each stage's success is *verified*, not assumed from a zero exit
alone (e.g. project asserts the files exist; sync re-runs `--check`).

### The `attune_author` env resolution (R4)

`project_features.py` imports `attune_author`, absent from the worktree
venv. `build` resolves a usable interpreter in this order:

1. the current interpreter, if `import attune_author` succeeds;
2. an explicit `--python <path>` argument;
3. a discovered sibling main-checkout venv
   (`<repo-parent-or-main>/.venv/bin/python`) that imports
   `attune_author`;

and if none works, exits with the exact remedy ("install attune-author in
this venv, or pass `--python <main-venv-python>`") rather than a raw
`ModuleNotFoundError`. This turns the silent gotcha into an actionable
message.

## The template file

`content/features/_TEMPLATE.md` — the canonical skeleton, leading
underscore so it is ignored by feature enumeration (the projector and
manifest key on real slugs). It is the single place the section contract
lives; `scaffold` substitutes into it. Keeping it as a file (not a string
constant) means the skeleton is reviewed like any other content and stays
in step with what the projector expects.

## Testing

- **Unit:** `scaffold` on a throwaway slug writes a master whose
  frontmatter parses and whose sections match the template; rejects an
  existing slug; rejects a bad slug; inserts a well-formed yaml entry.
- **Integration / regression (R7 acceptance):** scaffold a throwaway
  feature, fill it from a fixture body, `build` it, and assert the
  produced `.help` + docs + bundle outputs are byte-identical to running
  `project_features.py` + `sync_help_bundle.py` by hand — proving the
  wrapper adds no drift. Clean up the throwaway artifacts in teardown.
- The throwaway slug (e.g. `_scaffolder_probe`) is `.gitignore`-safe or
  removed in teardown so it never lands in `features.yaml`.

## Rollout

1. Ship `scripts/new_feature.py` + `_TEMPLATE.md` + tests.
2. Update the lessons playbook entry to lead with
   `python scripts/new_feature.py scaffold|build` and demote the manual
   5 steps to "what it does under the hood" (R7).
3. (Future, out of scope) thin `attune feature new` CLI wrapper.
