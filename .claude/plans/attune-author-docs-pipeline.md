# attune-author: Project Docs Pipeline Extension

**Created:** 2026-04-23
**Source:** /brainstorm session

---

## Problem

attune-author has no concept of project-level docs. It knows about features
mapped to `.help/` templates for in-session RAG retrieval, but it has no
awareness of `docs/how-to/`, `docs/reference/`, or `mkdocs.yml`. Writing
guides like `context-management.md` or `telemetry-and-signals.md` requires
manually reading source, writing narrative prose, running a separate polish
step, and then hand-wiring the mkdocs nav. Nothing tracks whether those docs
go stale when the source changes.

---

## Goals

**Must-haves:**
- New template kinds: `how-to`, `cli-reference`, `architecture`, `tutorial` in attune-author
- `features.yaml` extended with `doc_kinds` and `doc_path` fields
- `attune-author generate` outputs to `docs/` with the same polish pipeline
- `attune-author status` covers both `.help/` and `docs/` docs in one view
- Staleness detection for `docs/` files tied to the same source hash mechanism
- `attune-author audit` scans `src/` for modules not yet in `features.yaml`
- `attune-author bulk-generate` generates all features missing their `doc_kinds`
- mkdocs.yml nav auto-updated when new docs are generated

**Nice-to-haves:**
- `attune-author migrate` to retroactively register the docs we already wrote
  (detect existing `docs/` files, infer source mappings, add to features.yaml)
- Dry-run mode for bulk-generate that shows what would be generated without
  writing files

---

## End State

A developer adding a new module `src/attune/foo/` registers it in
`features.yaml` with:

```yaml
- id: foo
  name: Foo Module
  sources:
    - src/attune/foo/
  doc_kinds:
    - how-to
    - architecture
  doc_path: docs/how-to/foo.md
  arch_path: docs/architecture/foo-architecture.md
  doc_nav_section: "How-to > Advanced"
```

Running `attune-author generate foo` reads the source, produces a complete
draft at `docs/how-to/foo.md`, runs the LLM polish step, and inserts the doc
into the `mkdocs.yml` nav under the specified section. `attune-author status`
shows both `.help/` and `docs/` freshness for every feature. When
`src/attune/foo/` changes, `attune-author status` flags `foo` as stale and
`attune-author update foo` regenerates.

---

## Approach

### Phase 1 — Schema and template kinds (attune-author package)

1. Extend `features.yaml` schema:
   - Add `doc_kinds: list[str]` — valid values: `how-to`, `cli-reference`,
     `architecture` (extensible)
   - Add `doc_path: str` — output path for primary doc in `docs/`
   - Add `doc_nav_section: str` — mkdocs.yml nav section to insert under
   - Keep all existing `.help/` fields unchanged

2. Add 4 new template kind definitions in attune-author's template registry,
   bringing the total from 11 to 15 kinds:

   - `how-to` — task-oriented guide. Assumes competence, solves a specific
     problem without hand-holding. Sections: why/when to use, quick start,
     core API, configuration, integration patterns, see-also.
   - `tutorial` — learning-oriented guide. Leads a beginner through building
     something end-to-end; explains *why* at each step, not just *what*.
     Sections: what you'll build, prerequisites, step-by-step walkthrough,
     what you learned, next steps. Generation prompt is deliberately different
     from `how-to` — assumes no prior knowledge, includes more explanation.
   - `cli-reference` — per-command docs: description, usage, options table,
     output examples, related commands.
   - `architecture` — module overview: purpose, key classes, data flow
     diagram (ASCII), design decisions, extension points.

   **how-to vs tutorial distinction:** a how-to says "here's the recipe for X";
   a tutorial says "let's build X together so you understand why it works."
   The same source module may generate both: `tutorial` for first-time
   onboarding, `how-to` for day-to-day reference. They output to different
   paths (`docs/tutorials/` vs `docs/how-to/`) and have separate nav sections.

3. Write generation prompts for each new kind. Key difference from `.help/`
   prompts: these need narrative prose and code examples, not keyword-dense
   retrieval text. The prompt should instruct the LLM to:
   - Read the provided source files
   - Follow the template structure for the kind
   - Include working code examples from actual source
   - Add "See Also" cross-links to related docs

### Phase 2 — Staleness tracking for docs/

4. Source hash tracking for `docs/` files: append an HTML comment to the
   bottom of generated files (invisible to mkdocs, parseable by attune-author):
   ```html
   <!-- attune-generated: source_hash=abc123 feature=foo kind=how-to generated_at=2026-04-23 -->
   ```
   This keeps generated docs clean (no YAML frontmatter pollution) while
   preserving the staleness signal.

5. Extend `check_staleness()` / `load_manifest()` to read both `.help/`
   frontmatter hashes and `docs/` HTML comment hashes in one pass.

6. `attune-author status` output gains a "Project Docs" section alongside
   the existing "Help Templates" section.

### Phase 3 — Generation commands

7. `attune-author generate <feature> [--kind how-to|tutorial|cli-reference|architecture]`
   - Reads sources from features.yaml
   - Calls generation prompt for the specified kind
   - Runs polish pipeline
   - Writes to `doc_path` or `arch_path`
   - Updates mkdocs.yml nav (insert if not present; skip if already wired)

8. `attune-author audit`
   - Scans `src/attune/` directory tree
   - Compares module directories against features registered in features.yaml
   - Reports: registered (has .help/ + docs/), partial (has .help/ only),
     unregistered (not in features.yaml at all)
   - Outputs a table with recommended `doc_kinds` based on module size/type

9. `attune-author bulk-generate [--kind how-to] [--dry-run]`
   - Iterates all features that have `doc_kinds` set but missing their output
     file (or are stale)
   - Generates each in sequence with the same pipeline as single-feature generate
   - `--dry-run` shows what would be generated without writing

### Phase 4 — mkdocs nav wiring

10. Nav insertion logic:
    - Parse mkdocs.yml nav as a Python structure
    - Locate the section named `doc_nav_section` from features.yaml entry
    - Insert `{doc_title}: {doc_path}` if not already present
    - Write back mkdocs.yml (preserving comments, which requires round-trip-safe
      YAML handling — use `ruamel.yaml` not standard `yaml`)

---

## Decisions Made

- **Staleness logic lives in attune-help** (resolved). `check_staleness` and
  the hash-reading logic will be extended in `attune-help` to understand the
  new HTML comment format in `docs/` files. `attune-author` calls into
  `attune-help` as it already does for `.help/` staleness. Requires a
  coordinated release of both packages — planned for the weekend.

## Open Questions

- **Single vs. multi-file features**: Some features (like CLI reference) would
  generate *multiple* docs (one per command group). Does each command group get
  its own features.yaml entry, or does one feature generate multiple output files?
  Recommendation: one entry per logical feature, `doc_kinds` can include a list of
  paths for multi-file output.

- **Retroactive migration**: The docs we already wrote (`context-management.md`,
  `telemetry-and-signals.md`, etc.) should be registered so they appear in
  `attune-author status`. A one-time `attune-author migrate` command could scan
  `docs/` for unregistered files and prompt to add them. Out of scope for Phase 1.

- **ruamel.yaml for mkdocs**: Standard `yaml.dump` destroys mkdocs.yml formatting
  and comments. Phase 4 should use `ruamel.yaml` (comment-preserving). Check if
  attune-author already has it as a dep.

---

## Next Steps

- [ ] Extend `features.yaml` schema in attune-author (add `doc_kinds`, `doc_path`,
      `doc_nav_section` fields with validation)
- [ ] Write template kind definitions for `how-to`, `cli-reference`, `architecture`
- [ ] Write generation prompts for the 4 new kinds
- [ ] Implement HTML comment staleness tracking for `docs/` files
- [ ] Extend `check_staleness()` to handle both tracking formats
- [ ] Implement `attune-author generate` output to `docs/`
- [ ] Implement `attune-author audit` module scan
- [ ] Implement `attune-author bulk-generate`
- [ ] Implement mkdocs nav wiring (Phase 4, depends on ruamel.yaml)
- [ ] Register existing `docs/` files retroactively (migration, out of scope for v1)
