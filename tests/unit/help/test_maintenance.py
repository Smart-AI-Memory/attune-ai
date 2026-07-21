"""Tests for help/maintenance.py — hook logic and manual refresh."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("yaml")

from attune.help.generator import generate_feature_templates  # noqa: E402
from attune.help.maintenance import (  # noqa: E402
    MaintenanceResult,
    format_status_report,
    get_changed_files,
    run_hook,
    run_maintenance,
)
from attune.help.manifest import Feature, FeatureManifest, save_manifest  # noqa: E402


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a project with source files and .help/ manifest."""
    # Source files
    src = tmp_path / "src" / "auth"
    src.mkdir(parents=True)
    (src / "login.py").write_text("def login(): pass\n", encoding="utf-8")

    src2 = tmp_path / "src" / "api"
    src2.mkdir(parents=True)
    (src2 / "routes.py").write_text("def routes(): pass\n", encoding="utf-8")

    # Manifest
    manifest = FeatureManifest(
        version=1,
        features={
            "auth": Feature(
                name="auth",
                description="Authentication",
                files=["src/auth/**"],
            ),
            "api": Feature(
                name="api",
                description="REST API",
                files=["src/api/**"],
            ),
        },
    )
    help_dir = tmp_path / ".help"
    save_manifest(manifest, help_dir)

    # Generate initial templates
    for feat in manifest.features.values():
        generate_feature_templates(feat, help_dir, tmp_path)

    return tmp_path


class TestRunMaintenance:
    """Tests for run_maintenance()."""

    def test_all_current_no_regeneration(self, project: Path) -> None:
        result = run_maintenance(project / ".help", project)
        assert isinstance(result, MaintenanceResult)
        assert result.stale_count == 0
        assert result.regenerated_count == 0

    def test_detects_and_regenerates_stale(self, project: Path) -> None:
        # Modify source to make auth stale
        (project / "src" / "auth" / "login.py").write_text(
            "def login(user, pw): pass\n", encoding="utf-8"
        )

        result = run_maintenance(project / ".help", project)
        assert result.stale_count == 1
        assert result.regenerated_count == 1
        assert result.regenerated[0].feature == "auth"

    def test_dry_run_does_not_regenerate(self, project: Path) -> None:
        (project / "src" / "auth" / "login.py").write_text(
            "def login(user): pass\n", encoding="utf-8"
        )

        result = run_maintenance(project / ".help", project, dry_run=True)
        assert result.stale_count == 1
        assert result.regenerated_count == 0

    def test_filter_by_feature_names(self, project: Path) -> None:
        # Make both stale
        (project / "src" / "auth" / "login.py").write_text("x=1\n")
        (project / "src" / "api" / "routes.py").write_text("y=2\n")

        result = run_maintenance(project / ".help", project, features=["auth"])
        # Only checks auth
        assert len(result.staleness.entries) == 1
        assert result.staleness.entries[0].feature == "auth"

    def test_missing_manifest_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            run_maintenance(tmp_path / ".help", tmp_path)


class TestGetChangedFiles:
    """Tests for get_changed_files()."""

    def test_returns_empty_outside_git(self, tmp_path: Path) -> None:
        """Non-git directory returns empty list."""
        files = get_changed_files(tmp_path)
        assert files == []

    @patch("attune.help.maintenance.subprocess.run")
    def test_parses_git_output(self, mock_run: object) -> None:
        mock_run.return_value.returncode = 0  # type: ignore[union-attr]
        mock_run.return_value.stdout = (  # type: ignore[union-attr]
            "src/auth/login.py\nsrc/api/routes.py\n"
        )
        files = get_changed_files("/fake")
        assert files == ["src/auth/login.py", "src/api/routes.py"]


class TestRunHook:
    """Tests for run_hook()."""

    def test_returns_none_without_manifest(self, tmp_path: Path) -> None:
        result = run_hook(tmp_path / ".help", tmp_path)
        assert result is None

    @patch("attune.help.maintenance.get_changed_files")
    def test_returns_none_when_no_features_affected(
        self, mock_changed: object, project: Path
    ) -> None:
        mock_changed.return_value = ["README.md"]  # type: ignore[union-attr]
        result = run_hook(project / ".help", project)
        assert result is None

    @patch("attune.help.maintenance.get_changed_files")
    def test_reports_stale_without_regenerating(self, mock_changed: object, project: Path) -> None:
        """Check-only: stale features are reported, never regenerated."""
        # Make auth source stale first
        (project / "src" / "auth" / "login.py").write_text("def login(u): pass\n", encoding="utf-8")
        mock_changed.return_value = ["src/auth/login.py"]  # type: ignore[union-attr]

        template_dir = project / ".help" / "templates" / "auth"
        before = {p: p.read_bytes() for p in sorted(template_dir.rglob("*")) if p.is_file()}

        with patch("attune.help.maintenance.generate_feature_templates") as mock_gen:
            result = run_hook(project / ".help", project)

        assert result is not None
        assert result.stale_count == 1
        assert result.regenerated_count == 0
        mock_gen.assert_not_called()
        after = {p: p.read_bytes() for p in sorted(template_dir.rglob("*")) if p.is_file()}
        assert after == before, "post-commit hook must not write template files"

    @patch("attune.help.maintenance.get_changed_files")
    def test_drift_guard_hook_cannot_reach_regenerating_branch(
        self, mock_changed: object, project: Path
    ) -> None:
        """Regression guard (docs/specs/post-commit-help-check-only).

        The post-commit hook path must never invoke the template
        generator — the per-commit LLM re-polish must not silently
        return. The generator stub raises if reached.
        """
        (project / "src" / "auth" / "login.py").write_text("def login(u): pass\n", encoding="utf-8")
        (project / "src" / "api" / "routes.py").write_text("def routes(x): pass\n")
        mock_changed.return_value = [  # type: ignore[union-attr]
            "src/auth/login.py",
            "src/api/routes.py",
        ]

        def _forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("post-commit hook reached the regenerating branch")

        with patch("attune.help.maintenance.generate_feature_templates", side_effect=_forbidden):
            result = run_hook(project / ".help", project)

        assert result is not None
        assert result.stale_count == 2
        assert result.regenerated_count == 0
        assert result.failed == []


class TestFormatStatusReport:
    """Tests for format_status_report()."""

    def test_all_current(self, project: Path) -> None:
        from attune.help.manifest import load_manifest
        from attune.help.staleness import check_staleness

        manifest = load_manifest(project / ".help")
        report = check_staleness(manifest, project / ".help", project)
        text = format_status_report(report)
        assert "**2** current" in text
        assert "**0** stale" in text

    def test_stale_features_listed(self, project: Path) -> None:
        from attune.help.manifest import load_manifest
        from attune.help.staleness import check_staleness

        (project / "src" / "auth" / "login.py").write_text("x=1\n")
        manifest = load_manifest(project / ".help")
        report = check_staleness(manifest, project / ".help", project)
        text = format_status_report(report)
        assert "**1** stale" in text
        assert "auth" in text


class TestRegenerationFailure:
    """Tests for error paths during regeneration."""

    @patch("attune.help.maintenance.generate_feature_templates")
    def test_regeneration_failure_populates_failed(self, mock_gen: object, project: Path) -> None:
        """OSError during regeneration is caught and recorded."""
        mock_gen.side_effect = OSError("disk full")  # type: ignore[union-attr]

        # Make auth stale so regeneration is attempted
        (project / "src" / "auth" / "login.py").write_text("def login(u): pass\n", encoding="utf-8")

        result = run_maintenance(project / ".help", project)
        assert result.stale_count >= 1
        assert "auth" in result.failed
        assert result.regenerated_count == 0
