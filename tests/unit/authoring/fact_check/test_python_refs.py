"""Tests for the python-refs check.

Uses real ``importlib`` against stdlib + attune_author modules
so the test exercises the same code path as production. The
regression fixture for ``attune.ops._readers`` (the ops-dashboard
class of bug) is documented in the docstring of each test —
those paths really don't exist in the active venv, which is
exactly the behavior the check is designed to catch.
"""

from __future__ import annotations

from pathlib import Path

from attune.authoring.fact_check import python_refs
from attune.authoring.fact_check.report import CHECK_PYTHON_REFS


def _write(tmp_path: Path, body: str) -> Path:
    f = tmp_path / "polished.md"
    f.write_text(body, encoding="utf-8")
    return f


def test_catches_unresolvable_module_in_code_fence(tmp_path: Path) -> None:
    """The headline regression: ``from attune.ops._readers import …``."""
    body = "# Polished\n\n" "```python\n" "from attune.ops._readers import ReadOnlyFinder\n" "```\n"
    findings = python_refs.check(_write(tmp_path, body))
    assert any(
        f.check == CHECK_PYTHON_REFS
        and f.severity == "error"
        and "attune.ops._readers" in f.message
        for f in findings
    )


def test_catches_missing_attribute_on_real_module(tmp_path: Path) -> None:
    """Module exists; specific name does not — distinct error path."""
    body = "```python\n" "from attune import DefinitelyNotAClassHere\n" "```\n"
    findings = python_refs.check(_write(tmp_path, body))
    assert any("DefinitelyNotAClassHere" in f.message for f in findings)


def test_catches_unresolvable_prose_dotted(tmp_path: Path) -> None:
    """Prose ref ``attune.ops._readers.Foo`` resolves to nothing."""
    body = "See `attune.ops._readers.ReadOnlyFinder` for details.\n"
    findings = python_refs.check(_write(tmp_path, body))
    assert any(f.severity == "error" and "attune.ops._readers" in f.message for f in findings)


def test_clean_imports_produce_no_findings(tmp_path: Path) -> None:
    """A correct import (``from pathlib import Path``) is silent."""
    body = "```python\n" "from pathlib import Path\n" "import json\n" "```\n"
    findings = python_refs.check(_write(tmp_path, body))
    assert findings == []


def test_skips_invalid_python_in_fence(tmp_path: Path) -> None:
    """Snippets like ``...`` or partial assignments don't ast-parse;
    we silently skip rather than spuriously flag."""
    body = "```python\n" "result = foo(\n" "    ...,\n" "```\n"
    findings = python_refs.check(_write(tmp_path, body))
    assert findings == []


def test_deduplicates_repeated_same_module(tmp_path: Path) -> None:
    """The same unresolvable module mentioned twice surfaces once."""
    body = (
        "```python\n"
        "from attune.ops._readers import A\n"
        "```\n"
        "```python\n"
        "from attune.ops._readers import B\n"
        "```\n"
    )
    findings = python_refs.check(_write(tmp_path, body))
    msgs = [f.message for f in findings if "attune.ops._readers" in f.message]
    assert len(msgs) == 1
