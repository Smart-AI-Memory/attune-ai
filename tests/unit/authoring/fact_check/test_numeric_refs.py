"""Tests for the numeric-refs check."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_missing_templates_dir_warns(tmp_path: Path) -> None:
    """``.help/`` exists but ``.help/templates/`` does not — ``_count_templates``
    returns ``None`` and the claim surfaces as a warning, not an error."""
    (tmp_path / ".help").mkdir()
    body = "There are 7 templates available.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert any(f.severity == "warning" and "7 templates" in f.message for f in findings)
    assert not any(f.severity == "error" for f in findings)


def test_missing_features_yaml_warns(tmp_path: Path) -> None:
    """``.help/`` exists but ``features.yaml`` does not — ``_count_features``
    returns ``None`` and the claim surfaces as a warning, not an error."""
    (tmp_path / ".help").mkdir()
    body = "Ships with 9 features today.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert any(f.severity == "warning" and "9 features" in f.message for f in findings)
    assert not any(f.severity == "error" for f in findings)


def test_features_yaml_invalid_utf8_warns(tmp_path: Path) -> None:
    """A ``features.yaml`` that isn't valid UTF-8 raises ``UnicodeDecodeError``
    (a ``ValueError`` subclass) from ``read_text`` — caught and treated as
    unresolvable rather than propagating."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_bytes(b"\xff\xfe\x00bogus")
    body = "Tracking 4 features currently.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert any(f.severity == "warning" and "4 features" in f.message for f in findings)
    assert not any(f.severity == "error" for f in findings)


def test_features_yaml_top_level_list_warns(tmp_path: Path) -> None:
    """A ``features.yaml`` whose top level parses to a list (not a mapping)
    is not a valid features document — ``_count_features`` returns ``None``."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text("- one\n- two\n", encoding="utf-8")
    body = "There are 2 features.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert any(f.severity == "warning" and "2 features" in f.message for f in findings)
    assert not any(f.severity == "error" for f in findings)


def test_features_yaml_features_key_is_list(tmp_path: Path) -> None:
    """When ``features:`` maps to a list, the count is the list length."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text(
        "features:\n  - alpha\n  - beta\n  - gamma\n", encoding="utf-8"
    )
    body = "There are 3 features documented.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert not any(f.severity == "error" and "3 features" in f.message for f in findings)

    mismatch_body = "There are 9 features documented.\n"
    mismatch_findings = numeric_refs.check(_write(tmp_path, mismatch_body), tmp_path)
    assert any(
        f.severity == "error" and "actual count is 3" in f.message for f in mismatch_findings
    )


def test_features_yaml_features_key_is_scalar_warns(tmp_path: Path) -> None:
    """When ``features:`` maps to neither a dict nor a list (a bare scalar),
    ``_count_features`` cannot derive a count and returns ``None``."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text("features: 5\n", encoding="utf-8")
    body = "There are 5 features documented.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert any(f.severity == "warning" and "5 features" in f.message for f in findings)
    assert not any(f.severity == "error" for f in findings)


def test_count_kinds_resolves_when_kinds_importable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``attune.authoring.source_introspection.KINDS`` is importable
    and sized, ``_count_kinds`` reports its length and mismatches surface
    as errors (not warnings)."""
    from attune.authoring import source_introspection

    monkeypatch.setattr(source_introspection, "KINDS", ["a", "b", "c"], raising=False)
    body = "Cap is 3 kinds.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert not any(f.severity == "error" and "3 kinds" in f.message for f in findings)

    mismatch_body = "Cap is 9 kinds.\n"
    mismatch_findings = numeric_refs.check(_write(tmp_path, mismatch_body), tmp_path)
    assert any(
        f.severity == "error" and "actual count is 3" in f.message for f in mismatch_findings
    )


def test_count_kinds_typeerror_warns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When ``KINDS`` is importable but not sized (``len()`` raises
    ``TypeError``), ``_count_kinds`` falls back to ``None`` and the claim
    surfaces as a warning rather than raising."""
    from attune.authoring import source_introspection

    monkeypatch.setattr(source_introspection, "KINDS", object(), raising=False)
    body = "Cap is 11 kinds.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    assert any(f.severity == "warning" and "11 kinds" in f.message for f in findings)
    assert not any(f.severity == "error" for f in findings)


def test_duplicate_claim_deduped_across_lines(tmp_path: Path) -> None:
    """The same ``(noun, count)`` claim repeated in the document is only
    reported once — the ``seen`` set skips subsequent occurrences."""
    _scaffold_help_tree(tmp_path, template_count=3, feature_count=2)
    body = "There are 498 templates.\nAgain, 498 templates total.\n"
    findings = numeric_refs.check(_write(tmp_path, body), tmp_path)
    matches = [f for f in findings if "498" in f.message]
    assert len(matches) == 1
