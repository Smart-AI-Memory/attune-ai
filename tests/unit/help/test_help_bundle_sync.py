"""Tests for Design B — single-source content emitted into the bundle.

`scripts/sync_help_bundle.py` projects each single-sourced feature's
`.help/templates/<F>/<kind>.md` into the served bundle
(`plugin/help/generated/<type>/<F>.md`) so a clean plugin/uvx install —
which ships only the bundle, not `.help/templates/<F>/` — serves the
grounded content. These tests guard against drift and prove bundle
resolution works without the dev-checkout fallback.

Spec: docs/specs/help-serving-bridge/ (decision D5).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_BUNDLE = _REPO / "plugin" / "help" / "generated"
sys.path.insert(0, str(_REPO / "scripts"))

import sync_help_bundle as shb  # noqa: E402

from attune.help.templates import populate  # noqa: E402


def _plan():
    features = shb._single_sourced_features(_REPO / ".help" / "features.yaml")
    return shb._planned_outputs(_REPO, features)


def test_bundle_in_sync_with_single_source():
    """Every single-source kind is emitted to the bundle and current.

    Fails if a feature master changed without re-running
    `scripts/sync_help_bundle.py` — the drift guard.
    """
    stale = []
    for src, dest, feature, tags in _plan():
        rendered = shb._render_bundle_file(src, feature, tags)
        if not dest.exists() or dest.read_text(encoding="utf-8") != rendered:
            stale.append(str(dest.relative_to(_REPO)))
    assert not stale, (
        f"{len(stale)} bundle file(s) out of sync — run "
        f"scripts/sync_help_bundle.py: {stale[:5]}"
    )


def test_single_source_resolves_from_bundle_without_fallback(tmp_path):
    """A clean bundle (no .help sibling) still serves single-source content.

    Copies the bundle to a non-canonical path so the D1 dev-checkout
    fallback cannot fire, then asserts resolution — this is what a clean
    `uvx`/plugin install sees.
    """
    clean = tmp_path / "generated"
    shutil.copytree(_BUNDLE, clean)

    # Sanity: the fallback must be inactive for this path.
    assert shb_templates_dir_inactive(clean)

    for feature in ("help-system", "ops-dashboard", "security-audit"):
        result = populate(f"con-{feature}", generated_dir=clean)
        assert result is not None, f"con-{feature} not in bundle"
        assert result.body.strip()


def shb_templates_dir_inactive(path: Path) -> bool:
    """True when the resolver fallback is NOT active for *path*."""
    from attune.help.templates import _templates_dir_for

    return _templates_dir_for(path) is None


def test_planned_outputs_cover_known_features():
    """The plan includes the canonical single-sourced features."""
    dests = {d.name for _, d, _, _ in _plan()}
    # every feature emits a concept named <feature>.md
    assert "help-system.md" in dests
    assert "ops-dashboard.md" in dests
