"""Tests for scripts/consolidate_changelog.py.

The merge is a pure text transform, so every case runs real — only the
CLI's file I/O touches tmp_path.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "consolidate_changelog.py"

SCATTERED = """# Changelog

## [Unreleased]

## [16.3.0] - 2026-09-08

An intro paragraph.

### Fixed

- first fix

### Added

- first add

### Changed

- the change

### Fixed

- second fix

### Added

- second add

## [16.2.1] - 2026-09-03

### Fixed

- older release, untouched
"""


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_consolidate_changelog", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["_consolidate_changelog"] = m
    spec.loader.exec_module(m)
    return m


def _section(text: str, version: str) -> str:
    start = text.index(f"## [{version}]")
    rest = text[start + 1 :]
    nxt = rest.find("\n## [")
    return rest[:nxt] if nxt != -1 else rest


class TestConsolidate:
    def test_duplicate_headers_are_merged_once_each(self, mod) -> None:
        out = mod.consolidate(SCATTERED, "16.3.0")
        section = _section(out, "16.3.0")
        for header in ("### Added", "### Changed", "### Fixed"):
            assert section.count(header) == 1, header

    def test_entry_order_is_preserved_within_a_category(self, mod) -> None:
        section = _section(mod.consolidate(SCATTERED, "16.3.0"), "16.3.0")
        assert section.index("first add") < section.index("second add")
        assert section.index("first fix") < section.index("second fix")

    def test_categories_come_out_in_keep_a_changelog_order(self, mod) -> None:
        section = _section(mod.consolidate(SCATTERED, "16.3.0"), "16.3.0")
        assert section.index("### Added") < section.index("### Changed")
        assert section.index("### Changed") < section.index("### Fixed")

    def test_no_entry_is_lost(self, mod) -> None:
        section = _section(mod.consolidate(SCATTERED, "16.3.0"), "16.3.0")
        for entry in ("first fix", "second fix", "first add", "second add", "the change"):
            assert entry in section, entry

    def test_intro_prose_survives(self, mod) -> None:
        assert "An intro paragraph." in mod.consolidate(SCATTERED, "16.3.0")

    def test_other_sections_are_untouched(self, mod) -> None:
        out = mod.consolidate(SCATTERED, "16.3.0")
        assert _section(out, "16.2.1") == _section(SCATTERED, "16.2.1")
        assert out.startswith("# Changelog\n")

    def test_idempotent(self, mod) -> None:
        once = mod.consolidate(SCATTERED, "16.3.0")
        assert mod.consolidate(once, "16.3.0") == once

    def test_already_clean_section_is_returned_unchanged(self, mod) -> None:
        clean = "# C\n\n## [1.0.0] - 2026-01-01\n\n### Added\n\n- one\n"
        assert mod.consolidate(clean, "1.0.0") == clean

    def test_unknown_header_is_kept_in_first_seen_order(self, mod) -> None:
        text = (
            "# C\n\n## [1.0.0] - 2026-01-01\n\n### Notes\n\n- n\n\n"
            "### Added\n\n- a\n\n### Notes\n\n- n2\n"
        )
        out = mod.consolidate(text, "1.0.0")
        assert out.count("### Notes") == 1
        assert out.index("### Added") < out.index("### Notes")
        assert "n2" in out

    def test_empty_section_body_does_not_crash(self, mod) -> None:
        text = "# C\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n\n### Added\n\n- a\n"
        assert mod.consolidate(text, "Unreleased") == text

    def test_missing_version_raises_rather_than_silently_passing(self, mod) -> None:
        with pytest.raises(LookupError, match="no ## \\[9.9.9\\] section"):
            mod.consolidate(SCATTERED, "9.9.9")


class TestCli:
    def test_writes_and_reports(self, mod, tmp_path: Path, capsys) -> None:
        path = tmp_path / "CHANGELOG.md"
        path.write_text(SCATTERED, encoding="utf-8")
        assert mod.main(["16.3.0", "--path", str(path)]) == 0
        assert "consolidated" in capsys.readouterr().out
        assert _section(path.read_text(encoding="utf-8"), "16.3.0").count("### Fixed") == 1

    def test_check_reports_without_writing(self, mod, tmp_path: Path) -> None:
        path = tmp_path / "CHANGELOG.md"
        path.write_text(SCATTERED, encoding="utf-8")
        assert mod.main(["16.3.0", "--path", str(path), "--check"]) == 1
        assert path.read_text(encoding="utf-8") == SCATTERED

    def test_check_passes_on_a_clean_file(self, mod, tmp_path: Path) -> None:
        path = tmp_path / "CHANGELOG.md"
        path.write_text("# C\n\n## [1.0.0] - 2026-01-01\n\n### Added\n\n- one\n", encoding="utf-8")
        assert mod.main(["1.0.0", "--path", str(path), "--check"]) == 0

    def test_missing_version_exits_2(self, mod, tmp_path: Path, capsys) -> None:
        path = tmp_path / "CHANGELOG.md"
        path.write_text(SCATTERED, encoding="utf-8")
        assert mod.main(["9.9.9", "--path", str(path)]) == 2
        assert "error:" in capsys.readouterr().err


def test_the_repo_changelog_is_consolidated(mod) -> None:
    """Drift guard: main's own changelog must stay merged.

    Cutting 16.3.0 found seven headers in one section; this fails the
    moment they accumulate again, at PR time rather than release time.
    """
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for version in ("Unreleased", "16.3.0"):
        assert mod.consolidate(text, version) == text, version
