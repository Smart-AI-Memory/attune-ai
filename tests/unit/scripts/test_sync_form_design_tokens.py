"""Receipts for the released attune-forms → website token projection."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from scripts.sync_form_design_tokens import JSON_DEST, render_css


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
    assert Path("website/app/semantic-tokens.css").is_file()
    assert Path("website/design/semantic_tokens.json").is_file()
