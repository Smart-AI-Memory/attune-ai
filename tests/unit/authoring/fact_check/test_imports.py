"""Shared authoritative resolver (#1586) — incl. the line-115 regression."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from attune.authoring.fact_check import imports as fc_imports
from attune.authoring.fact_check import python_refs

_MASTER_BODY = (
    "```python\n"
    "from attune_tdemo import MARKER\n"
    "```\n"
    "\n"
    "See `attune_tdemo.MARKER` for details.\n"
)


def _make_repo(tmp_path: Path) -> tuple[Path, Path]:
    """A repo whose src/ defines a package the active venv has never
    heard of, plus a master doc referencing it."""
    repo = tmp_path / "repo"
    pkg = repo / "src" / "attune_tdemo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("MARKER = 'here'\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname = "tdemo"\n', encoding="utf-8")
    docs = repo / "content" / "features"
    docs.mkdir(parents=True)
    master = docs / "demo.md"
    master.write_text(_MASTER_BODY, encoding="utf-8")
    return repo, master


@pytest.fixture(autouse=True)
def _restore_import_state(monkeypatch: pytest.MonkeyPatch):
    """Undo sys.path inserts and demo-module imports after each test."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    yield
    sys.modules.pop("attune_tdemo", None)


class TestRepoRootDiscovery:
    def test_finds_root_above_master(self, tmp_path: Path) -> None:
        repo, master = _make_repo(tmp_path)
        assert fc_imports.find_repo_root(master) == repo

    def test_none_outside_a_repo_layout(self, tmp_path: Path) -> None:
        loose = tmp_path / "loose.md"
        loose.write_text("x\n", encoding="utf-8")
        assert fc_imports.find_repo_root(loose) is None

    def test_ensure_src_on_path_is_idempotent(self, tmp_path: Path) -> None:
        repo, _ = _make_repo(tmp_path)
        fc_imports.ensure_src_on_path(repo)
        fc_imports.ensure_src_on_path(repo)
        assert sys.path.count(str(repo / "src")) == 1
        fc_imports.ensure_src_on_path(None)  # must be a no-op, not a crash


class TestResolveImportStatement:
    def test_clean_statements_resolve(self) -> None:
        assert fc_imports.resolve_import_statement("import attune") is None
        assert (
            fc_imports.resolve_import_statement("from attune.authoring.fact_check import imports")
            is None
        )

    def test_missing_attribute_named(self) -> None:
        msg = fc_imports.resolve_import_statement(
            "from attune.authoring.fact_check.imports import not_a_real_name"
        )
        assert msg is not None
        assert "no attribute" in msg
        assert "not_a_real_name" in msg

    def test_missing_module_named(self) -> None:
        msg = fc_imports.resolve_import_statement("import attune.nope_xyz")
        assert msg is not None
        assert "ModuleNotFoundError" in msg


class TestLine115Regression:
    def test_repo_src_symbol_resolves_authoritatively(self, tmp_path: Path) -> None:
        """The #1586 regression: a symbol that exists ONLY in the checked
        repo's src/ must resolve — the venv's (absent) view of the
        package must not produce a false 'not importable'."""
        _, master = _make_repo(tmp_path)
        findings = python_refs.check(master)
        assert findings == []

    def test_same_doc_without_repo_layout_still_fails(self, tmp_path: Path) -> None:
        """Negative control: with no repo src/ to resolve against, the
        same references are honestly unresolvable — proving the pass
        above came from repo-src resolution, not ambient state."""
        loose = tmp_path / "demo.md"
        loose.write_text(_MASTER_BODY, encoding="utf-8")
        findings = python_refs.check(loose)
        assert findings, "expected unresolvable-reference findings"
        assert any("attune_tdemo" in f.message for f in findings)
