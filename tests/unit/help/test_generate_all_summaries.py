"""Tests for the summaries-copy step in scripts/generate_all.py.

Verifies that `_copy_summaries` correctly bundles summaries.json (and
summaries_by_path.json) from the installed attune-help package into the
generated/ directory so end users see populated Summaries panels.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "generate_all.py"


@pytest.fixture
def gen_module():
    """Load scripts/generate_all.py as a module.

    The script imports sibling modules (build_cross_links, etc.) by name,
    so scripts/ must be on sys.path during load.
    """
    scripts_dir = str(SCRIPT.parent)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location("_generate_all", SCRIPT)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_generate_all"] = mod
        spec.loader.exec_module(mod)
        yield mod
    finally:
        sys.modules.pop("_generate_all", None)
        if scripts_dir in sys.path:
            sys.path.remove(scripts_dir)


def _make_fake_attune_help(
    monkeypatch: pytest.MonkeyPatch,
    templates_dir: Path,
) -> None:
    """Inject a fake attune_help package whose templates dir is templates_dir."""
    pkg_init = templates_dir.parent / "__init__.py"
    pkg_init.write_text("# fake attune_help package\n", encoding="utf-8")
    fake = types.ModuleType("attune_help")
    fake.__file__ = str(pkg_init)
    monkeypatch.setitem(sys.modules, "attune_help", fake)


def test_copy_summaries_copies_both_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gen_module,
) -> None:
    src = tmp_path / "attune_help" / "templates"
    src.mkdir(parents=True)
    (src / "summaries.json").write_text('{"a/b.md": "summary"}', encoding="utf-8")
    (src / "summaries_by_path.json").write_text('{"a/b.md": {"summary": "x"}}', encoding="utf-8")
    _make_fake_attune_help(monkeypatch, src)

    generated = tmp_path / "generated"
    generated.mkdir()

    copied, skipped = gen_module._copy_summaries(generated)
    assert copied == 2
    assert skipped == []
    assert (generated / "summaries.json").read_text(encoding="utf-8") == '{"a/b.md": "summary"}'
    assert (generated / "summaries_by_path.json").exists()


def test_copy_summaries_skips_when_attune_help_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gen_module,
) -> None:
    """When attune_help cannot be located, copy is a no-op."""
    monkeypatch.setattr(gen_module, "_attune_help_templates_dir", lambda: None)

    generated = tmp_path / "generated"
    generated.mkdir()
    copied, skipped = gen_module._copy_summaries(generated)

    assert copied == 0
    assert any("not installed" in r or "missing" in r for r in skipped)


def test_copy_summaries_skips_missing_optional_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gen_module,
) -> None:
    """Only summaries.json present — summaries_by_path.json is reported as skipped."""
    src = tmp_path / "attune_help" / "templates"
    src.mkdir(parents=True)
    (src / "summaries.json").write_text("{}", encoding="utf-8")
    _make_fake_attune_help(monkeypatch, src)

    generated = tmp_path / "generated"
    generated.mkdir()

    copied, skipped = gen_module._copy_summaries(generated)
    assert copied == 1
    assert any("summaries_by_path.json" in r for r in skipped)
    assert (generated / "summaries.json").exists()
    assert not (generated / "summaries_by_path.json").exists()
