---
type: task
name: task-help-system-testing
tags: [testing, help-system, quality, validation]
source: developer-guidance
---

# Task: Test the attune-help system

Step-by-step guide to verifying that templates load,
progressive depth works, precursor warnings fire
correctly, cross-links resolve, and renderers produce
valid output. All examples use the HelpEngine API
directly.

## Prerequisites

- `attune-help` installed (`pip install attune-help` or
  editable install from the monorepo)
- `pytest` available
- `python-frontmatter` installed (pulled in by
  attune-help)

## Step 1: Verify template collection

Confirm every template file in the templates directory
parses without error. This is the equivalent of
`pytest --collect-only` for templates.

```python
from pathlib import Path
from attune_help.templates import _parse_template_file

TEMPLATES_DIR = Path(
    "packages/attune-help/src/attune_help/templates"
)

REQUIRED_FIELDS = {"type", "name", "tags", "source"}
TYPE_DIRS = [
    "concepts", "tasks", "references", "quickstarts",
    "errors", "warnings", "tips", "faqs", "notes",
    "troubleshooting", "comparisons",
]


def test_all_templates_parse():
    """Every .md template parses with valid frontmatter."""
    failures = []
    count = 0

    for type_dir in TYPE_DIRS:
        for md_file in (TEMPLATES_DIR / type_dir).glob("*.md"):
            count += 1
            try:
                data = _parse_template_file(md_file)
                missing = REQUIRED_FIELDS - set(data.keys())
                if missing:
                    failures.append(
                        f"{md_file.name}: missing {missing}"
                    )
                if not data.get("title"):
                    failures.append(
                        f"{md_file.name}: no h1 heading"
                    )
            except Exception as e:
                failures.append(f"{md_file.name}: {e}")

    assert count > 0, "No templates found"
    assert not failures, (
        f"{len(failures)} template(s) failed:\n"
        + "\n".join(failures)
    )
```

## Step 2: Test progressive depth cycle

Progressive depth should advance from concept (0) to
task (1) to reference (2) on repeated calls, then reset
when the topic changes.

```python
from attune_help.engine import HelpEngine
from attune_help.storage import MemoryStorage


def test_progressive_depth_cycle():
    """Three calls to the same topic escalate depth."""
    engine = HelpEngine(
        storage=MemoryStorage(),
        renderer="plain",
    )

    # First call: concept (depth 0)
    r1 = engine.lookup_raw("security-audit")
    assert r1 is not None
    assert r1.metadata["depth_level"] == 0

    # Second call: task (depth 1)
    r2 = engine.lookup_raw("security-audit")
    assert r2 is not None
    assert r2.metadata["depth_level"] == 1

    # Third call: reference (depth 2)
    r3 = engine.lookup_raw("security-audit")
    assert r3 is not None
    assert r3.metadata["depth_level"] == 2


def test_topic_change_resets_depth():
    """Switching topics resets depth to 0."""
    engine = HelpEngine(
        storage=MemoryStorage(),
        renderer="plain",
    )

    engine.lookup_raw("security-audit")  # depth 0
    engine.lookup_raw("security-audit")  # depth 1

    # New topic resets
    r = engine.lookup_raw("code-review")
    assert r is not None
    assert r.metadata["depth_level"] == 0
```

## Step 3: Test precursor warnings

Precursor warnings map file extensions and filenames to
relevant help templates. Verify each file type triggers
the expected tags.

```python
def test_precursor_warnings_python_file():
    """Python files trigger testing/error-handling warnings."""
    engine = HelpEngine(
        storage=MemoryStorage(),
        renderer="plain",
    )
    warnings = engine.precursor_warnings("src/models.py")
    assert len(warnings) > 0
    # At least one warning should be returned
    assert all(isinstance(w, str) for w in warnings)


def test_precursor_warnings_yaml_file():
    """YAML files trigger CI/GitHub Actions warnings."""
    engine = HelpEngine(
        storage=MemoryStorage(),
        renderer="plain",
    )
    warnings = engine.precursor_warnings(
        ".github/workflows/ci.yml"
    )
    assert len(warnings) > 0


def test_precursor_warnings_unknown_extension():
    """Unknown extensions return no warnings."""
    engine = HelpEngine(
        storage=MemoryStorage(),
        renderer="plain",
    )
    warnings = engine.precursor_warnings("data.xyz")
    assert warnings == []
```

## Step 4: Verify cross-links resolve

Every template ID in `cross_links.json` should point to
a file that actually exists on disk.

```python
import json


def test_cross_links_resolve():
    """All cross-link targets exist as template files."""
    from attune_help.templates import _find_template_file

    gen_dir = Path(
        "packages/attune-help/src/attune_help/templates"
    )
    cross_links = json.loads(
        (gen_dir / "cross_links.json").read_text(
            encoding="utf-8"
        )
    )

    dangling = []
    for template_id in cross_links.get("links", {}):
        if _find_template_file(template_id, gen_dir) is None:
            dangling.append(template_id)

    assert not dangling, (
        f"{len(dangling)} dangling cross-link(s):\n"
        + "\n".join(dangling)
    )
```

## Step 5: Test each renderer

Each renderer should produce non-empty output and not
raise exceptions for any template type.

```python
RENDERERS = ["plain", "cli", "claude_code", "marketplace"]
SAMPLE_TOPICS = [
    "con-progressive-depth",
    "err-shadow-dirs",
    "ref-tool-security-audit",
]


def test_renderers_produce_output():
    """Every renderer returns non-empty strings."""
    from attune_help.templates import (
        AudienceProfile,
        populate,
    )
    from attune_help.transformers import (
        render_claude_code,
        render_cli,
        render_marketplace,
    )

    gen_dir = Path(
        "packages/attune-help/src/attune_help/templates"
    )
    renderers = {
        "plain": lambda t: t.body,
        "claude_code": render_claude_code,
        "cli": render_cli,
        "marketplace": render_marketplace,
    }

    for topic_id in SAMPLE_TOPICS:
        template = populate(
            topic_id,
            audience=AudienceProfile(),
            generated_dir=gen_dir,
        )
        if template is None:
            continue

        for name, fn in renderers.items():
            output = fn(template)
            assert output, (
                f"{name} returned empty for {topic_id}"
            )
            assert isinstance(output, str)
```

## Verification checklist

After adding these tests to your suite:

- [ ] `pytest tests/help/ -v` passes with no failures
- [ ] Template count matches expected (check `cross_links.json`
  stats)
- [ ] All three depth levels produce distinct output
- [ ] Precursor warnings cover `.py`, `.yml`, `.toml`, `.md`
  at minimum
- [ ] No dangling cross-links

## Want to learn more?

- Say **"what should I test in the help system?"** for
  the conceptual overview of test types and the testing
  pyramid
- Say **"show me the help system test reference"** for
  complete patterns including performance testing and CI
  integration
- Say **"I need to test my help system"** for the
  5-step quickstart

## Related Topics

- **Concept**: Help system testing -- what to test and
  why, the testing pyramid, key insights
- **Reference**: Help system testing -- complete test
  patterns, CI integration, and performance budgets
- **Quickstart**: Help system testing -- 5-step guide
  with runnable Python code
