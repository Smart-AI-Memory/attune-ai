"""Tests for the doc-examples check (compile + coroutine misuse).

Covers help-docs-single-source follow-up P5. The check derives
"is this callable async?" from each block's *own* imports (no
hardcoded package list), so the tests import real coroutine functions
(stdlib ``asyncio.sleep``) and a purpose-built local module to exercise
the ``from M import f``, ``import M``, and class-method paths.
"""

from __future__ import annotations

from pathlib import Path

from attune.authoring.fact_check import doc_examples
from attune.authoring.fact_check.report import CHECK_DOC_EXAMPLES


def _md(tmp_path: Path, *blocks: str) -> Path:
    """Write a markdown file whose body is the given python blocks."""
    parts = ["# Doc\n"]
    for block in blocks:
        parts.append("```python\n" + block.strip("\n") + "\n```\n")
    path = tmp_path / "doc.md"
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


# --- coroutine misuse (bare ``from M import f`` path) -----------------------


def test_flags_coroutine_called_without_await(tmp_path):
    path = _md(tmp_path, "from asyncio import sleep\n\nsleep(1)\n")
    findings = doc_examples.check(path)
    assert len(findings) == 1
    assert findings[0].check == CHECK_DOC_EXAMPLES
    assert findings[0].severity == "error"
    assert "sleep()" in findings[0].message


def test_awaited_coroutine_is_clean(tmp_path):
    # Top-level await is an illustrative fragment — compiled wrapped in
    # ``async def`` and recognised as correctly awaited.
    path = _md(tmp_path, "from asyncio import sleep\n\nawait sleep(1)\n")
    assert doc_examples.check(path) == []


def test_scheduled_coroutine_is_clean(tmp_path):
    path = _md(tmp_path, "import asyncio\nfrom asyncio import sleep\n\nasyncio.run(sleep(1))\n")
    assert doc_examples.check(path) == []


def test_aliased_import_is_tracked(tmp_path):
    path = _md(tmp_path, "from asyncio import sleep as nap\n\nnap(1)\n")
    findings = doc_examples.check(path)
    assert len(findings) == 1
    assert "nap()" in findings[0].message


# --- ``import M`` + class-method paths via a local module -------------------


def _write_async_module(tmp_path: Path, monkeypatch) -> None:
    """Create an importable module with a coroutine fn and a class
    whose method is a coroutine, and put it on ``sys.path``."""
    (tmp_path / "mymod.py").write_text(
        "async def fetch():\n"
        "    return 1\n"
        "\n\n"
        "class Client:\n"
        "    async def call(self):\n"
        "        return 2\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))


def test_flags_module_attr_coroutine(tmp_path, monkeypatch):
    _write_async_module(tmp_path, monkeypatch)
    path = _md(tmp_path, "import mymod\n\nmymod.fetch()\n")
    findings = doc_examples.check(path)
    assert len(findings) == 1
    assert "fetch()" in findings[0].message


def test_flags_class_method_coroutine(tmp_path, monkeypatch):
    _write_async_module(tmp_path, monkeypatch)
    path = _md(tmp_path, "from mymod import Client\n\nc = Client()\nc.call()\n")
    findings = doc_examples.check(path)
    assert len(findings) == 1
    assert "call()" in findings[0].message


def test_awaited_class_method_is_clean(tmp_path, monkeypatch):
    _write_async_module(tmp_path, monkeypatch)
    path = _md(tmp_path, "from mymod import Client\n\nc = Client()\nawait c.call()\n")
    assert doc_examples.check(path) == []


# --- tolerance + edge cases -------------------------------------------------


def test_sync_call_is_not_flagged(tmp_path):
    path = _md(tmp_path, "from math import sqrt\n\nsqrt(4)\n")
    assert doc_examples.check(path) == []


def test_unimportable_module_is_skipped_silently(tmp_path):
    # A doc importing a module this venv lacks must not crash or flag a
    # coroutine — python_refs owns the "module not importable" finding.
    path = _md(tmp_path, "from totally_made_up_pkg import go\n\ngo()\n")
    assert doc_examples.check(path) == []


def test_non_compiling_block_is_a_warning(tmp_path):
    path = _md(tmp_path, "def broken(:\n    pass\n")
    findings = doc_examples.check(path)
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert "does not compile" in findings[0].message


def test_no_python_blocks_is_clean(tmp_path):
    path = tmp_path / "prose.md"
    path.write_text("# Title\n\nJust prose, no code.\n", encoding="utf-8")
    assert doc_examples.check(path) == []
