# T2 — Build the deterministic projector

**Status:** ready to execute · **Lands in:** attune-author (module +
tests) + attune-ai (driver script) · **Decisions:** D6, D7, **D8**
(projector home), DD1–DD5 in [design.md](design.md)

> Execute this from an **attune-author-rooted session** for the module
> + tests (the attune-ai worktree path-guard blocks cross-repo
> Write/Edit). The driver script lands in attune-ai and can be written
> from either session.

---

## Objective

Build a deterministic projector that reads a single-source master file
(`content/features/<feature>.md` in the consumer repo) and renders it
to the 10 non-faq `.help` kinds + the 4 `docs/` feature pages — no
LLM, no AST-render, no meta-templates. Prove it on `spec-engine`
(master file already authored + merged in attune-ai #960).

---

## Context (grounded in the real code, 2026-06-21)

```xml
<context>
  <existing-api path="attune_author/generator.py">
    generate_feature_templates(feature, help_dir, project_root, *,
      depths=None, overwrite=False, use_rag=True) — the LLM generator.
    Phase 1 renders meta_templates/*.j2 from AST-extracted vars
    (public_classes, module_docstrings, ...); Phase 2 LLM-polishes.
    REUSE the frontmatter/footer helpers ONLY:
      compute_scaffold_hash(content) -> str
      _inject_scaffold_hash / _read_scaffold_hash / _refresh_metadata_in_place
      _PROJECT_DOC_NAMES = (how-to, tutorial, cli-reference, architecture)
        — these route to docs/ with an HTML-comment footer; all other
        kinds route to .help/templates/<feature>/<kind>.md with YAML
        frontmatter.
    DO NOT reuse meta_templates/*.j2 — they are AST-keyed and assume
    an LLM polish pass; the projector renders hand-authored prose.
  </existing-api>
  <reuse path="attune_author/fact_check/">
    python_refs, cli_refs, md_links, import_repair (DD4/R3). Run on the
    master file; warn-only for the pilot.
  </reuse>
  <input path="content/features/spec-engine.md (in consumer repo)">
    YAML frontmatter (feature, summary, tags, source_globs, nav;
    optional cli:) + fixed H2 sections: Overview, Concepts, Quickstart,
    Tasks, Reference, Comparison, Failure modes, FAQ seeds,
    Notes &amp; tips, Design &amp; extension. A missing section = skip
    its dependent outputs, never an error.
  </input>
  <output-contracts>
    .help kind file frontmatter (must match what attune-help's
    HelpEngine reads today — DD2/R4, zero consumer change):
      type, name (=&lt;feature&gt;-&lt;kind&gt;), feature, depth (=kind),
      generated_at, source_hash, status: generated
    docs page footer (project-doc kinds):
      &lt;!-- attune-generated: source_hash=… feature=&lt;f&gt; kind=&lt;k&gt; generated_at=… --&gt;
  </output-contracts>
  <invocation>
    attune-author is a library; the consumer drives it (see attune-ai
    scripts/regenerate_help_templates.py). The projector follows the
    same shape: a library fn + a new attune-ai driver script.
  </invocation>
</context>
```

---

## Projection map (the contract — from design.md, faq excluded per D7)

```python
# .help kind -> source sections (in order)
HELP_KIND_SECTIONS = {
    "concept":         ["Overview", "Concepts"],
    "reference":       ["Reference"],
    "task":            ["Tasks"],
    "quickstart":      ["Quickstart"],
    "comparison":      ["Comparison"],
    "error":           ["Failure modes"],
    "troubleshooting": ["Failure modes"],
    "warning":         ["Failure modes"],
    "note":            ["Overview", "Concepts", "Notes & tips"],
    "tip":             ["Notes & tips"],
    # "faq" intentionally excluded — D7 (Generator unbuilt)
}

# docs/ page (project-doc kind) -> source sections
DOCS_PAGE_SECTIONS = {
    "how-to":       ["Quickstart", "Tasks", "Reference"],
    "tutorial":     ["Tasks"],                    # see Risk: tutorial
    "architecture": ["Overview", "Concepts", "Design & extension"],
    "reference":    ["Reference"],                # python-API ref; CLI block only if cli: present
}
```

---

## Files to create

```xml
<files-to-create>
  <file path="attune_author/src/attune_author/projector.py">
    @dataclass MasterFile: feature:str, frontmatter:dict,
      sections:dict[str,str]  # H2 title -> body markdown

    parse_master_file(path: Path) -> MasterFile
      - split YAML frontmatter; split body on '## ' H2 headings into an
        ordered {title: body} map. Tolerate missing sections.

    project_feature(master_path, project_root, help_dir, *,
        skip_kinds=("faq",), dry_run=False) -> ProjectionResult
      - parse; for each HELP_KIND_SECTIONS entry not in skip_kinds,
        concatenate the named sections, wrap with .help frontmatter
        (source_hash via compute_scaffold_hash over the master file),
        write .help/templates/<feature>/<kind>.md
      - for each DOCS_PAGE_SECTIONS entry, concatenate sections, wrap
        with the docs HTML-comment footer, write docs/<kind>/<feature>.md
        (cli-reference kind -> docs/reference/<feature>.md)
      - return ProjectionResult(written: list[Path], skipped: list[str],
        warnings: list[str])

    validate_master_file(master_path, project_root) -> list[Finding]
      - run fact_check python_refs/cli_refs/md_links + import_repair;
        warn-only for the pilot.
  </file>
  <file path="attune_author/tests/unit/test_projector.py">
    - parse_master_file on content/features/spec-engine.md yields all
      10 sections + frontmatter feature == "spec-engine".
    - project_feature(dry_run=True) plans exactly 10 .help kinds (no
      faq) + 4 docs pages.
    - each planned .help file's frontmatter has the 7 required keys and
      depth == kind; docs pages carry the footer.
    - a master file missing a section skips only its dependent outputs.
  </file>
  <file path="scripts/project_features.py (in attune-ai)">
    CLI: `python scripts/project_features.py <feature> [--dry-run]`.
    Resolves project_root = repo root, help_dir = .help/, master =
    content/features/<feature>.md; calls projector.project_feature;
    prints written/skipped/warnings. Mirrors
    scripts/regenerate_help_templates.py's project-root resolution.
  </file>
</files-to-create>
```

---

## Validation (acceptance for T2)

```xml
<validation>
  <check>python scripts/project_features.py spec-engine writes 10 .help kinds + how-to/tutorial/architecture/reference docs pages; faq NOT written.</check>
  <check>attune-help HelpEngine(template_dir=".help/templates").lookup("spec-engine") serves the projected concept/task/reference unchanged — no consumer code change (DD2/R4).</check>
  <check>mkdocs build is clean on the 4 projected docs pages.</check>
  <check>fact_check on content/features/spec-engine.md is green (or warnings only); import_repair finds nothing to fix (T1 already verified refs).</check>
  <check>diff projected .help vs the current LLM-generated .help/spec-engine/* — the hand-authored content replaces the fiction (esp. no spec-engine-CLI, async execute_with_approval, property access, HTML-comment state); this is the win, not a regression.</check>
</validation>
```

---

## Risks

```xml
<risks>
  <risk severity="medium">Tutorial projection. design.md flags tutorial may resist pure projection. Pilot slice = DOCS_PAGE_SECTIONS["tutorial"] = ["Tasks"], rendering the "Run a plan programmatically" task as the guided narrative. If the result reads thin vs the hand-authored tutorial, keep tutorial hand-authored per-feature and drop it from DOCS_PAGE_SECTIONS (record as a decision). Decide by inspecting the rendered page, not in advance.</risk>
  <risk severity="low">.help frontmatter drift. If the projected frontmatter omits a key HelpEngine expects, lookup breaks silently. Mitigation: copy the exact key set from an existing .help/spec-engine/*.md and assert it in test_projector.py.</risk>
  <risk severity="low">Per-output formatting. One section may need terser vs narrative rendering across outputs (e.g. Tasks -> terse .help/task vs how-to#core-api). Start with straight section concatenation; add a light per-output transform only where the rendered output is visibly wrong.</risk>
  <risk severity="medium">DD5 ordering. Do NOT remove spec-engine's 10 projected kinds from .help/features.yaml until AFTER the projector output is verified to serve correctly (pilot step 6). Removing early loses the .help content if the projector has a gap.</risk>
</risks>
```

---

## After T2 (pilot steps 4–8, not this task)

4. Resolve fact-check/grounding findings. 5. Verify help-serve +
`mkdocs build`. 6. Remove spec-engine's 10 projected kinds from the
generator manifest (DD5). 7. Repeat for `models` (exercises the `cli:`
block + `cli_refs`). 8. Write the R7 rollout playbook. FAQ Generator
(FG1) and Failure-modes sourcing (FM1) remain separate follow-ups.
