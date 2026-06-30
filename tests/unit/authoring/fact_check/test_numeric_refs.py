"""Tests for the numeric-refs check."""

from __future__ import annotations

from pathlib import Path

from attune.authoring.fact_check import numeric_refs
from attune.authoring.fact_check.report import CHECK_NUMERIC_REFS


def _write(tmp_path: Path, body: str) -> Path:
    f = tmp_path / "polished.md"
    f.write_text(body, encoding="utf-8")
    return f


def _scaffold_help_tree(root: Path, template_count: int, feature_count: int) -> None:
    """Create ``.help/templates/`` + ``.help/features.yaml`` with N entries."""
    templates = root / ".help" / "templates"
    templates.mkdir(parents=True)
    for i in range(template_count):
        feat = templates / f"feat-{i}"
        feat.mkdir()
        (feat / "concept.md").write_text("# x\n", encoding="utf-8")
    features = {f"feat-{i}": {"name": f"feat-{i}"} for i in range(feature_count)}
    import yaml

    (root / ".help" / "features.yaml").write_text(
        yaml.safe_dump({"features": features}), encoding="utf-8"
    )


def test_catches_mismatched_template_count(tmp_path: Path) -> None:
    """The ``498 templates`` regression."""
    _scaffold_help_tree(tmp_path, template_count=3, feature_count=2)
    body = "There are 498 templates in this corpus.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert any(
        f.check == CHECK_NUMERIC_REFS
        and f.severity == "error"
        and "498" in f.message
        and "actual count is 3" in f.message
        for f in findings
    )


def test_accepts_correct_feature_count(tmp_path: Path) -> None:
    _scaffold_help_tree(tmp_path, template_count=3, feature_count=2)
    body = "Currently 2 features are tracked.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert not any(f.severity == "error" and "2 features" in f.message for f in findings)


def test_unverifiable_noun_surfaces_warning(tmp_path: Path) -> None:
    """``5 workflows`` has no deterministic resolver — warn the human."""
    _scaffold_help_tree(tmp_path, template_count=1, feature_count=1)
    body = "Ships with 5 workflows.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert any(f.severity == "warning" and "5 workflows" in f.message for f in findings)


def test_no_help_dir_warns_rather_than_errors(tmp_path: Path) -> None:
    """When the consumer has no ``.help/`` tree, resolvers return None.

    The check should NOT spuriously fire an error claiming a count
    mismatch; it should warn so the human can confirm.
    """
    body = "Cap is 11 kinds.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    # No deterministic verifier (or one that returned None) → warning, not error
    assert all(f.severity != "error" for f in findings)
