"""Tests for scripts/bump_version.py (drift-guards-to-generators R4).

Covers:
- happy path: all 10 files rewritten (15 occurrences), old version
  returned;
- dry-run: validation runs, nothing written;
- semver / same-version rejection;
- count-mismatch aborts BEFORE any write (no partial state);
- real-repo dry-run smoke: the site list matches the actual tree
  (the generator drifting from reality fails here, not at release).

Loads the script via importlib (matches the existing scripts-test
pattern).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bump_version.py"

OLD = "1.0.0"
NEW = "1.1.0"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_bump_version", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    # The script defines a @dataclass; dataclasses resolves
    # cls.__module__ via sys.modules, so the module must be
    # registered BEFORE exec_module or decoration crashes.
    sys.modules["_bump_version"] = m
    try:
        spec.loader.exec_module(m)
        yield m
    finally:
        sys.modules.pop("_bump_version", None)


@pytest.fixture()
def fixture_root(tmp_path: Path) -> Path:
    """A minimal repo tree carrying every version site at OLD."""
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nversion = "{OLD}"\n', encoding="utf-8"
    )
    plugin_cp = tmp_path / "plugin" / ".claude-plugin"
    plugin_cp.mkdir(parents=True)
    (plugin_cp / "plugin.json").write_text(
        f'{{\n  "name": "x",\n  "version": "{OLD}"\n}}\n', encoding="utf-8"
    )
    marketplace = (
        f'{{\n  "metadata": {{"version": "{OLD}"}},\n'
        f'  "plugins": [{{"version": "{OLD}"}}]\n}}\n'
    )
    (plugin_cp / "marketplace.json").write_text(marketplace, encoding="utf-8")
    root_cp = tmp_path / ".claude-plugin"
    root_cp.mkdir()
    (root_cp / "marketplace.json").write_text(marketplace, encoding="utf-8")
    core = tmp_path / "plugin" / "core"
    core.mkdir()
    (core / "__init__.py").write_text(f'__version__ = "{OLD}"\n', encoding="utf-8")
    (tmp_path / "plugin" / "README.md").write_text(
        f"# x\n\n**Version:** {OLD} | **License:** Apache 2.0\n",
        encoding="utf-8",
    )
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "CLAUDE.md").write_text(
        f"# Attune AI Framework v{OLD}\n\nbody\n\n**Version:** {OLD} | tail\n",
        encoding="utf-8",
    )
    ref = tmp_path / "docs" / "reference"
    ref.mkdir(parents=True)
    (ref / "API_REFERENCE.md").write_text(
        f"# API\n\n**Version:** {OLD}\n\nbody\n\n**Version:** {OLD} | tail\n",
        encoding="utf-8",
    )
    web_lib = tmp_path / "website" / "lib"
    web_lib.mkdir(parents=True)
    # Two attune-ai product entries plus a sibling product whose
    # version must NOT be touched (the pypiName anchor guards it).
    (web_lib / "features.ts").write_text(
        "export const PRODUCTS = [\n"
        "  {\n"
        '    id: "attune-ai",\n'
        '    pypiName: "attune-ai",\n'
        f'    version: "{OLD}",\n'
        "  },\n"
        "  {\n"
        '    id: "attune-help",\n'
        '    pypiName: "attune-help",\n'
        '    version: "0.1.0",\n'
        "  },\n"
        "  {\n"
        '    id: "claude-code-plugin",\n'
        '    pypiName: "attune-ai",\n'
        f'    version: "{OLD}",\n'
        "  },\n"
        "];\n",
        encoding="utf-8",
    )
    web_app = tmp_path / "website" / "app"
    web_app.mkdir(parents=True)
    (web_app / "page.tsx").write_text(
        f"<div>\n  <span>v{OLD}</span>\n</div>\n",
        encoding="utf-8",
    )
    return tmp_path


def _all_texts(root: Path) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8")
        for p in [
            root / "pyproject.toml",
            root / "plugin" / ".claude-plugin" / "plugin.json",
            root / "plugin" / ".claude-plugin" / "marketplace.json",
            root / ".claude-plugin" / "marketplace.json",
            root / "plugin" / "core" / "__init__.py",
            root / "plugin" / "README.md",
            root / ".claude" / "CLAUDE.md",
            root / "docs" / "reference" / "API_REFERENCE.md",
            root / "website" / "lib" / "features.ts",
            root / "website" / "app" / "page.tsx",
        ]
    )


class TestBump:
    def test_happy_path_updates_every_site(self, mod, fixture_root: Path) -> None:
        old = mod.bump(fixture_root, NEW)
        assert old == OLD
        combined = _all_texts(fixture_root)
        assert OLD not in combined
        # 1 pyproject + 1 plugin.json + 2+2 marketplace + 1 __init__
        # + 1 plugin README + 2 CLAUDE.md + 2 API_REFERENCE
        # + 2 features.ts + 1 page.tsx = 15 occurrences
        assert combined.count(NEW) == 15
        # The sibling product's independent version is untouched.
        features = fixture_root / "website" / "lib" / "features.ts"
        assert 'version: "0.1.0"' in features.read_text(encoding="utf-8")

    def test_dry_run_writes_nothing(self, mod, fixture_root: Path) -> None:
        before = _all_texts(fixture_root)
        old = mod.bump(fixture_root, NEW, dry_run=True)
        assert old == OLD
        assert _all_texts(fixture_root) == before

    def test_rejects_non_semver(self, mod, fixture_root: Path) -> None:
        with pytest.raises(ValueError, match="not a semver"):
            mod.bump(fixture_root, "1.1")

    def test_rejects_same_version(self, mod, fixture_root: Path) -> None:
        with pytest.raises(ValueError, match="already at"):
            mod.bump(fixture_root, OLD)

    def test_count_mismatch_aborts_with_no_partial_writes(self, mod, fixture_root: Path) -> None:
        # Break a LATE site (CLAUDE.md header) so early sites would
        # already have validated; nothing may be written.
        claude_md = fixture_root / ".claude" / "CLAUDE.md"
        claude_md.write_text(f"no header here\n\n**Version:** {OLD} | tail\n", encoding="utf-8")
        before = _all_texts(fixture_root)
        with pytest.raises(ValueError, match="expected 1 occurrence"):
            mod.bump(fixture_root, NEW)
        assert _all_texts(fixture_root) == before

    def test_cli_main_happy_and_error(self, mod, fixture_root: Path, capsys) -> None:
        rc = mod.main([NEW, "--root", str(fixture_root)])
        assert rc == 0
        out = capsys.readouterr().out
        assert f"bumped {OLD} -> {NEW}" in out
        rc = mod.main(["nope", "--root", str(fixture_root)])
        assert rc == 1
        assert "not a semver" in capsys.readouterr().err


class TestRealRepo:
    def test_site_list_matches_actual_tree(self, mod) -> None:
        """Dry-run against the REAL repo: every site resolves and the
        occurrence counts hold. Catches the generator drifting from
        the tree (renamed file, changed header format) before a
        release does."""
        old = mod.bump(REPO_ROOT, "999.999.999", dry_run=True)
        assert old.count(".") == 2
