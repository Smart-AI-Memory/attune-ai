---
type: quickstart
name: task-help-system-testing
tags: [testing, help-system, quality, validation]
source: developer-guidance
---

# I Need to Test My Help System

Five steps to verify templates, progressive depth,
precursor warnings, cross-links, and renderers -- with
runnable Python code you can paste into a test file.

## Step 1: Verify templates parse

Scan every `.md` file and confirm frontmatter loads
without exceptions. This catches typos, missing fields,
and malformed YAML.

```python
from pathlib import Path
from attune_help.templates import _parse_template_file

TEMPLATES_DIR = Path(
    "packages/attune-help/src/attune_help/templates"
)


def test_all_templates_load():
    """Every template parses without error."""
    failures = []
    for md in TEMPLATES_DIR.rglob("*.md"):
        try:
            data = _parse_template_file(md)
            assert data["type"], f"{md.name}: empty type"
            assert data["tags"], f"{md.name}: no tags"
        except Exception as e:
            failures.append(f"{md.name}: {e}")
    assert not failures, "\n".join(failures)
```

Run it: `pytest tests/help/test_templates.py -x`

## Step 2: Test progressive depth

Call `lookup` on the same topic three times. Depth
should advance from 0 to 1 to 2.

```python
from attune_help.engine import HelpEngine
from attune_help.storage import MemoryStorage


def test_depth_advances():
    """Repeated lookup escalates depth 0 -> 1 -> 2."""
    engine = HelpEngine(
        storage=MemoryStorage(), renderer="plain"
    )

    r1 = engine.lookup_raw("security-audit")
    r2 = engine.lookup_raw("security-audit")
    r3 = engine.lookup_raw("security-audit")

    assert r1.metadata["depth_level"] == 0
    assert r2.metadata["depth_level"] == 1
    assert r3.metadata["depth_level"] == 2
```

## Step 3: Test precursor warnings

Pass a filename to `precursor_warnings()` and confirm
relevant help surfaces.

```python
def test_python_file_gets_warnings():
    """Editing a .py file triggers help system warnings."""
    engine = HelpEngine(
        storage=MemoryStorage(), renderer="plain"
    )
    warnings = engine.precursor_warnings("app.py")
    assert len(warnings) > 0
    assert all(isinstance(w, str) for w in warnings)
```

## Step 4: Check cross-links

Load `cross_links.json` and verify every template ID
in the links index resolves to a real file.

```python
import json
from attune_help.templates import _find_template_file


def test_no_dangling_cross_links():
    """Every cross-link target exists on disk."""
    gen_dir = Path(
        "packages/attune-help/src/attune_help/templates"
    )
    data = json.loads(
        (gen_dir / "cross_links.json").read_text(
            encoding="utf-8"
        )
    )

    dangling = [
        tid
        for tid in data.get("links", {})
        if _find_template_file(tid, gen_dir) is None
    ]
    assert not dangling, f"Dangling: {dangling[:10]}"
```

## Step 5: Smoke-test renderers

Render one template through each renderer and confirm
non-empty output with no exceptions.

```python
from attune_help.templates import AudienceProfile, populate
from attune_help.transformers import (
    render_claude_code, render_cli, render_marketplace,
)

RENDERERS = {
    "plain": lambda t: t.body,
    "claude_code": render_claude_code,
    "cli": render_cli,
    "marketplace": render_marketplace,
}


def test_all_renderers_work():
    """Each renderer produces non-empty output."""
    gen_dir = Path(
        "packages/attune-help/src/attune_help/templates"
    )
    template = populate(
        "con-progressive-depth",
        audience=AudienceProfile(),
        generated_dir=gen_dir,
    )
    assert template is not None

    for name, fn in RENDERERS.items():
        output = fn(template)
        assert output and len(output) > 10, (
            f"{name} returned empty or too-short output"
        )
```

**Done.** Run `pytest tests/help/ -v` to execute all
five checks. If everything passes, your help system is
healthy.

## Quick additions

| Want to add | What to do |
|---|---|
| Performance budget | Wrap `engine.lookup()` in `time.perf_counter()` and assert < 200 ms |
| CI gate | Add `pytest tests/help/ -x --tb=short` to your GitHub Actions workflow |
| Pre-commit hook | Trigger template validation only when `.md` files under `templates/` change |
| Coverage tracking | Run `pytest tests/help/ --cov=attune_help --cov-report=term-missing` |

## Want to learn more?

- Say **"what should I test in the help system?"** for
  the conceptual overview -- test types, the testing
  pyramid, and why each layer matters
- Say **"walk me through the full test setup"** for the
  detailed guide with comprehensive test code
- Say **"show me the help system test reference"** for
  complete patterns, CI integration, performance budgets,
  and troubleshooting
- Try **/smart-test** to find untested code paths in the
  help engine itself

## Related Topics

- **Concept**: Help system testing -- what to test and
  why, the testing pyramid, key insights
- **Task**: Help system testing -- step-by-step guide to
  writing tests using HelpEngine directly
- **Reference**: Help system testing -- complete test
  patterns, CI integration, and performance budgets
