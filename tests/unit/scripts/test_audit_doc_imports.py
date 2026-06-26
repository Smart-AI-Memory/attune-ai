"""Unit tests for ``scripts/audit_doc_imports.py`` — the doc-import gate.

Tests the script's LOGIC (fence extraction, skip markers, multi-line
imports, attune-only filtering, path exclusion, resolution) with
synthetic fixtures. Does NOT assert on the live doc backlog, which
changes as docs are fixed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_doc_imports.py"
_spec = importlib.util.spec_from_file_location("audit_doc_imports", _SCRIPT)
adi = importlib.util.module_from_spec(_spec)
# Register before exec so dataclass (with `from __future__ import
# annotations`) can resolve `cls.__module__` during class creation.
sys.modules[_spec.name] = adi
_spec.loader.exec_module(adi)


# --- fence + import extraction --------------------------------------------


def test_extracts_attune_imports_only():
    body = (
        "import os\n"
        "from attune import AttuneConfig\n"
        "import attune.workflows\n"
        "from collections import OrderedDict\n"
    )
    stmts = [s for _, s in adi._import_statements(body)]
    assert "from attune import AttuneConfig" in stmts
    assert "import attune.workflows" in stmts
    # non-attune imports are ignored
    assert not any("os" in s or "OrderedDict" in s for s in stmts)


def test_handles_multiline_parenthesized_import():
    body = "from attune import (\n    AttuneConfig,\n    get_redis_memory,\n)\n"
    stmts = [s for _, s in adi._import_statements(body)]
    assert stmts == ["from attune import AttuneConfig, get_redis_memory"]


def test_falls_back_to_line_scan_on_snippet():
    # A non-parseable snippet (bare expression) still yields its import.
    body = "from attune import AttuneConfig\nresult = wf.  # truncated\n"
    stmts = [s for _, s in adi._import_statements(body)]
    assert "from attune import AttuneConfig" in stmts


# --- resolution -----------------------------------------------------------


def test_resolve_valid_import_returns_none():
    # AttuneConfig is a stable public export.
    assert adi._resolve("from attune import AttuneConfig") is None


def test_resolve_missing_symbol_reports():
    msg = adi._resolve("from attune import DefinitelyNotARealSymbol_xyz")
    assert msg is not None
    assert "DefinitelyNotARealSymbol_xyz" in msg


def test_resolve_missing_module_reports():
    msg = adi._resolve("from attune.not_a_module_xyz import Thing")
    assert msg is not None
    assert "ModuleNotFoundError" in msg


def test_resolve_import_alias_valid():
    assert adi._resolve("import attune.workflows as wf") is None


# --- skip marker ----------------------------------------------------------


def test_skip_marker_detected():
    text = (
        "# Doc\n\n"
        "<!-- doc-import-skip: historical before-example -->\n"
        "```python\n"
        "from attune import GoneSymbol\n"
        "```\n"
    )
    fences = list(adi._iter_python_fences(text))
    assert len(fences) == 1
    _, _, skipped, reason = fences[0]
    assert skipped is True
    assert reason == "historical before-example"


def test_no_skip_marker_not_skipped():
    text = "```python\nfrom attune import AttuneConfig\n```\n"
    _, _, skipped, _ = list(adi._iter_python_fences(text))[0]
    assert skipped is False


# --- end-to-end audit() ---------------------------------------------------


def test_audit_flags_broken_import(tmp_path: Path):
    repo = tmp_path
    (repo / "docs").mkdir()
    (repo / "docs" / "x.md").write_text(
        "```python\nfrom attune import NotRealSymbol_xyz\n```\n",
        encoding="utf-8",
    )
    findings, stats = adi.audit(repo, ["docs/x.md"])
    assert len(findings) == 1
    assert findings[0].statement == "from attune import NotRealSymbol_xyz"
    assert stats.imports_checked == 1


def test_audit_passes_valid_import(tmp_path: Path):
    repo = tmp_path
    (repo / "docs").mkdir()
    (repo / "docs" / "x.md").write_text(
        "```python\nfrom attune import AttuneConfig\n```\n", encoding="utf-8"
    )
    findings, _ = adi.audit(repo, ["docs/x.md"])
    assert findings == []


def test_audit_honors_skip_marker(tmp_path: Path):
    repo = tmp_path
    (repo / "docs").mkdir()
    (repo / "docs" / "x.md").write_text(
        "<!-- doc-import-skip: removed in vX, before-example -->\n"
        "```python\nfrom attune import GoneSymbol_xyz\n```\n",
        encoding="utf-8",
    )
    findings, stats = adi.audit(repo, ["docs/x.md"])
    assert findings == []
    assert stats.skipped_fences == 1


@pytest.mark.parametrize("excluded", ["docs/specs", "docs/archive"])
def test_audit_excludes_history_paths(tmp_path: Path, excluded: str):
    repo = tmp_path
    d = repo / excluded
    d.mkdir(parents=True)
    (d / "x.md").write_text("```python\nfrom attune import NotReal_xyz\n```\n", encoding="utf-8")
    # Even when pointed straight at it, excluded paths yield no findings.
    findings, _ = adi.audit(repo, [excluded])
    assert findings == []
