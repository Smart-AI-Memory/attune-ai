"""Tests for the help-serving bridge (D1 resolver fallback).

The in-conversation help surface resolves a template ID against the
type-organized bundle (plugin/help/generated) first, then falls back to
the single-source layout (.help/templates/<feature>/<kind>.md). These
tests pin that behavior and guard against regressing bundle-only IDs.

Spec: docs/specs/help-serving-bridge/ (decisions D1).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.help.templates import (
    _DEFAULT_TEMPLATES_DIR,
    _PREFIX_TO_KIND,
    _find_single_source_file,
    _find_template_file,
    _templates_dir_for,
    populate,
)

_BUNDLE = Path(__file__).resolve().parents[3] / "plugin" / "help" / "generated"


def _has_single_source(feature: str) -> bool:
    """True when the single-source concept for *feature* exists."""
    return (_DEFAULT_TEMPLATES_DIR / feature / "concept.md").exists()


def test_fallback_serves_single_source_feature():
    """populate() serves single-source content absent from the bundle."""
    if not _has_single_source("help-system"):
        pytest.skip("single-source help-system not present")

    result = populate("con-help-system")

    assert result is not None
    assert result.body.strip()


def test_fallback_covers_all_kinds():
    """Every projected kind resolves through the fallback."""
    feature = "help-system"
    if not _has_single_source(feature):
        pytest.skip("single-source help-system not present")

    feature_dir = _DEFAULT_TEMPLATES_DIR / feature
    prefix_for_kind = {kind: prefix for prefix, kind in _PREFIX_TO_KIND.items()}

    for kind_file in feature_dir.glob("*.md"):
        prefix = prefix_for_kind.get(kind_file.stem)
        if prefix is None:
            continue
        assert populate(f"{prefix}-{feature}") is not None, kind_file.stem


def test_bundle_ids_still_resolve():
    """Bundle-only IDs keep resolving — no fallback regression."""
    # progressive-depth is a hand-curated system concept that exists
    # only in the bundle, never in the single-source layout.
    if not (_BUNDLE / "concepts" / "progressive-depth.md").exists():
        pytest.skip("bundle concept not present")

    assert populate("con-progressive-depth") is not None


def test_unknown_id_returns_none():
    """An ID matching neither source resolves to None."""
    assert populate("con-definitely-not-a-real-feature-xyz") is None


def test_custom_generated_dir_has_no_implicit_fallback(tmp_path):
    """A non-canonical bundle dir gets no surprise .help/templates fallback."""
    # tmp_path is not <root>/plugin/help/generated, so no fallback applies.
    assert _templates_dir_for(tmp_path) is None
    assert _find_template_file("con-help-system", tmp_path) is None


def test_templates_dir_derived_for_canonical_bundle():
    """The canonical bundle layout derives the paired templates dir."""
    derived = _templates_dir_for(_BUNDLE)
    assert derived is not None
    assert derived == _DEFAULT_TEMPLATES_DIR


def test_fallback_blocks_path_traversal():
    """A traversing feature name cannot escape the templates dir."""
    assert _find_single_source_file("con", "../../../etc/passwd", _BUNDLE) is None


def test_unknown_prefix_has_no_fallback():
    """An unmapped prefix yields no single-source path."""
    assert _find_single_source_file("zzz", "help-system", _BUNDLE) is None
