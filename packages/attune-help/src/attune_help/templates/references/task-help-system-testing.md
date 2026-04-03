---
type: reference
subtype: tabular
name: task-help-system-testing
tags: [testing, help-system, quality, validation]
source: developer-guidance
---

# Reference: Help system test patterns

Complete reference for testing every layer of the
attune-help system: template validation, progressive
depth, precursor warnings, cross-links, renderers,
performance, and CI integration.

## Template validation

### Frontmatter schema

Every template must have these frontmatter fields.
Validation should reject files missing any of them.

| Field | Type | Required | Allowed values |
|---|---|---|---|
| `type` | string | Yes | concept, task, reference, quickstart, error, warning, tip, faq, note, troubleshooting, comparison |
| `name` | string | Yes | Kebab-case slug matching filename |
| `tags` | list | Yes | At least one tag |
| `source` | string | Yes | File path or `developer-guidance` |
| `subtype` | string | No | tabular, procedural, free-form |
| `category` | string | No | tool, skill, workflow |
| `confidence` | string | No | high, medium, low |

### Required sections per type

Each template type has expected sections. Missing
sections are not fatal but should produce warnings.

| Type | Required sections | Optional sections |
|---|---|---|
| concept | What, Why | How, Example, Want to learn more?, Related Topics |
| task | Prerequisites, Steps or named step sections | Verification checklist, Want to learn more?, Related Topics |
| reference | At least one table or structured section | Usage, Common problems, Want to learn more?, Related Topics |
| quickstart | Numbered step sections (Step 1, Step 2, ...) | Quick additions, Want to learn more?, Related Topics |
| error | Signature, Root Cause, Resolution | Affected Files, Example, Related Topics |
| warning | Condition, Risk, Mitigation | Example, Related Topics |
| tip | Recommendation | Why, Example, Related Topics |

### Validation test pattern

```python
import frontmatter as fm
from pathlib import Path

VALID_TYPES = {
    "concept", "task", "reference", "quickstart",
    "error", "warning", "tip", "faq", "note",
    "troubleshooting", "comparison",
}

SECTION_EXPECTATIONS = {
    "concept": ["What", "Why"],
    "task": [],  # Flexible — steps may use custom names
    "reference": [],
    "quickstart": [],
    "error": ["Signature", "Root Cause", "Resolution"],
    "warning": ["Condition", "Risk", "Mitigation"],
    "tip": ["Recommendation"],
}


def validate_template(filepath: Path) -> list[str]:
    """Return list of validation issues for a template."""
    issues: list[str] = []
    post = fm.load(str(filepath))

    # Required frontmatter
    if post.get("type") not in VALID_TYPES:
        issues.append(f"invalid type: {post.get('type')}")
    if not post.get("name"):
        issues.append("missing name")
    if not post.get("tags"):
        issues.append("missing tags")
    if not post.get("source"):
        issues.append("missing source")

    # Name should match filename
    expected_name = filepath.stem
    if post.get("name") != expected_name:
        issues.append(
            f"name '{post.get('name')}' != "
            f"filename '{expected_name}'"
        )

    # Check expected sections
    content = post.content
    headings = [
        line[3:].strip()
        for line in content.split("\n")
        if line.startswith("## ")
    ]
    ttype = post.get("type", "")
    for section in SECTION_EXPECTATIONS.get(ttype, []):
        if section not in headings:
            issues.append(f"missing section: {section}")

    return issues
```

## Progressive depth testing

### Three-call cycle

The core behavior: same topic, three calls, three
different depth levels.

| Call | Expected depth | Expected type | Depth prompt suffix |
|---|---|---|---|
| 1st | 0 | concept | `(concept view -- say "tell me more" ...)` |
| 2nd | 1 | task | `(task view -- say "tell me more" ...)` |
| 3rd | 2 | reference | (none) |

### Topic reset

| Action | Expected depth | Why |
|---|---|---|
| Call topic A | 0 | First access |
| Call topic A again | 1 | Same topic, advance |
| Call topic B | 0 | Different topic, reset |
| Call topic A again | 0 | Topic changed, restart from 0 |

### Depth ceiling

Calling the same topic more than three times should stay
at depth 2 (reference level). It must never exceed 2 or
wrap around to 0.

```python
def test_depth_ceiling():
    """Depth stays at 2 after three calls."""
    engine = HelpEngine(
        storage=MemoryStorage(), renderer="plain"
    )
    for _ in range(5):
        r = engine.lookup_raw("security-audit")
    assert r is not None
    assert r.metadata["depth_level"] == 2
```

### TTL and session expiry

If session storage supports TTL (time-to-live), depth
should reset after the TTL expires. Test with a mock
clock or short TTL.

```python
def test_depth_resets_after_session_expiry():
    """Expired session resets depth to 0."""
    storage = MemoryStorage()
    engine = HelpEngine(
        storage=storage, renderer="plain"
    )

    engine.lookup_raw("security-audit")  # depth 0
    engine.lookup_raw("security-audit")  # depth 1

    # Simulate session expiry
    storage.clear_session("default")

    r = engine.lookup_raw("security-audit")
    assert r is not None
    assert r.metadata["depth_level"] == 0
```

## Precursor warning testing

### Extension map coverage

Every extension in the engine's `ext_map` should be
tested. Missing coverage means a file type can silently
lose its warnings.

| Extension | Expected tags | Example file | Expected result |
|---|---|---|---|
| `.py` | python, imports, testing, error-handling | `src/main.py` | At least 1 warning |
| `.yml` | ci, github-actions | `ci.yml` | At least 1 warning |
| `.yaml` | ci, github-actions | `config.yaml` | At least 1 warning |
| `.json` | packaging | `package.json` | 0+ warnings (depends on templates) |
| `.toml` | packaging, python, publishing | `pyproject.toml` | At least 1 warning |
| `.md` | claude-code | `SKILL.md` | 0+ warnings |
| `.sql` | database, migrations | `001_init.sql` | 0+ warnings |
| `.env` | config, secrets | `.env` | At least 1 warning |

### Filename map coverage

| Filename | Extra tags | Expected result |
|---|---|---|
| `pyproject.toml` | deps, publishing, packaging | At least 1 warning |
| `models.py` | database | At least 1 warning |
| `alembic.ini` | database, migrations | At least 1 warning |
| `dockerfile` | ci, cd | 0+ warnings |
| `.gitignore` | git | 0+ warnings |

### Precursor test pattern

```python
import pytest

EXTENSION_CASES = [
    ("app.py", True),
    ("ci.yml", True),
    ("pyproject.toml", True),
    ("data.xyz", False),
    ("image.png", False),
]


@pytest.mark.parametrize("filename,expect_warnings", EXTENSION_CASES)
def test_precursor_by_extension(filename, expect_warnings):
    """Extension map produces expected warning presence."""
    engine = HelpEngine(
        storage=MemoryStorage(), renderer="plain"
    )
    warnings = engine.precursor_warnings(filename)
    if expect_warnings:
        assert len(warnings) > 0, (
            f"Expected warnings for {filename}"
        )
    else:
        assert len(warnings) == 0, (
            f"Unexpected warnings for {filename}"
        )
```

## Renderer testing

### Expected output patterns

| Renderer | Returns | Contains title? | Contains frontmatter? | Contains Rich markup? |
|---|---|---|---|---|
| plain | Raw markdown body | Yes (h1 heading) | No | No |
| claude_code | Condensed markdown | Yes (bold title) | No | No |
| cli | Rich-formatted or plain fallback | Yes (panel title) | No | Yes (if Rich installed) |
| marketplace | YAML frontmatter + markdown | Yes (in frontmatter) | Yes | No |

### Renderer contract test

```python
from attune_help.templates import (
    AudienceProfile, populate,
)
from attune_help.transformers import (
    render_claude_code, render_cli, render_marketplace,
)

RENDERERS = {
    "plain": lambda t: t.body,
    "claude_code": render_claude_code,
    "cli": render_cli,
    "marketplace": render_marketplace,
}


def test_renderer_contract():
    """All renderers return non-empty str for every template type."""
    gen_dir = Path(
        "packages/attune-help/src/attune_help/templates"
    )
    sample_ids = [
        "con-progressive-depth",
        "tas-run-workflow",
        "ref-tool-security-audit",
        "err-shadow-dirs",
    ]

    for tid in sample_ids:
        template = populate(
            tid,
            audience=AudienceProfile(),
            generated_dir=gen_dir,
        )
        if template is None:
            continue

        for name, fn in RENDERERS.items():
            output = fn(template)
            assert isinstance(output, str), (
                f"{name} returned {type(output)} for {tid}"
            )
            assert len(output) > 10, (
                f"{name} returned too-short output for {tid}"
            )
```

### Marketplace frontmatter validation

```python
import yaml


def test_marketplace_output_has_valid_frontmatter():
    """Marketplace renderer produces parseable YAML frontmatter."""
    gen_dir = Path(
        "packages/attune-help/src/attune_help/templates"
    )
    template = populate(
        "con-progressive-depth",
        audience=AudienceProfile(),
        generated_dir=gen_dir,
    )
    assert template is not None

    output = render_marketplace(template)
    assert output.startswith("---")

    # Extract frontmatter block
    parts = output.split("---", 2)
    assert len(parts) >= 3
    fm_data = yaml.safe_load(parts[1])
    assert "title" in fm_data
    assert "type" in fm_data
```

## Performance testing

### Budgets

| Operation | Budget | How to measure |
|---|---|---|
| HelpEngine construction | < 50 ms | `time.perf_counter()` around `HelpEngine()` |
| First lookup (cold cache) | < 200 ms | First `engine.lookup()` call |
| Subsequent lookup (warm cache) | < 20 ms | Second call to same topic |
| Cross-links cache load | < 100 ms | Time `_load_cross_links()` |
| Full template scan (600+ files) | < 2 s | Time the validation loop |

### Performance test pattern

```python
import time


def test_lookup_performance():
    """Lookup completes within performance budget."""
    engine = HelpEngine(
        storage=MemoryStorage(), renderer="plain"
    )

    start = time.perf_counter()
    engine.lookup("security-audit")
    cold = time.perf_counter() - start

    start = time.perf_counter()
    engine.lookup("security-audit")
    warm = time.perf_counter() - start

    assert cold < 0.2, f"Cold lookup took {cold:.3f}s"
    assert warm < 0.02, f"Warm lookup took {warm:.3f}s"
```

## CI integration

### Running as part of the test suite

Add help system tests to the standard pytest run. No
special configuration is needed beyond having
`attune-help` installed.

```
pytest tests/help/ -v --tb=short
```

### Pre-commit hook

Add a lightweight template validation check to
pre-commit that runs only when template files change:

```yaml
- repo: local
  hooks:
    - id: validate-help-templates
      name: Validate help templates
      entry: python -m pytest tests/help/test_template_validation.py -x --tb=short
      language: system
      files: 'packages/attune-help/.*\.md$'
      pass_filenames: false
```

### CI matrix considerations

Help template tests are platform-independent (no file
system quirks, no encoding issues). Running them on a
single OS (Ubuntu) is sufficient. Skip them in the
cross-platform matrix to save runner minutes.

## Cross-link integrity

### Full integrity check

```python
def test_cross_link_tag_index_integrity():
    """Every ID in the tag index resolves to a file."""
    gen_dir = Path(
        "packages/attune-help/src/attune_help/templates"
    )
    cross_links = json.loads(
        (gen_dir / "cross_links.json").read_text(
            encoding="utf-8"
        )
    )
    tag_index = cross_links.get("tag_index", {})

    dangling = []
    for tag, ids in tag_index.items():
        for tid in ids:
            if _find_template_file(tid, gen_dir) is None:
                dangling.append(f"{tag} -> {tid}")

    assert not dangling, (
        f"{len(dangling)} dangling tag index entries:\n"
        + "\n".join(dangling[:20])
    )
```

## Common test failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `_parse_template_file` raises `TypeError` | Missing `python-frontmatter` dependency | `pip install python-frontmatter` |
| Depth stays at 0 on repeat calls | Storage not shared between calls (new instance each time) | Pass the same `MemoryStorage` instance |
| Precursor returns empty for `.py` | No templates with matching tags in the tag index | Regenerate `cross_links.json` |
| Marketplace output has broken YAML | Template title contains unescaped quotes | Fix the title in the template file |
| Cross-link test finds dangling IDs | Template was deleted but cross_links.json not regenerated | Run the cross-link generator |
| Performance test fails on CI | CI runner is slower than local machine | Increase budget or mark as benchmark-only |

## Want to learn more?

- Say **"what should I test in the help system?"** for
  the conceptual overview of test types and the testing
  pyramid
- Say **"how do I test the help system?"** for the
  step-by-step guide with working Python code
- Say **"I need to test my help system"** for the
  5-step quickstart

## Related Topics

- **Concept**: Help system testing -- what to test and
  why, the testing pyramid, key insights
- **Task**: Help system testing -- step-by-step guide to
  writing tests using HelpEngine directly
- **Quickstart**: Help system testing -- 5-step guide
  with runnable Python code
