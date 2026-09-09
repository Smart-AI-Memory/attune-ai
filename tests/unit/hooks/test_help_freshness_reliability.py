"""Real authored projections and standalone help-hook failure receipts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from attune.authoring.projector import project_feature
from attune.authoring.source_introspection import compute_scaffold_hash
from attune.hooks.scripts import help_freshness_nudge as hook

REPO_ROOT = Path(__file__).resolve().parents[3]


def _project(root: Path, feature: str = "security-audit") -> Path:
    """Use the real projector and today's manual-manifest convention."""
    master = root / "content" / "features" / f"{feature}.md"
    master.parent.mkdir(parents=True)
    master.write_text(
        (REPO_ROOT / f"content/features/{feature}.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    project_feature(master, root, root / ".help")
    (root / ".help/features.yaml").write_text(
        f"features:\n  {feature}:\n    status: manual\n", encoding="utf-8"
    )
    return master


def _run_script(root: Path, *, missing_yaml: bool = False) -> subprocess.CompletedProcess:
    """Run unmodified hook/support bytes with __file__ rooted in the fixture."""
    scripts = root / "src" / "attune" / "hooks" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    actual = REPO_ROOT / "src/attune/hooks/scripts"
    for name in ("help_freshness_nudge.py", "_bootstrap.py", "_sdk_gate.py"):
        (scripts / name).write_bytes((actual / name).read_bytes())
    settings = json.loads((REPO_ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    registered_timeout = next(
        item["timeout"]
        for group in settings["hooks"]["SessionStart"]
        for item in group["hooks"]
        if "help_freshness_nudge.py" in item["command"]
    )
    if missing_yaml:
        # Exercise the actual lazy import in the child while keeping its test
        # isolation hooks active (the inference guard disallows Python -S).
        (scripts / "yaml.py").write_text(
            "raise ModuleNotFoundError('PyYAML unavailable in fixture')\n", encoding="utf-8"
        )
    return subprocess.run(
        [sys.executable, str(scripts / "help_freshness_nudge.py")],
        cwd=root,
        env=dict(
            os.environ,
            ATTUNE_SDK_GATE_OVERRIDE="1",
            # Copied hook fixtures intentionally consume this worktree's
            # projector. Preserve the inherited inference-guard bootstrap.
            PYTHONPATH=os.pathsep.join(
                filter(None, [str(REPO_ROOT / "src"), os.environ.get("PYTHONPATH", "")])
            ),
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=registered_timeout,
    )


def test_actual_entrypoint_imports_checkout_projector_without_pythonpath():
    result = subprocess.run(
        [sys.executable, "-v", str(REPO_ROOT / "src/attune/hooks/scripts/help_freshness_nudge.py")],
        cwd=REPO_ROOT,
        # The inference guard prepends its own bootstrap to the empty path;
        # no test-provided src path can hide an installed-wheel import here.
        env=dict(os.environ, ATTUNE_SDK_GATE_OVERRIDE="1", PYTHONPATH=""),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=5,
    )
    expected = str(REPO_ROOT / "src/attune/authoring/projector.py")
    assert expected in result.stderr
    assert "freshness checks unavailable" not in result.stdout


def test_standalone_authored_source_change_ignores_checkout_mtime(tmp_path):
    master = _project(tmp_path)
    baseline = _run_script(tmp_path)
    assert baseline.stdout == baseline.stderr == ""

    # Content, not filesystem age: restored/check-out mtimes must not hide drift.
    master.write_text(master.read_text(encoding="utf-8") + "\nChanged source.\n", encoding="utf-8")
    os.utime(master, (1, 1))
    changed = _run_script(tmp_path)
    assert "1 stale (authored projection drift)" in changed.stdout
    assert changed.stderr == ""
    assert "scripts/project_features.py" in changed.stdout
    assert "attune-author" not in changed.stdout

    project_feature(master, tmp_path, tmp_path / ".help")
    assert _run_script(tmp_path).stdout == ""


def test_actual_source_hash_prose_change_is_detected_even_when_hash_is_equal(tmp_path):
    master = _project(tmp_path, "help-system")
    original = master.read_text(encoding="utf-8")
    edited = original.replace(
        "each with a `source_hash`", "each with a deliberately changed `source_hash`"
    )
    assert edited != original  # Pin the actual prose this regression exercises.
    assert compute_scaffold_hash(edited) == compute_scaffold_hash(original)
    master.write_text(edited, encoding="utf-8")
    assert hook._authored_stale(master, tmp_path / ".help/templates/help-system", tmp_path)
    assert "1 stale (authored projection drift)" in _run_script(tmp_path).stdout


def test_projection_ignores_generated_timestamp_changes(tmp_path):
    master = _project(tmp_path)
    concept = tmp_path / ".help/templates/security-audit/concept.md"
    lines = concept.read_text(encoding="utf-8").splitlines()
    lines = [
        "generated_at: 2099-01-01T00:00:00" if line.startswith("generated_at:") else line
        for line in lines
    ]
    concept.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not hook._authored_stale(master, concept.parent, tmp_path)


def test_checks_other_kinds_when_concept_hash_is_current(tmp_path):
    master = _project(tmp_path)
    reference = tmp_path / ".help/templates/security-audit/reference.md"
    reference.write_text(
        reference.read_text(encoding="utf-8").replace(
            compute_scaffold_hash(master.read_text(encoding="utf-8")), "f" * 64
        ),
        encoding="utf-8",
    )
    assert hook._authored_stale(master, reference.parent, tmp_path)


@pytest.mark.parametrize("removed", ["all", "comparison"])
def test_removed_source_sections_cannot_leave_old_templates_marked_fresh(tmp_path, removed):
    master = _project(tmp_path)
    original = master.read_text(encoding="utf-8")
    if removed == "all":
        edited = "---\nfeature: security-audit\n---\n"
        expected_plan = set()
    else:
        edited = re.sub(r"(?ms)^## Comparison\n.*?(?=^## |\Z)", "", original)
        expected_plan = hook.EXPECTED_KINDS - {"comparison"}
    assert edited != original
    master.write_text(edited, encoding="utf-8")
    plan = project_feature(master, tmp_path, tmp_path / ".help", dry_run=True)
    assert {out.kind for out in plan.outputs if out.target == "help"} == expected_plan
    templates = tmp_path / ".help/templates/security-audit"
    assert {path.stem for path in templates.glob("*.md")} == hook.EXPECTED_KINDS
    assert hook._authored_stale(master, templates, tmp_path)
    assert "1 stale (authored projection drift)" in _run_script(tmp_path).stdout


def test_standalone_glob_failure_preserves_other_findings(tmp_path):
    master = _project(tmp_path)
    master.write_text(master.read_text(encoding="utf-8") + "\nChanged.\n", encoding="utf-8")
    broken = tmp_path / ".help/templates/broken"
    broken.mkdir()
    (broken / "concept.md").write_text("# Existing template\n", encoding="utf-8")
    (tmp_path / ".help/features.yaml").write_text(
        "features:\n  security-audit:\n    status: manual\n"
        "  missing-feature:\n    files: []\n"
        "  broken:\n    files: [/absolute/source.py]\n",
        encoding="utf-8",
    )
    result = _run_script(tmp_path)
    assert "1 missing" in result.stdout
    assert "1 incomplete" in result.stdout
    assert "1 stale (authored projection drift)" in result.stdout
    assert "1 freshness checks unavailable: broken (ValueError)" in result.stdout
    assert result.stderr == ""


@pytest.mark.parametrize("manifest", [b"features: [broken", b"\xff"])
def test_standalone_unreadable_manifest_keeps_completeness(tmp_path, manifest):
    _project(tmp_path)
    (tmp_path / ".help/templates/security-audit/reference.md").unlink()
    (tmp_path / ".help/features.yaml").write_bytes(manifest)
    result = _run_script(tmp_path)
    assert "manifest check unavailable" in result.stdout
    assert "1 incomplete" in result.stdout
    assert "orphan" not in result.stdout  # Unknown manifest is not an empty one.
    assert result.stderr == ""


def test_standalone_missing_yaml_is_visible_and_nonblocking(tmp_path):
    _project(tmp_path)
    result = _run_script(tmp_path, missing_yaml=True)
    assert "manifest check unavailable (ModuleNotFoundError" in result.stdout
    assert result.stderr == ""


def test_yaml_quotes_comments_and_inline_collections_are_resolved(tmp_path):
    _project(tmp_path)
    (tmp_path / ".help/features.yaml").write_text(
        'features:\n  memory:\n    files: ["source.py"] # valid YAML\n', encoding="utf-8"
    )
    assert hook._load_manifest(tmp_path / ".help") == {"memory": ["source.py"]}


@pytest.mark.parametrize(
    "manifest",
    [
        "[]",
        "features: []",
        "features: {'../escape': {}}",
        "features: {memory: []}",
        "features: {memory: {files: source.py}}",
        "features: {memory: {files: [123]}}",
    ],
)
def test_invalid_manifest_schema_is_not_silently_accepted(tmp_path, manifest):
    (tmp_path / "features.yaml").write_text(manifest, encoding="utf-8")
    with pytest.raises(ValueError):
        hook._load_manifest(tmp_path)


@pytest.mark.parametrize("pattern", ["../outside.py", "missing/*.py"])
def test_legacy_sources_without_safe_matches_are_unavailable(tmp_path, pattern):
    _project(tmp_path)
    findings = hook._freshness_findings({"security-audit": [pattern]}, tmp_path)
    assert findings == []  # Authored source takes precedence over legacy patterns.
    (tmp_path / "content/features/security-audit.md").unlink()
    findings = hook._freshness_findings({"security-audit": [pattern]}, tmp_path)
    assert "freshness checks unavailable" in findings[0]


def test_missing_authored_source_is_unavailable(tmp_path):
    master = _project(tmp_path)
    master.unlink()
    result = _run_script(tmp_path)
    assert "freshness checks unavailable" in result.stdout


def test_template_without_source_metadata_is_drifted(tmp_path):
    master = _project(tmp_path)
    concept = tmp_path / ".help/templates/security-audit/concept.md"
    concept.write_text("---\ntype: concept\n---\n# Text\n", encoding="utf-8")
    assert hook._authored_stale(master, concept.parent, tmp_path)
    assert "stale (authored projection drift)" in _run_script(tmp_path).stdout


@pytest.mark.parametrize("linked", ["directory", "concept"])
@pytest.mark.parametrize("foreign_mtime", [1, 10000])
def test_legacy_template_symlinks_are_rejected_before_using_mtimes(tmp_path, linked, foreign_mtime):
    repo = tmp_path / "repo"
    templates = repo / ".help/templates"
    templates.mkdir(parents=True)
    outside = tmp_path / "foreign-templates"
    outside.mkdir()
    for kind in hook.EXPECTED_KINDS:
        (outside / f"{kind}.md").write_text("# foreign template\n", encoding="utf-8")
    foreign_concept = outside / "concept.md"
    os.utime(foreign_concept, (foreign_mtime, foreign_mtime))
    (repo / "source.py").write_text("# current source\n", encoding="utf-8")
    os.utime(repo / "source.py", (5000, 5000))
    (repo / ".help/features.yaml").write_text(
        "features:\n  legacy:\n    files: [source.py]\n", encoding="utf-8"
    )
    try:
        if linked == "directory":
            (templates / "legacy").symlink_to(outside, target_is_directory=True)
        else:
            (templates / "legacy").mkdir()
            for kind in hook.EXPECTED_KINDS - {"concept"}:
                (templates / "legacy" / f"{kind}.md").write_text("# local\n", encoding="utf-8")
            (templates / "legacy/concept.md").symlink_to(foreign_concept)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    result = _run_script(repo)
    assert "1 freshness checks unavailable: legacy (ValueError)" in result.stdout
    assert "stale (mtime hint)" not in result.stdout


@pytest.mark.parametrize("artifact", ["master", "template", "legacy-source"])
def test_outside_symlinks_cannot_supply_freshness_evidence(tmp_path, artifact):
    repo = tmp_path / "repo"
    master = _project(repo)
    outside = tmp_path / "outside.md"
    outside.write_text(master.read_text(encoding="utf-8"), encoding="utf-8")
    path = {
        "master": master,
        "template": repo / ".help/templates/security-audit/concept.md",
        "legacy-source": repo / "source.py",
    }[artifact]
    if path.exists():
        path.unlink()
    if artifact == "legacy-source":
        master.unlink()
    try:
        path.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    findings = hook._freshness_findings({"security-audit": ["source.py"]}, repo)
    assert "freshness checks unavailable" in findings[0]


def test_diagnostic_sanitizes_and_bounds_failure_text():
    message = hook._check_error("manifest check", ValueError("bad\n" * 500))
    assert "\n" not in message
    assert len(message) < 220
