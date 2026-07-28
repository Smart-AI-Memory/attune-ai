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


# --- mkdocs-scoped (published surfaces only) ------------------------------


def _write_mkdocs(repo: Path, nav: list[str], exclude: list[str]) -> None:
    nav_block = "\n".join(f"  - Page: {p}" for p in nav)
    exc_block = "\n".join(f"  {ln}" for ln in exclude)
    (repo / "mkdocs.yml").write_text(
        f"site_name: T\nexclude_docs: |\n{exc_block}\nnav:\n{nav_block}\n",
        encoding="utf-8",
    )


def test_scope_skips_excluded_orphan(tmp_path: Path):
    pytest.importorskip("pathspec")
    repo = tmp_path
    (repo / "docs").mkdir()
    (repo / "docs" / "orphan.md").write_text(
        "```python\nfrom attune import NotReal_xyz\n```\n", encoding="utf-8"
    )
    _write_mkdocs(repo, nav=[], exclude=["orphan.md"])
    findings, _ = adi.audit(repo, None)
    # excluded by exclude_docs AND not in nav -> not a published page.
    assert findings == []


def test_scope_checks_nav_page_even_if_excluded(tmp_path: Path):
    repo = tmp_path
    (repo / "docs").mkdir()
    (repo / "docs" / "page.md").write_text(
        "```python\nfrom attune import NotReal_xyz\n```\n", encoding="utf-8"
    )
    # In nav AND in exclude_docs (the real hooks.md conflict): nav wins.
    _write_mkdocs(repo, nav=["page.md"], exclude=["page.md"])
    findings, _ = adi.audit(repo, None)
    assert len(findings) == 1


def test_scope_content_blog_always_checked(tmp_path: Path):
    repo = tmp_path
    (repo / "content" / "blog").mkdir(parents=True)
    (repo / "content" / "blog" / "x.md").write_text(
        "```python\nfrom attune import NotReal_xyz\n```\n", encoding="utf-8"
    )
    # content/** is the website source — never governed by mkdocs exclude.
    _write_mkdocs(repo, nav=[], exclude=["**"])
    findings, _ = adi.audit(repo, None)
    assert len(findings) == 1


# --- G4 deep checks (claim-drift-gates G4) ---------------------------------


def _deep_repo(tmp_path: Path, doc_body: str, allow: str | None = None) -> Path:
    repo = tmp_path
    (repo / "docs" / "getting-started").mkdir(parents=True)
    (repo / "docs" / "getting-started" / "x.md").write_text(doc_body, encoding="utf-8")
    gates = repo / ".claude" / "gates"
    gates.mkdir(parents=True)
    (gates / "doc-deep-check-allowlist.txt").write_text(
        allow if allow is not None else "docs/getting-started/x.md :: onboarding snippet\n",
        encoding="utf-8",
    )
    return repo


def test_allowlist_requires_reason(tmp_path: Path):
    repo = _deep_repo(tmp_path, "no fences\n", allow="docs/getting-started/x.md\n")
    findings, _ = adi.audit(repo, ["docs/getting-started/x.md"])
    assert any("needs '<path> :: <reason>'" in f.message for f in findings)


def test_deep_unknown_kwarg_flagged(tmp_path: Path):
    body = (
        "```python\n"
        "from attune.roundtable.solutions import CheckReceipt\n"
        'r = CheckReceipt(label="x", argv=[], exit_code=0, tail="", bogus_kwarg=1)\n'
        "```\n"
    )
    repo = _deep_repo(tmp_path, body)
    findings, stats = adi.audit(repo, ["docs/getting-started/x.md"])
    assert stats.deep_files == 1
    assert any("bogus_kwarg" in f.message for f in findings)


def test_deep_dataclass_attr_flagged(tmp_path: Path):
    body = (
        "```python\n"
        "from attune.roundtable.solutions import CheckReceipt\n"
        'r = CheckReceipt(label="x", argv=[], exit_code=0, tail="")\n'
        "print(r.tail)\n"
        "print(r.tale_typo)\n"
        "```\n"
    )
    repo = _deep_repo(tmp_path, body)
    findings, _ = adi.audit(repo, ["docs/getting-started/x.md"])
    msgs = [f.message for f in findings]
    assert any("tale_typo" in m for m in msgs)
    assert not any("'tail'" in m for m in msgs)


def test_deep_module_attr_chain_flagged(tmp_path: Path):
    body = "```python\nimport attune\nattune.definitely_not_real_xyz()\n```\n"
    repo = _deep_repo(tmp_path, body)
    findings, _ = adi.audit(repo, ["docs/getting-started/x.md"])
    assert any("definitely_not_real_xyz" in f.message for f in findings)


def test_deep_not_run_without_allowlist_entry(tmp_path: Path):
    body = (
        "```python\n"
        "from attune.roundtable.solutions import CheckReceipt\n"
        'r = CheckReceipt(label="x", argv=[], exit_code=0, tail="", bogus_kwarg=1)\n'
        "```\n"
    )
    repo = _deep_repo(tmp_path, body, allow="# empty\n")
    findings, stats = adi.audit(repo, ["docs/getting-started/x.md"])
    assert stats.deep_files == 0
    assert findings == []


def test_json_fence_bad_module_flagged(tmp_path: Path):
    body = '```json\n{"mcpServers": {"s": {"args": ["-m", "attune.gone_xyz"]}}}\n```\n'
    repo = _deep_repo(tmp_path, body)
    findings, _ = adi.audit(repo, ["docs/getting-started/x.md"])
    assert any("attune.gone_xyz" in f.message for f in findings)


def test_json_fence_real_module_passes(tmp_path: Path):
    body = '```json\n{"mcpServers": {"s": {"args": ["-m", "attune.mcp.server"]}}}\n```\n'
    repo = _deep_repo(tmp_path, body)
    findings, _ = adi.audit(repo, ["docs/getting-started/x.md"])
    assert findings == []


def test_mcp_json_diff_only_when_documenting_real_file(tmp_path: Path):
    fence = (
        '```json\n{"mcpServers": {"other": {"command": "python",'
        ' "args": ["-m", "attune.mcp.server"]}}}\n```\n'
    )
    real = '{"mcpServers": {"attune-ai": {"command": "uv", "args": ["run"]}}}'
    # Desktop-config context: no mention of .claude/mcp.json -> no diff.
    repo = _deep_repo(tmp_path, "Claude Desktop config:\n\n" + fence)
    (repo / ".claude" / "mcp.json").write_text(real, encoding="utf-8")
    findings, _ = adi.audit(repo, ["docs/getting-started/x.md"])
    assert findings == []
    # Documenting the real file -> the unknown server IS flagged.
    repo2 = _deep_repo(tmp_path / "second", "Configured via `.claude/mcp.json`:\n\n" + fence)
    (repo2 / ".claude" / "mcp.json").write_text(real, encoding="utf-8")
    findings2, _ = adi.audit(repo2, ["docs/getting-started/x.md"])
    assert any("not present in the real .claude/mcp.json" in f.message for f in findings2)


def test_mcp_json_arg_drift_flagged(tmp_path: Path):
    fence = (
        '```json\n{"mcpServers": {"attune-ai": {"command": "python",'
        ' "args": ["-m", "attune.mcp.server"]}}}\n```\n'
    )
    real = (
        '{"mcpServers": {"attune-ai": {"command": "uv",'
        ' "args": ["run", "python", "-m", "attune.mcp.server"]}}}'
    )
    repo = _deep_repo(tmp_path, "The real `.claude/mcp.json`:\n\n" + fence)
    (repo / ".claude" / "mcp.json").write_text(real, encoding="utf-8")
    findings, _ = adi.audit(repo, ["docs/getting-started/x.md"])
    assert any("drifts from .claude/mcp.json" in f.message for f in findings)
