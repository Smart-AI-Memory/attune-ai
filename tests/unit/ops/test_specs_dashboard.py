"""Tests for the `/specs` and `/specs/{slug}` dashboard pages — Phase 3 UI."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402


def _make_spec(root: Path, slug: str, *, files: dict[str, str]) -> Path:
    """Create a spec directory with the given phase files."""
    spec_dir = root / slug
    spec_dir.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (spec_dir / name).write_text(body, encoding="utf-8")
    return spec_dir


def _client(
    tmp_path: Path,
    *,
    specs_roots: tuple[Path, ...] | None = None,
    allow_run: bool = False,
) -> TestClient:
    config = build_config(
        project_root=tmp_path,
        specs_roots=specs_roots,
        allow_run=allow_run,
        trusted_hosts=("testserver", "test"),
    )
    return TestClient(create_app(config))


# ---------------------------------------------------------------------------
# GET /specs — listing page
# ---------------------------------------------------------------------------


def test_specs_page_renders_with_no_specs(tmp_path):
    """No specs → empty-state copy renders without crashing."""
    client = _client(tmp_path, specs_roots=(tmp_path / "empty",), allow_run=True)
    r = client.get("/specs")
    assert r.status_code == 200
    assert "No specs found" in r.text


def test_specs_page_lists_specs_with_status_chips(tmp_path):
    """A spec with a status renders its name + a chip class matching the status."""
    root = tmp_path / "specs"
    _make_spec(
        root,
        "alpha",
        files={
            "decisions.md": "# Alpha\n\n**Status:** approved\n",
            "tasks.md": "**Status:** draft\n",
        },
    )
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)
    r = client.get("/specs")
    assert r.status_code == 200
    assert "alpha" in r.text
    # In read-only mode, statuses render as plain chips (not selects)
    assert "approved" in r.text
    assert "draft" in r.text


def test_specs_page_writeable_mode_shows_editable_pills(tmp_path):
    """allow_run=True → the Stage chip is editable (click-to-edit).

    Earlier versions rendered per-phase pills (PR #358); the Stage
    column replaced them with ONE derived chip that reuses the same
    click-to-edit machinery, pre-targeted at the next-action phase.
    We verify the writeable-mode markers (status-pill-editable class,
    role=button, tabindex, data attributes) are present, and that no
    inline ``<select>`` is rendered until the user clicks the chip.
    """
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"requirements.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)
    r = client.get("/specs")
    assert r.status_code == 200
    # No inline status-edit <select> inside the table body — those are
    # created client-side on pill click. The toolbar's sort <select>
    # (added in A3a) is a navigation control, not a status mutation,
    # so it sits outside <tbody> by construction.
    tbody = r.text.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert "<select" not in tbody
    # Pills carry the writeable markers so specs.js can wire click-to-edit.
    assert "status-pill-editable" in r.text
    assert 'role="button"' in r.text
    assert 'tabindex="0"' in r.text
    # Per-cell data attributes feed the PUT /api/specs/.../status call —
    # the chip targets the NEXT-action phase (unapproved requirements
    # here) with its current status prefilled.
    assert 'data-slug="alpha"' in r.text
    assert 'data-phase="requirements"' in r.text
    assert 'data-original="draft"' in r.text


def test_specs_page_readonly_mode_no_status_dropdowns(tmp_path):
    """allow_run=False → no status-edit dropdowns inside the table body.

    The toolbar's sort <select> (A3a) is always present regardless of
    allow_run — it's a navigation control. What read-only mode forbids
    is per-pill status mutation, which would render as a <select>
    inside the spec table's <tbody>.
    """
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)
    r = client.get("/specs")
    assert r.status_code == 200
    tbody = r.text.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert "<select" not in tbody
    assert "Read-only mode" in r.text


def test_specs_page_shows_em_dash_for_missing_phases(tmp_path):
    """A spec with only tasks.md → missing phases marked in the Stage tooltip.

    The per-phase pills (and their ``chip-muted`` em-dash cells) were
    replaced by the Stage chip; missing phases now render as
    ``<name>: —`` inside the chip's tooltip summary.
    """
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)
    r = client.get("/specs").text
    assert "requirements: —" in r
    assert "design: —" in r
    assert "tasks: draft" in r


def test_specs_page_includes_specs_js_when_writeable(tmp_path):
    """allow_run=True → specs.js loaded."""
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)
    r = client.get("/specs")
    assert "/static/js/specs.js" in r.text


def test_specs_page_omits_specs_js_when_readonly(tmp_path):
    """allow_run=False → specs.js not loaded (no editing possible)."""
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)
    r = client.get("/specs")
    assert "/static/js/specs.js" not in r.text


def test_specs_page_links_to_drill_in(tmp_path):
    """Each spec row links to its drill-in page."""
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)
    r = client.get("/specs")
    assert 'href="/specs/alpha"' in r.text


# ---------------------------------------------------------------------------
# GET /specs/{slug} — drill-in page
# ---------------------------------------------------------------------------


def test_spec_detail_renders_phase_files(tmp_path):
    """The drill-in page shows the body content of each phase file."""
    root = tmp_path / "specs"
    _make_spec(
        root,
        "alpha",
        files={
            "decisions.md": "# Alpha decisions\n\n**Status:** approved\n\nWe decided X.\n",
            "tasks.md": "**Status:** draft\n\n- [ ] Task A\n",
        },
    )
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)
    r = client.get("/specs/alpha")
    assert r.status_code == 200
    assert "We decided X." in r.text
    assert "Task A" in r.text
    assert "approved" in r.text
    assert "draft" in r.text


def test_spec_detail_missing_spec_returns_404(tmp_path):
    """Slugs that don't exist → 404."""
    root = tmp_path / "specs"
    root.mkdir(parents=True)
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)
    r = client.get("/specs/does-not-exist")
    assert r.status_code == 404


@pytest.mark.parametrize("slug", ["../escape", "weird/slash", "back\\slash"])
def test_spec_detail_rejects_path_traversal(tmp_path, slug):
    """Path-traversal slugs return 400 or 404 (FastAPI may reject before handler)."""
    root = tmp_path / "specs"
    root.mkdir(parents=True)
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)
    r = client.get(f"/specs/{slug}")
    assert r.status_code in (400, 404), f"slug={slug!r} got {r.status_code}: {r.text}"


def test_spec_detail_shows_back_link(tmp_path):
    """The drill-in page links back to the listing."""
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)
    r = client.get("/specs/alpha")
    assert r.status_code == 200
    assert 'href="/specs"' in r.text


def test_spec_detail_shows_missing_phase_indicator(tmp_path):
    """Phases that don't exist show a 'missing' chip and don't crash."""
    root = tmp_path / "specs"
    # Only tasks.md exists — decisions/requirements/design are missing.
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)
    r = client.get("/specs/alpha")
    assert r.status_code == 200
    assert "doesn&#39;t exist yet" in r.text or "doesn't exist yet" in r.text


# ---------------------------------------------------------------------------
# Nav integration
# ---------------------------------------------------------------------------


def test_specs_link_in_nav(tmp_path):
    """The Specs tab appears in nav on every page."""
    client = _client(tmp_path, allow_run=False)
    for path in ("/", "/workflows", "/specs", "/telemetry", "/health"):
        r = client.get(path)
        assert r.status_code == 200, f"{path}: {r.status_code}"
        assert 'href="/specs"' in r.text, f"{path}: no Specs nav link"


def test_specs_nav_active_class_set_on_specs_page(tmp_path):
    """The Specs nav link gets is-active when on /specs."""
    client = _client(tmp_path, allow_run=False)
    r = client.get("/specs")
    assert r.status_code == 200
    # Look for the active class somewhere near the Specs link
    assert 'href="/specs" class="nav-link is-active"' in r.text
