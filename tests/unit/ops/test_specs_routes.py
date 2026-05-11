"""Tests for `attune.ops.routes.specs` — Phase 1 read-side API.

Covers the Phase 1 task list from
`docs/specs/ops-specs-features/tasks.md`:
- empty roots
- single root with multiple specs
- multi-root with naming collisions
- phase file missing
- malformed phase file (no `**Status**:` line)
- slug-safety on the drill-in route
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402


def _make_spec(root: Path, slug: str, *, files: dict[str, str]) -> Path:
    """Create a spec directory at ``root/slug`` with the given phase files.

    ``files`` maps phase file name (e.g. ``decisions.md``) to body content.
    """
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
    )
    return TestClient(create_app(config))


# ---------------------------------------------------------------------------
# GET /api/specs — listing
# ---------------------------------------------------------------------------


def test_list_specs_empty_roots_returns_empty(tmp_path, monkeypatch):
    """No spec dirs anywhere → empty `specs` list, root listed in `roots`."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    client = _client(tmp_path)
    response = client.get("/api/specs")
    assert response.status_code == 200
    body = response.json()
    assert body["specs"] == []
    # Default root is project_root/docs/specs even when it doesn't exist.
    # Use os.sep to be cross-platform (Windows: \, POSIX: /).
    import os

    assert len(body["roots"]) == 1
    assert body["roots"][0].endswith(os.path.join("docs", "specs"))


def test_list_specs_single_root_multiple_specs(tmp_path, monkeypatch):
    """Two specs in the default root → both listed, slugs sorted."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    specs_root = tmp_path / "docs" / "specs"
    _make_spec(
        specs_root,
        "alpha-spec",
        files={
            "decisions.md": "# Alpha\n\n**Status:** Draft\n",
            "tasks.md": "# Tasks\n\n**Status:** Draft\n",
        },
    )
    _make_spec(
        specs_root,
        "beta-spec",
        files={"decisions.md": "# Beta\n\n**Status:** Approved\n"},
    )

    client = _client(tmp_path)
    response = client.get("/api/specs")
    assert response.status_code == 200
    body = response.json()
    slugs = [s["slug"] for s in body["specs"]]
    assert slugs == ["alpha-spec", "beta-spec"]


def test_list_specs_phase_status_extracted(tmp_path, monkeypatch):
    """Status line is parsed correctly across decisions and tasks files."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    specs_root = tmp_path / "docs" / "specs"
    _make_spec(
        specs_root,
        "my-spec",
        files={
            "decisions.md": "# X\n\n**Status:** Approved & Prioritized (2026-05-11)\n\nbody",
            "tasks.md": "# Tasks\n\n**Status:** Draft\n",
        },
    )
    client = _client(tmp_path)
    response = client.get("/api/specs")
    body = response.json()
    phases = {p["name"]: p for p in body["specs"][0]["phases"]}
    assert phases["decisions"]["status"] == "Approved & Prioritized (2026-05-11)"
    assert phases["tasks"]["status"] == "Draft"
    assert phases["requirements"]["exists"] is False
    assert phases["requirements"]["status"] is None


def test_list_specs_malformed_status_line(tmp_path, monkeypatch):
    """A phase file without `**Status**:` → exists=true, status=None."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    specs_root = tmp_path / "docs" / "specs"
    _make_spec(
        specs_root,
        "no-status",
        files={"decisions.md": "# Just a heading, no status line"},
    )
    client = _client(tmp_path)
    response = client.get("/api/specs")
    decisions = next(p for p in response.json()["specs"][0]["phases"] if p["name"] == "decisions")
    assert decisions["exists"] is True
    assert decisions["status"] is None


def test_list_specs_ignores_dirs_without_phase_files(tmp_path, monkeypatch):
    """A directory under specs root that has no phase files is NOT a spec."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    specs_root = tmp_path / "docs" / "specs"
    specs_root.mkdir(parents=True)
    (specs_root / "scratch-dir").mkdir()
    (specs_root / "scratch-dir" / "notes.txt").write_text("random notes", encoding="utf-8")
    _make_spec(specs_root, "real-spec", files={"decisions.md": "**Status:** Draft\n"})

    client = _client(tmp_path)
    body = client.get("/api/specs").json()
    slugs = [s["slug"] for s in body["specs"]]
    assert slugs == ["real-spec"]


def test_list_specs_multi_root_collision_preserved(tmp_path, monkeypatch):
    """Same slug in two roots → both listed, distinct by `root` field."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    root_a = tmp_path / "repo-a" / "docs" / "specs"
    root_b = tmp_path / "repo-b" / "docs" / "specs"
    _make_spec(root_a, "shared-slug", files={"decisions.md": "**Status:** Draft (repo-a)\n"})
    _make_spec(root_b, "shared-slug", files={"decisions.md": "**Status:** Approved (repo-b)\n"})

    client = _client(tmp_path, specs_roots=(root_a, root_b))
    body = client.get("/api/specs").json()
    matches = [s for s in body["specs"] if s["slug"] == "shared-slug"]
    assert len(matches) == 2
    statuses = [next(p for p in s["phases"] if p["name"] == "decisions")["status"] for s in matches]
    assert "Draft (repo-a)" in statuses
    assert "Approved (repo-b)" in statuses


# ---------------------------------------------------------------------------
# GET /api/specs/{slug} — drill-in
# ---------------------------------------------------------------------------


def test_get_spec_returns_file_contents(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    specs_root = tmp_path / "docs" / "specs"
    decisions_text = "# Title\n\n**Status:** Draft\n\nbody paragraph"
    tasks_text = "# Tasks\n\n- [ ] step 1\n- [ ] step 2"
    _make_spec(
        specs_root,
        "my-spec",
        files={"decisions.md": decisions_text, "tasks.md": tasks_text},
    )
    client = _client(tmp_path)
    body = client.get("/api/specs/my-spec").json()
    assert body["slug"] == "my-spec"
    assert body["contents"]["decisions"] == decisions_text
    assert body["contents"]["tasks"] == tasks_text
    # phases without files are present in `phases` array with exists=False
    requirements = next(p for p in body["phases"] if p["name"] == "requirements")
    assert requirements["exists"] is False


def test_get_spec_not_found_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    client = _client(tmp_path)
    response = client.get("/api/specs/no-such-slug")
    assert response.status_code == 404


def test_get_spec_first_root_wins_on_collision(tmp_path, monkeypatch):
    """Same slug in multiple roots → drill-in returns the first one."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    root_a = tmp_path / "repo-a" / "docs" / "specs"
    root_b = tmp_path / "repo-b" / "docs" / "specs"
    _make_spec(root_a, "shared", files={"decisions.md": "from-a"})
    _make_spec(root_b, "shared", files={"decisions.md": "from-b"})

    client = _client(tmp_path, specs_roots=(root_a, root_b))
    body = client.get("/api/specs/shared").json()
    assert body["contents"]["decisions"] == "from-a"


@pytest.mark.parametrize(
    "slug",
    ["../escape", "weird/slash", r"back\slash", "..\\nt-escape"],
)
def test_get_spec_rejects_path_traversal(tmp_path, monkeypatch, slug):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    client = _client(tmp_path)
    response = client.get(f"/api/specs/{slug}")
    # 400 (our validator) or 404 (FastAPI rejecting the path) are both acceptable;
    # the important property is that no file outside the configured root is read
    assert response.status_code in (400, 404)


# ---------------------------------------------------------------------------
# Config wiring
# ---------------------------------------------------------------------------


def test_config_defaults_to_docs_specs(tmp_path):
    """When --specs-root isn't passed, config.specs_roots is empty and the
    route falls back to <project_root>/docs/specs/."""
    config = build_config(project_root=tmp_path)
    assert config.specs_roots == ()


def test_config_accepts_multiple_specs_roots(tmp_path):
    """build_config accepts a tuple of specs roots."""
    a = tmp_path / "a" / "docs" / "specs"
    b = tmp_path / "b" / "docs" / "specs"
    config = build_config(project_root=tmp_path, specs_roots=(a, b))
    assert config.specs_roots == (a, b)


# ---------------------------------------------------------------------------
# PUT /api/specs/{slug}/{phase}/status — Phase 2 status flip
# ---------------------------------------------------------------------------


def test_put_status_flips_attune_ai_convention(tmp_path, monkeypatch):
    """`**Status:** old` is rewritten to `**Status:** new` (colon-inside)."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "# Tasks\n\n**Status:** draft\n\nBody.\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)

    r = client.put("/api/specs/alpha/tasks/status", json={"status": "approved"})

    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["status"] == "approved"
    assert payload["phase"] == "tasks"
    assert payload["slug"] == "alpha"
    updated = (root / "alpha" / "tasks.md").read_text(encoding="utf-8")
    assert "**Status:** approved" in updated
    assert "**Status:** draft" not in updated
    assert "Body." in updated  # body preserved


def test_put_status_flips_attune_gui_convention(tmp_path, monkeypatch):
    """`**Status**: old` (colon-outside) is also recognized and rewritten."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    _make_spec(root, "beta", files={"design.md": "# Design\n\n**Status**: draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)

    r = client.put("/api/specs/beta/design/status", json={"status": "complete"})

    assert r.status_code == 200, r.text
    updated = (root / "beta" / "design.md").read_text(encoding="utf-8")
    assert "**Status:** complete" in updated


def test_put_status_inserts_when_missing(tmp_path, monkeypatch):
    """Files without any **Status** line get one inserted near the top."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    _make_spec(root, "gamma", files={"requirements.md": "# Requirements\n\nNo status here.\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)

    r = client.put("/api/specs/gamma/requirements/status", json={"status": "draft"})

    assert r.status_code == 200, r.text
    updated = (root / "gamma" / "requirements.md").read_text(encoding="utf-8")
    assert "**Status:** draft" in updated
    assert "# Requirements" in updated  # H1 preserved
    assert "No status here." in updated  # body preserved


def test_put_status_accepts_done_and_completed_aliases(tmp_path, monkeypatch):
    """`done` and `completed` are accepted alongside `complete`."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    _make_spec(root, "delta", files={"tasks.md": "**Status:** approved\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)

    for status in ("done", "completed", "complete"):
        r = client.put("/api/specs/delta/tasks/status", json={"status": status})
        assert r.status_code == 200, f"{status}: {r.text}"


def test_put_status_read_only_returns_403(tmp_path, monkeypatch):
    """When allow_run is False (default --read-only), PUT is rejected."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=False)

    r = client.put("/api/specs/alpha/tasks/status", json={"status": "approved"})

    assert r.status_code == 403, r.text
    # File unchanged
    assert (root / "alpha" / "tasks.md").read_text(encoding="utf-8") == "**Status:** draft\n"


def test_put_status_unknown_spec_returns_404(tmp_path, monkeypatch):
    """Slug that doesn't exist in any root → 404."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    root.mkdir(parents=True)
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)

    r = client.put("/api/specs/missing/tasks/status", json={"status": "draft"})

    assert r.status_code == 404, r.text


def test_put_status_unknown_phase_returns_400(tmp_path, monkeypatch):
    """Phase name outside the recognized set → 400 before any FS work."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)

    r = client.put("/api/specs/alpha/notarealphase/status", json={"status": "draft"})

    assert r.status_code == 400, r.text
    assert "unknown phase" in r.json()["detail"].lower()


def test_put_status_invalid_status_value_returns_400(tmp_path, monkeypatch):
    """Status value outside the accepted vocabulary → 400."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)

    r = client.put("/api/specs/alpha/tasks/status", json={"status": "WIP"})

    assert r.status_code == 400, r.text
    assert "invalid status" in r.json()["detail"].lower()


def test_put_status_missing_status_field_returns_422(tmp_path, monkeypatch):
    """Body without a `status` string → 422 (Unprocessable Entity)."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    _make_spec(root, "alpha", files={"tasks.md": "**Status:** draft\n"})
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)

    r = client.put("/api/specs/alpha/tasks/status", json={"other": "value"})

    assert r.status_code == 422, r.text


@pytest.mark.parametrize(
    "slug",
    ["../escape", "weird/slash", "back\\slash", "UPPERCASE", "-leading-dash", "with space"],
)
def test_put_status_rejects_invalid_slug(tmp_path, monkeypatch, slug):
    """Slugs that don't match the directory-name shape are rejected as 400."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "specs"
    root.mkdir(parents=True)
    client = _client(tmp_path, specs_roots=(root,), allow_run=True)

    r = client.put(f"/api/specs/{slug}/tasks/status", json={"status": "draft"})

    # FastAPI may also return 404 for some path-traversal-shaped slugs that
    # don't reach the route handler — accept either rejection.
    assert r.status_code in (400, 404), f"slug={slug!r} status={r.status_code} body={r.text}"


def test_put_status_first_root_wins_on_collision(tmp_path, monkeypatch):
    """When the same slug exists in multiple roots, PUT writes to the first."""
    monkeypatch.chdir(tmp_path)
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    _make_spec(root_a, "shared", files={"tasks.md": "**Status:** draft\n"})
    _make_spec(root_b, "shared", files={"tasks.md": "**Status:** approved\n"})
    client = _client(tmp_path, specs_roots=(root_a, root_b), allow_run=True)

    r = client.put("/api/specs/shared/tasks/status", json={"status": "complete"})

    assert r.status_code == 200, r.text
    assert r.json()["root"] == str(root_a)
    # Only root_a was rewritten
    assert "**Status:** complete" in (root_a / "shared" / "tasks.md").read_text(encoding="utf-8")
    # root_b is untouched
    assert (root_b / "shared" / "tasks.md").read_text(encoding="utf-8") == (
        "**Status:** approved\n"
    )
