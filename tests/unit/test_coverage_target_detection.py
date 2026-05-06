"""Tests for ``attune.utils.coverage`` — pyproject-driven --cov target detection."""

from __future__ import annotations

from pathlib import Path

from attune.utils.coverage import detect_coverage_target, detect_coverage_targets


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class TestDetectCoverageTargets:
    def test_no_pyproject_returns_src(self, tmp_path: Path) -> None:
        assert detect_coverage_targets(tmp_path) == ["src"]

    def test_corrupt_pyproject_returns_src(self, tmp_path: Path) -> None:
        _write(tmp_path / "pyproject.toml", "not toml {")
        assert detect_coverage_targets(tmp_path) == ["src"]

    def test_tool_coverage_run_source_wins(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "pyproject.toml",
            "[tool.coverage.run]\nsource = ['my_pkg', 'other_pkg']\n",
        )
        assert detect_coverage_targets(tmp_path) == ["my_pkg", "other_pkg"]

    def test_source_pkgs_alias_works(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "pyproject.toml",
            "[tool.coverage.run]\nsource_pkgs = ['only_pkg']\n",
        )
        assert detect_coverage_targets(tmp_path) == ["only_pkg"]

    def test_hatch_packages_when_no_coverage_section(self, tmp_path: Path) -> None:
        """attune-gui case: hatch wheel packages from non-src layout."""
        _write(
            tmp_path / "pyproject.toml",
            (
                "[project]\nname = 'attune-gui'\n"
                "[tool.hatch.build.targets.wheel]\n"
                "packages = ['sidecar/attune_gui']\n"
            ),
        )
        assert detect_coverage_targets(tmp_path) == ["sidecar/attune_gui"]

    def test_falls_back_to_project_name_under_src(self, tmp_path: Path) -> None:
        (tmp_path / "src" / "my_pkg").mkdir(parents=True)
        _write(tmp_path / "pyproject.toml", "[project]\nname = 'my-pkg'\n")
        assert detect_coverage_targets(tmp_path) == ["src/my_pkg"]

    def test_falls_back_to_project_name_at_root(self, tmp_path: Path) -> None:
        (tmp_path / "flat_pkg").mkdir()
        _write(tmp_path / "pyproject.toml", "[project]\nname = 'flat-pkg'\n")
        assert detect_coverage_targets(tmp_path) == ["flat_pkg"]

    def test_default_when_no_signal(self, tmp_path: Path) -> None:
        _write(tmp_path / "pyproject.toml", "[project]\nname = 'unknown'\n")
        assert detect_coverage_targets(tmp_path) == ["src"]

    def test_singular_helper_returns_first(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "pyproject.toml",
            "[tool.coverage.run]\nsource = ['first', 'second']\n",
        )
        assert detect_coverage_target(tmp_path) == "first"
