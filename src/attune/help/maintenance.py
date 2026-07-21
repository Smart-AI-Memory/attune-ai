"""Help maintenance logic for commit hooks and manual refresh.

Ties together manifest, staleness, and generator modules to
detect which features need help updates and regenerate their
templates. Used by both the post-commit hook and the
/coach maintain command.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from attune.help.generator import GenerationResult, generate_feature_templates
from attune.help.manifest import (
    load_manifest,
    match_files_to_features,
)
from attune.help.staleness import StalenessReport, check_staleness

logger = logging.getLogger(__name__)


@dataclass
class MaintenanceResult:
    """Result of a help maintenance run.

    Attributes:
        staleness: Full staleness report.
        regenerated: Features whose templates were regenerated.
        skipped_manual: Features skipped (status: manual).
        failed: Features that failed to regenerate.
    """

    staleness: StalenessReport
    regenerated: list[GenerationResult] = field(default_factory=list)
    skipped_manual: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def stale_count(self) -> int:
        """Number of stale features detected."""
        return self.staleness.stale_count

    @property
    def regenerated_count(self) -> int:
        """Number of features regenerated."""
        return len(self.regenerated)


def run_maintenance(
    help_dir: str | Path,
    project_root: str | Path,
    features: list[str] | None = None,
    dry_run: bool = False,
) -> MaintenanceResult:
    """Run help maintenance — check staleness and regenerate.

    Args:
        help_dir: Path to the .help/ directory.
        project_root: Project root for resolving globs.
        features: Optional list of feature names to check.
            If None, checks all features.
        dry_run: If True, report staleness without regenerating.

    Returns:
        MaintenanceResult with staleness and regeneration info.

    Raises:
        FileNotFoundError: If features.yaml doesn't exist.
    """
    manifest = load_manifest(help_dir)
    report = check_staleness(manifest, help_dir, project_root, features)

    result = MaintenanceResult(staleness=report)

    # Single-sourced (status: manual) features are excluded from the
    # staleness report by check_staleness; surface them here so a run
    # reports what it deliberately left alone instead of silently.
    candidates = features if features else list(manifest.features.keys())
    result.skipped_manual = [
        name
        for name in candidates
        if (feat := manifest.features.get(name)) is not None and feat.is_manual
    ]

    if dry_run or report.stale_count == 0:
        return result

    for entry in report.entries:
        if not entry.is_stale:
            continue

        feat = manifest.features.get(entry.feature)
        if not feat:
            continue

        try:
            gen_result = generate_feature_templates(
                feature=feat,
                help_dir=help_dir,
                project_root=project_root,
            )
            result.regenerated.append(gen_result)
            logger.info(
                "Regenerated %d templates for '%s'",
                len(gen_result.templates),
                entry.feature,
            )
        except OSError as e:
            logger.error(
                "Failed to regenerate '%s': %s",
                entry.feature,
                e,
            )
            result.failed.append(entry.feature)

    return result


def get_changed_files(project_root: str | Path) -> list[str]:
    """Get files changed in the most recent commit.

    Uses git diff to find changed files. Returns relative
    paths from the project root.

    Args:
        project_root: Project root directory.

    Returns:
        List of relative file paths changed in HEAD.
    """
    try:
        output = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if output.returncode != 0:
            logger.debug("git diff failed: %s", output.stderr)
            return []
        return [line.strip() for line in output.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.debug("Cannot get changed files: %s", e)
        return []


def run_hook(
    help_dir: str | Path,
    project_root: str | Path,
) -> MaintenanceResult | None:
    """Post-commit hook entry point — check-only.

    Gets changed files from the latest commit, matches them
    against the feature manifest, and reports staleness for
    affected features. Never regenerates templates: hooks must
    not spend LLM budget or write to the working tree
    (docs/specs/post-commit-help-check-only). Regeneration
    happens only at release-prep cadence via /coach maintain.

    Args:
        help_dir: Path to the .help/ directory.
        project_root: Project root directory.

    Returns:
        MaintenanceResult (staleness report only) if any
        features were affected, None if the manifest doesn't
        exist or no features matched.
    """
    help_path = Path(help_dir)
    if not (help_path / "features.yaml").exists():
        return None

    changed = get_changed_files(project_root)
    if not changed:
        return None

    try:
        manifest = load_manifest(help_dir)
    except (FileNotFoundError, ValueError) as e:
        logger.warning("Cannot load manifest: %s", e)
        return None

    affected = match_files_to_features(changed, manifest)
    if not affected:
        return None

    affected_names = list(affected.keys())
    logger.info(
        "Commit touches %d feature(s): %s",
        len(affected_names),
        ", ".join(affected_names),
    )

    return run_maintenance(
        help_dir=help_dir,
        project_root=project_root,
        features=affected_names,
        dry_run=True,
    )


def format_status_report(
    report: StalenessReport,
    help_dir: str | Path | None = None,
) -> str:
    """Format a staleness report for display.

    Args:
        report: The staleness report to format.
        help_dir: Path to .help/ directory for preamble lookup.

    Returns:
        Markdown-formatted status report.
    """
    from attune.help.preamble import get_preamble

    lines = ["## Help Status\n"]
    lines.append(f"**{report.current_count}** current, " f"**{report.stale_count}** stale\n")

    if report.stale_count > 0:
        lines.append("### Stale Features\n")
        lines.append("| Feature | Description | Files Changed |\n")
        lines.append("|---------|-------------|---------------|\n")
        for entry in report.entries:
            if entry.is_stale:
                count = len(entry.matched_files)
                preamble = get_preamble(entry.feature, help_dir) or ""
                lines.append(f"| {entry.feature} | {preamble} | {count} source files |\n")
        lines.append("")

    if report.current_count > 0:
        lines.append("### Current Features\n")
        for entry in report.entries:
            if not entry.is_stale:
                preamble = get_preamble(entry.feature, help_dir) or ""
                if preamble:
                    lines.append(f"- **{entry.feature}** — {preamble}\n")
                else:
                    lines.append(f"- {entry.feature}\n")
        lines.append("")

    return "\n".join(lines)
