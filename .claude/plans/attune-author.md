# attune-author: Documentation Authoring Library

**Status:** Draft
**Created:** 2026-04-06
**Owner:** Patrick Roebuck

## Vision

`attune-author` is a focused documentation authoring and
maintenance library for the attune ecosystem. It sits between
`attune-help` (lightweight reader) and `attune-ai` (full AI
Workflow-harness), providing everything needed to author, generate,
and maintain documentation without the overhead of security
audits, code review, test generation, etc.

```
attune-help (reader)  -->  attune-author (authoring)  -->  attune-ai (full workflows)
     0 deps               medium deps                      all deps
     read/render           write/generate/maintain          dev lifecycle
```

## Target Audience

- Technical writers who need AI-assisted doc generation
- Developers who want help authoring without full attune-ai
- Teams using `.help` systems who need authoring tooling
- Plugin authors who need doc-gen for their plugins

## Package Details

- **Name:** `attune-author`
- **PyPI:** `attune-author`
- **Python:** >=3.10
- **License:** Apache 2.0
- **Location:** `packages/attune-author/`

## Dependencies

Core (minimal):

- `jinja2>=3.1.0` (template rendering)
- `python-frontmatter>=1.0.0` (markdown metadata)
- `pyyaml>=6.0` (features.yaml parsing)
- `attune-help>=0.3.0` (reader/renderer)

Optional extras:

- `[ai]` — `claude-agent-sdk` (AI-powered doc generation)
- `[rich]` — `rich>=13.0.0` (CLI formatting)

## Architecture

```
packages/attune-author/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── attune_author/
│       ├── __init__.py           # Public API, version
│       ├── manifest.py           # features.yaml parsing
│       ├── staleness.py          # Source hash, drift detection
│       ├── generator.py          # Jinja2 template generation
│       ├── polish.py             # LLM polish pass (optional)
│       ├── preamble.py           # Contextual preambles
│       ├── maintenance.py        # Bulk maintenance operations
│       ├── bootstrap.py          # Project help initialization
│       ├── doc_gen/              # Multi-stage doc generation
│       │   ├── __init__.py
│       │   ├── outline.py        # Outline planning stage
│       │   ├── writer.py         # Content writing stage
│       │   ├── reviewer.py       # Polish/review stage
│       │   └── config.py         # Generation config
│       ├── api_reference.py      # API reference generation
│       ├── meta_templates/       # Default Jinja2 templates
│       │   ├── concept.md.j2
│       │   ├── task.md.j2
│       │   └── reference.md.j2
│       └── cli.py                # CLI entry point
└── tests/
    └── ...
```

## What Gets Extracted from attune-ai

| Source | Destination | Notes |
|--------|-------------|-------|
| `src/attune/help/manifest.py` | `attune_author/manifest.py` | Feature YAML parsing |
| `src/attune/help/staleness.py` | `attune_author/staleness.py` | Source hash, drift |
| `src/attune/help/generator.py` | `attune_author/generator.py` | Jinja2 template gen |
| `src/attune/help/polish.py` | `attune_author/polish.py` | LLM polish pass |
| `src/attune/help/preamble.py` | `attune_author/preamble.py` | Contextual preambles |
| `src/attune/help/maintenance.py` | `attune_author/maintenance.py` | Bulk operations |
| `src/attune/help/bootstrap.py` | `attune_author/bootstrap.py` | Project init |
| `src/attune/help/meta_templates/` | `attune_author/meta_templates/` | Jinja2 defaults |
| `src/attune/workflows/document_gen/` | `attune_author/doc_gen/` | 3-stage pipeline |

## What Stays in attune-ai

- MCP server handlers (will import from attune-author)
- Plugin skills (`/coach`, `/doc-gen`)
- `documentation_orchestrator.py` (scout + prioritize)
- `doc_audit/` workflow (auditing, not authoring)
- `help_maintenance.py` workflow (pre-commit hook)
- Session, feedback, progression modules (runtime UX)

## Public API

```python
from attune_author import (
    # Manifest
    load_manifest,
    Feature,
    Manifest,

    # Staleness
    compute_source_hash,
    check_staleness,
    StalenessReport,

    # Generation
    generate_templates,
    generate_feature,

    # Bootstrap
    init_help,

    # Maintenance
    regenerate_stale,
    bulk_generate,

    # Doc generation (optional, requires [ai])
    generate_docs,
    generate_api_reference,
)
```

## CLI

```bash
attune-author init                    # Bootstrap .help/ in project
attune-author status                  # Show staleness report
attune-author generate <feature>      # Generate templates for feature
attune-author regenerate              # Regenerate stale templates
attune-author docs <path>             # Generate docs (requires [ai])
attune-author api-ref <module>        # Generate API reference
```

---

## Tasks

<task id="1" name="scaffold-package">
  <objective>
    Create the package directory structure, pyproject.toml,
    README, and __init__.py with version and public API.
  </objective>

  <files-to-create>
    <file path="packages/attune-author/pyproject.toml">
      Build config, dependencies, optional extras, CLI
      entry point, classifiers
    </file>
    <file path="packages/attune-author/README.md">
      Package description, installation, quick start,
      ecosystem diagram
    </file>
    <file path="packages/attune-author/LICENSE">
      Apache 2.0 (copy from repo root)
    </file>
    <file path="packages/attune-author/src/attune_author/__init__.py">
      Version, public API exports, __all__
    </file>
  </files-to-create>

  <validation>
    <check>pyproject.toml is valid TOML</check>
    <check>Package can be installed with pip install -e .</check>
  </validation>
</task>

<task id="2" name="extract-manifest">
  <objective>
    Extract features.yaml parsing from attune.help.manifest
    into attune_author.manifest, adapting imports and removing
    attune-ai-specific dependencies.
  </objective>

  <context>
    <existing-code path="src/attune/help/manifest.py">
      Feature dataclass, load_manifest(), YAML parsing
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/src/attune_author/manifest.py">
      Feature and Manifest dataclasses, load_manifest(),
      save_manifest() — standalone, no attune-ai imports
    </file>
  </files-to-create>

  <validation>
    <check>load_manifest() parses .help/features.yaml correctly</check>
    <check>No imports from attune.* (only attune_help if needed)</check>
  </validation>
</task>

<task id="3" name="extract-staleness">
  <objective>
    Extract staleness detection from attune.help.staleness
    into attune_author.staleness. This provides source hash
    computation, drift detection, and staleness reporting.
  </objective>

  <context>
    <existing-code path="src/attune/help/staleness.py">
      compute_source_hash(), _read_frontmatter_value(),
      check_staleness(), StalenessReport
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/src/attune_author/staleness.py">
      All staleness functions, standalone
    </file>
  </files-to-create>

  <validation>
    <check>compute_source_hash() returns consistent hashes</check>
    <check>check_staleness() detects stale templates</check>
  </validation>
</task>

<task id="4" name="extract-generator">
  <objective>
    Extract Jinja2 template generation from
    attune.help.generator into attune_author.generator.
    Include meta templates as package data.
  </objective>

  <context>
    <existing-code path="src/attune/help/generator.py">
      _build_jinja_env(), generate_feature(), AST parsing,
      Jinja2 meta template resolution
    </existing-code>
    <existing-code path="src/attune/help/meta_templates/">
      concept.md.j2, task.md.j2, reference.md.j2
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/src/attune_author/generator.py">
      Template generation with Jinja2, AST analysis
    </file>
    <file path="packages/attune-author/src/attune_author/meta_templates/concept.md.j2">
      Copy from src/attune/help/meta_templates/
    </file>
    <file path="packages/attune-author/src/attune_author/meta_templates/task.md.j2">
      Copy from src/attune/help/meta_templates/
    </file>
    <file path="packages/attune-author/src/attune_author/meta_templates/reference.md.j2">
      Copy from src/attune/help/meta_templates/
    </file>
  </files-to-create>

  <validation>
    <check>generate_feature() produces valid markdown templates</check>
    <check>Meta templates resolve correctly from package data</check>
  </validation>
</task>

<task id="5" name="extract-polish-preamble">
  <objective>
    Extract the LLM polish pass and contextual preamble
    generation into attune_author.polish and
    attune_author.preamble.
  </objective>

  <context>
    <existing-code path="src/attune/help/polish.py">
      Optional LLM-based quality improvement pass
    </existing-code>
    <existing-code path="src/attune/help/preamble.py">
      Context-aware preamble generation for templates
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/src/attune_author/polish.py">
      LLM polish pass, guarded behind optional [ai] extra
    </file>
    <file path="packages/attune-author/src/attune_author/preamble.py">
      Contextual preamble builder
    </file>
  </files-to-create>

  <validation>
    <check>polish module importable without AI deps installed</check>
    <check>preamble generation works standalone</check>
  </validation>
</task>

<task id="6" name="extract-bootstrap-maintenance">
  <objective>
    Extract project bootstrapping and bulk maintenance
    operations into attune_author.bootstrap and
    attune_author.maintenance.
  </objective>

  <context>
    <existing-code path="src/attune/help/bootstrap.py">
      init_help() — creates .help/ structure in a project
    </existing-code>
    <existing-code path="src/attune/help/maintenance.py">
      Bulk regeneration, stale template refresh
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/src/attune_author/bootstrap.py">
      Project help initialization
    </file>
    <file path="packages/attune-author/src/attune_author/maintenance.py">
      Bulk maintenance operations
    </file>
  </files-to-create>

  <validation>
    <check>init_help() creates valid .help/ structure</check>
    <check>regenerate_stale() finds and updates stale templates</check>
  </validation>
</task>

<task id="7" name="extract-doc-gen-pipeline">
  <objective>
    Extract the 3-stage document generation pipeline
    (outline, write, polish) from attune.workflows.document_gen
    into attune_author.doc_gen. Adapt to work standalone
    without BaseWorkflow.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/document_gen/">
      workflow.py (orchestrator), outline_stage.py,
      write_stage.py, polish_stage.py, config.py,
      api_reference.py, chunked_generation.py
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/src/attune_author/doc_gen/__init__.py">
      Public API for doc generation
    </file>
    <file path="packages/attune-author/src/attune_author/doc_gen/outline.py">
      Outline planning stage
    </file>
    <file path="packages/attune-author/src/attune_author/doc_gen/writer.py">
      Content writing stage
    </file>
    <file path="packages/attune-author/src/attune_author/doc_gen/reviewer.py">
      Polish/review stage
    </file>
    <file path="packages/attune-author/src/attune_author/doc_gen/config.py">
      Generation configuration
    </file>
    <file path="packages/attune-author/src/attune_author/api_reference.py">
      API reference generation from source
    </file>
  </files-to-create>

  <validation>
    <check>Doc gen pipeline works end-to-end with [ai] extra</check>
    <check>Config module importable without AI deps</check>
  </validation>

  <risks>
    <risk severity="medium">
      document_gen depends on BaseWorkflow and AgentSDK
      adapter — need to refactor to standalone pipeline
      pattern without those base classes
    </risk>
  </risks>
</task>

<task id="8" name="build-cli">
  <objective>
    Create a CLI entry point for attune-author using typer,
    exposing init, status, generate, regenerate, docs, and
    api-ref commands.
  </objective>

  <files-to-create>
    <file path="packages/attune-author/src/attune_author/cli.py">
      Typer CLI with subcommands: init, status, generate,
      regenerate, docs, api-ref
    </file>
  </files-to-create>

  <validation>
    <check>attune-author --help shows all commands</check>
    <check>attune-author init creates .help/ structure</check>
    <check>attune-author status shows staleness report</check>
  </validation>
</task>

<task id="9" name="write-tests">
  <objective>
    Write unit tests for all extracted modules. Target 80%+
    coverage. Test both with and without optional AI deps.
  </objective>

  <files-to-create>
    <file path="packages/attune-author/tests/conftest.py">
      Shared fixtures
    </file>
    <file path="packages/attune-author/tests/test_manifest.py">
      Manifest parsing tests
    </file>
    <file path="packages/attune-author/tests/test_staleness.py">
      Staleness detection tests
    </file>
    <file path="packages/attune-author/tests/test_generator.py">
      Template generation tests
    </file>
    <file path="packages/attune-author/tests/test_bootstrap.py">
      Bootstrap/init tests
    </file>
    <file path="packages/attune-author/tests/test_maintenance.py">
      Maintenance operations tests
    </file>
    <file path="packages/attune-author/tests/test_cli.py">
      CLI integration tests
    </file>
  </files-to-create>

  <validation>
    <check>pytest passes with 80%+ coverage</check>
    <check>Tests pass without optional [ai] extra</check>
  </validation>
</task>

<task id="10" name="wire-attune-ai-imports">
  <objective>
    Update attune-ai to depend on attune-author and re-export
    from it, so existing attune-ai users see no breaking
    changes. The help/ modules in attune-ai become thin
    wrappers.
  </objective>

  <files-to-modify>
    <file path="pyproject.toml">
      <change location="dependencies">
        Add attune-author>=0.1.0 to dependencies
      </change>
    </file>
    <file path="src/attune/help/__init__.py">
      <change location="module">
        Re-export from attune_author for backward compat
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Existing attune-ai imports still work</check>
    <check>MCP help handlers still function</check>
    <check>Plugin /coach skill still works</check>
  </validation>

  <risks>
    <risk severity="medium">
      Circular dependency risk if attune-author imports from
      attune-ai. Must ensure clean dependency direction:
      attune-author depends on attune-help only, never
      attune-ai.
    </risk>
  </risks>
</task>
