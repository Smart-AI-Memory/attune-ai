#!/usr/bin/env python
"""SessionStart hook: surface .help/ freshness and completeness issues.

Runs quickly (<2s) and prints a short summary to stdout when any of:

    1. Manifest features have missing directories or template kinds (< 11)
    2. Template directories exist that aren't in the manifest (orphans)
    3. Authored templates differ from a fresh deterministic projection
    4. Legacy source files are newer than concept.md (coarse mtime hint)

Authored checks use the existing projector in dry-run mode and compare help
outputs with generated timestamps normalized. No files are regenerated.
PyYAML and the projector are loaded lazily; missing dependencies and failed
checks produce a bounded diagnostic.

Output is informational only. Exit code is always 0 so the session starts
normally.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _read_repo_text(path: Path, repo_root: Path) -> str:
    """Read a local artifact only when its resolved path stays in the repo."""
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(repo_root.resolve()):
        raise ValueError("artifact resolves outside the repository")
    return resolved.read_text(encoding="utf-8")


def _yaml_mapping(text: str) -> dict:
    """Parse YAML without silently treating unsupported syntax as empty."""
    import yaml

    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError("invalid YAML") from exc
    if not isinstance(value, dict):
        raise ValueError("expected a YAML mapping")
    return value


def _load_manifest(help_dir: Path) -> dict[str, list[str]]:
    """Read feature names and source patterns using the manifest's YAML schema."""
    raw = _yaml_mapping(_read_repo_text(help_dir / "features.yaml", help_dir.parent))
    specs = raw.get("features")
    if not isinstance(specs, dict):
        raise ValueError("features must be a mapping")
    features: dict[str, list[str]] = {}
    for name, spec in specs.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", name):
            raise ValueError("invalid feature name")
        if not isinstance(spec, dict):
            raise ValueError(f"{name}: expected a feature mapping")
        patterns = spec.get("files", [])
        if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
            raise ValueError(f"{name}: files must be a list of strings")
        features[name] = patterns
    return features


EXPECTED_KINDS = {
    "concept",
    "task",
    "reference",
    "error",
    "warning",
    "troubleshooting",
    "faq",
    "quickstart",
    "tip",
    "note",
    "comparison",
}


def _coarse_staleness(
    manifest: dict[str, list[str]], repo_root: Path, templates_dir: Path
) -> list[str]:
    stale: list[str] = []
    resolved_root = repo_root.resolve()
    for feature, globs in manifest.items():
        feature_dir = templates_dir / feature
        if not feature_dir.resolve().is_relative_to(resolved_root):
            raise ValueError("template directory resolves outside the repository")
        concept = feature_dir / "concept.md"
        if not concept.is_file():
            continue
        if not concept.resolve().is_relative_to(resolved_root):
            raise ValueError("concept template resolves outside the repository")
        concept_mtime = concept.stat().st_mtime
        newest_src = 0.0
        matched = False
        for pattern in globs:
            if Path(pattern).anchor or ".." in Path(pattern).parts:
                raise ValueError("source pattern must stay inside the repository")
            for path in repo_root.glob(pattern):
                if path.is_file():
                    if not path.resolve().is_relative_to(resolved_root):
                        raise ValueError("source resolves outside the repository")
                    matched = True
                    newest_src = max(newest_src, path.stat().st_mtime)
        if globs and not matched:
            raise ValueError("source patterns matched no files")
        if newest_src > concept_mtime:
            stale.append(feature)
    return stale


def _authored_stale(master: Path, templates: Path, repo_root: Path) -> bool:
    """Compare help output with a dry run of the canonical authored projector.

    Source hashes alone omit prose lines containing metadata tokens. Comparing
    the projected body catches those edits and direct template edits as well.
    """
    from attune.authoring.projector import normalize_generated_stamps, project_feature

    _read_repo_text(master, repo_root)  # Validate containment before the projector reads it.
    result = project_feature(master, repo_root, templates.parent.parent, dry_run=True)
    planned_kinds = {output.kind for output in result.outputs if output.target == "help"}
    # Removed source sections can leave old templates behind: a partial/empty
    # plan does not establish freshness for the required eleven kinds.
    stale = planned_kinds != EXPECTED_KINDS
    for output in result.outputs:
        if output.target != "help":
            continue
        if output.path.parent != templates:
            raise ValueError("authored feature name does not match the manifest")
        if not output.path.is_file():
            continue  # The completeness check reports missing kinds.
        text = _read_repo_text(output.path, repo_root)
        stale = stale or normalize_generated_stamps(text) != normalize_generated_stamps(
            output.content
        )
    return stale


def _structural_findings(manifest: dict | None, templates_dir: Path) -> list[str]:
    """Check existing templates even when the manifest cannot be read."""
    if not templates_dir.is_dir():
        return [f"{len(manifest)} missing" if manifest else "templates directory missing"]
    on_disk = {p.name for p in templates_dir.iterdir() if p.is_dir()}
    names = set(manifest) if manifest is not None else on_disk
    bits = []
    if names - on_disk:
        bits.append(f"{len(names - on_disk)} missing")
    if manifest is not None and on_disk - names:
        bits.append(f"{len(on_disk - names)} orphan")
    incomplete: list[str] = []
    for feat in sorted(names & on_disk):
        present = {p.stem for p in (templates_dir / feat).glob("*.md") if p.is_file()}
        if EXPECTED_KINDS - present:
            incomplete.append(feat)
    if incomplete:
        bits.append(f"{len(incomplete)} incomplete")
    return bits


def _freshness_findings(manifest: dict[str, list[str]], repo_root: Path) -> list[str]:
    """Isolate failures per feature so completed checks remain visible."""
    authored, legacy, unavailable = [], [], []
    templates_dir = repo_root / ".help" / "templates"
    for feature, patterns in manifest.items():
        if not (templates_dir / feature).is_dir():
            continue  # Already reported missing by the structural check.
        master = repo_root / "content" / "features" / f"{feature}.md"
        try:
            if master.is_file():
                if _authored_stale(master, templates_dir / feature, repo_root):
                    authored.append(feature)
            elif patterns:
                legacy.extend(_coarse_staleness({feature: patterns}, repo_root, templates_dir))
            else:
                raise ValueError("no authored master or legacy sources")
        except (OSError, ValueError, ImportError, NotImplementedError) as exc:
            unavailable.append(f"{feature[:60]} ({type(exc).__name__})")
    bits = []
    if authored:
        bits.append(f"{len(authored)} stale (authored projection drift)")
    if legacy:
        bits.append(f"{len(legacy)} stale (mtime hint)")
    if unavailable:
        bits.append(
            f"{len(unavailable)} freshness checks unavailable: {', '.join(unavailable[:3])}"
        )
    return bits


def _check_error(check: str, exc: Exception) -> str:
    """Keep degradation diagnostics on one bounded line."""
    detail = " ".join(str(exc).split())[:160]
    return f"{check} unavailable ({type(exc).__name__}: {detail})"


def main() -> int:
    """Surface independent completeness and source-freshness findings."""
    repo_root = _repo_root()
    help_dir = repo_root / ".help"
    if not help_dir.is_dir():
        return 0
    bits = []
    manifest = None
    try:
        manifest = _load_manifest(help_dir)
    except (OSError, ValueError, ImportError) as exc:
        bits.append(_check_error("manifest check", exc))
    try:
        bits.extend(_structural_findings(manifest, help_dir / "templates"))
    except OSError as exc:
        bits.append(_check_error("completeness check", exc))
    structural_reported = bool(bits)
    if bits:
        print(f"[.help] {', '.join(bits)}", flush=True)
    bits = []
    if manifest is not None:
        bits.extend(_freshness_findings(manifest, repo_root))
    if bits:
        print(f"[.help] {', '.join(bits)}")
    if structural_reported or bits:
        print("        Inspect .help/features.yaml; re-project authored features with")
        print(
            "        `python scripts/project_features.py <feature>`; `/coach maintain` for legacy help."
        )
    return 0


if __name__ == "__main__":
    from _bootstrap import ensure_repo_src_on_path, ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    ensure_repo_src_on_path()
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: SessionStart continues, but a failed check stays visible.
        print(f"[.help] {_check_error('hook check', exc)}", file=sys.stderr)
        sys.exit(0)
