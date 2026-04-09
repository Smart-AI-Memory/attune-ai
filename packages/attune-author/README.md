# attune-author

Documentation authoring and maintenance for the attune
ecosystem.

```
attune-help (reader) --> attune-author (authoring) --> attune-ai (full workflows)
```

## Installation

```bash
pip install attune-author           # Core (templates, staleness)
pip install 'attune-author[ai]'     # + AI-powered doc generation
pip install 'attune-author[rich]'   # + Rich CLI formatting
```

## Quick Start

```bash
# Initialize help system in your project
attune-author init

# Check which templates are stale
attune-author status

# Generate templates for a feature
attune-author generate security-audit

# Regenerate all stale templates
attune-author regenerate
```

## Python API

```python
from attune_author import load_manifest, check_staleness

# Load your project's feature manifest
manifest = load_manifest(".help/features.yaml")

# Check which features have stale documentation
report = check_staleness(".help/")
for feature in report.stale:
    print(f"  {feature.name}: {feature.reason}")
```

## Features

- **Manifest parsing** -- Load and validate
  `.help/features.yaml`
- **Staleness detection** -- Track source hash drift,
  detect outdated templates
- **Template generation** -- Jinja2-based concept, task,
  and reference templates
- **LLM polish** -- Optional AI pass to improve generated
  content (requires `[ai]`)
- **Bulk maintenance** -- Regenerate stale templates in
  one command
- **API reference** -- Generate docs from Python source
  (requires `[ai]`)
- **CLI** -- `attune-author` command for all operations

## Ecosystem

| Package | Role | Deps |
|---------|------|------|
| `attune-help` | Read and render help content | 1 (frontmatter) |
| `attune-author` | Author, generate, maintain docs | 4 (jinja2, frontmatter, pyyaml, attune-help) |
| `attune-ai` | Full developer workflow OS | Many |

## License

Apache 2.0
