"""Workflow templates (third-consumer expansion, D3): registration
coverage, bound validation, code-derived option pins, poor-fit
absence, and buildability of every registered template."""

from __future__ import annotations

from pathlib import Path

import pytest

import attune.elicitation.workflow_templates as wt
from attune.elicitation.intake_template import (
    TEMPLATES,
    ProviderContext,
    build_form,
    validate_template,
)

_CTX = ProviderContext(repo_root=Path("/nonexistent"))

_RICH = ("deep-review", "discovery-sweep", "secure-release", "test-audit")


def _stub_overrides(template) -> dict[str, list[str]]:
    return {
        slot.key: ["candidate-a", "candidate-b"]
        for slot in template.fields
        if slot.provider is not None
    }


def test_standard_family_registered_and_bound() -> None:
    for name, budget_key in wt.STANDARD_ANALYSIS.items():
        template = TEMPLATES[name]
        assert template.workflow == name
        keys = [s.key for s in template.fields]
        assert keys[:2] == ["path", "depth"]
        if budget_key:
            assert budget_key in keys
        else:
            assert len(keys) == 2


def test_rich_candidates_registered_and_bound() -> None:
    for name in _RICH:
        assert TEMPLATES[name].workflow == name


def test_poor_fits_deliberately_absent() -> None:
    for name in wt.POOR_FITS:
        assert name not in TEMPLATES


@pytest.mark.parametrize(
    "name",
    sorted(set(wt.STANDARD_ANALYSIS) | set(_RICH)),
)
def test_every_registered_template_validates_and_builds(name: str) -> None:
    """Bound validation (tighten-only, list-needs-provider) runs
    against the REAL registry schema for every template, and the
    form builds with stubbed candidates."""
    template = TEMPLATES[name]
    validate_template(template)
    form = build_form(template, _CTX, candidates_override=_stub_overrides(template))
    assert [q.id for q in form.questions] == [s.key for s in template.fields]


def test_depth_options_pin_the_workflow_vocabulary() -> None:
    assert wt.DEPTH_OPTIONS == ["quick", "standard", "deep"]


def test_deep_review_focus_matches_workflow_valid_set() -> None:
    """Pin against the literal set in deep_review.py — if the
    workflow's valid_focus changes, this template must follow."""
    from attune.workflows import deep_review

    source = Path(deep_review.__file__).read_text()
    focus = wt._provider_deep_review_focus(_CTX)
    for value in focus:
        assert f'"{value}"' in source
    assert 'valid_focus = {"security", "quality", "test-gaps"}' in source


def test_sweep_sources_derive_from_live_adapter_registry() -> None:
    names = wt._provider_sweep_sources(_CTX)
    assert names, "adapter registry unexpectedly empty"
    from attune.workflows.discovery_sweep.cli_workflow import default_sources

    assert names == [s.name for s in default_sources()]


def test_changed_files_provider_filters_to_files(tmp_path: Path) -> None:
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    pkg = repo / "src"
    pkg.mkdir()
    (pkg / "mod.py").write_text("X = 1\n")
    ctx = ProviderContext(repo_root=repo)
    files = wt._provider_changed_files(ctx)
    assert "src/mod.py" in files
    assert "src" not in files


def test_cold_import_serves_workflow_templates(tmp_path: Path) -> None:
    import subprocess
    import sys

    code = (
        "from attune.elicitation.intake_template import intake_form\n"
        "from pathlib import Path\n"
        "assert intake_form('code-review', repo_root=Path('.')) is not None\n"
        "assert intake_form('discovery-sweep', repo_root=Path('.')) is not None\n"
        "assert intake_form('doc-orchestrator', repo_root=Path('.')) is None\n"
        "print('cold-ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "cold-ok" in proc.stdout
