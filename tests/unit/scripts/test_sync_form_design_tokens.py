"""Receipts for the released attune-forms → website token projection."""

from __future__ import annotations

import json
from importlib.resources import files

from scripts.sync_form_design_tokens import (
    CSS_DEST,
    JSON_DEST,
    ROOT,
    _projection_is_stale,
    _version_tuple,
    render_css,
)


def test_tracked_projection_matches_released_attune_forms() -> None:
    tracked = json.loads(JSON_DEST.read_text(encoding="utf-8"))
    released = json.loads(
        files("attune_forms").joinpath("semantic_tokens.json").read_text(encoding="utf-8")
    )
    assert tracked == released


def test_generated_css_projects_every_color_role_for_both_modes() -> None:
    tokens = json.loads(JSON_DEST.read_text(encoding="utf-8"))
    css = render_css(tokens, "0.9.0")
    for mode in ("light", "dark"):
        for value in tokens["color"][mode].values():
            assert value in css
    assert "prefers-color-scheme: dark" in css
    assert "--semantic-target-min: 2.5rem" in css


def test_projection_files_are_runtime_static_assets() -> None:
    assert CSS_DEST.is_file()
    assert JSON_DEST.is_file()


def test_prerelease_version_is_compared_by_release_segment() -> None:
    assert _version_tuple("0.9.0rc1") == (0, 9, 0)


def test_missing_projection_is_stale_instead_of_raising(tmp_path) -> None:
    assert _projection_is_stale(tmp_path / "missing.css", "expected")


def test_website_adapter_preserves_control_and_surface_semantics() -> None:
    css = (ROOT / "website/app/globals.css").read_text(encoding="utf-8")
    assert 'input:not([type="checkbox"]):not([type="radio"]):not([type="range"])' in css
    assert css.count("--secondary-dark: #3db57e;") == 2
    assert css.count("--surface-container-low: var(--semantic-surface-raised);") == 3
