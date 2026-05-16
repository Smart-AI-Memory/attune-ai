"""Tests for the Specs page server-rendered candidates section.

Spec: ``docs/specs/ops-specs-completion-candidates/`` (T5).

The "Ready to close?" section is rendered server-side behind a
two-gate check: ``allow_run AND specs_candidates_enabled``. JS only
loads when the shell is present, so server-side gating fully
suppresses the feature when off.

Covers:
- Section + JS rendered when both gates are on.
- Section absent when feature flag is off.
- Section absent when read-only.
- JS tag is correctly cache-busted with the attune version.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402


def _client(
    tmp_path: Path,
    *,
    specs_candidates_enabled: bool = True,
    allow_run: bool = True,
) -> TestClient:
    config = build_config(
        project_root=tmp_path,
        allow_run=allow_run,
        specs_candidates_enabled=specs_candidates_enabled,
        trusted_hosts=("testserver", "test"),
    )
    return TestClient(create_app(config))


class TestSectionGating:
    def test_section_rendered_when_both_gates_on(self, tmp_path: Path) -> None:
        client = _client(tmp_path, specs_candidates_enabled=True, allow_run=True)
        response = client.get("/specs")
        assert response.status_code == 200
        assert 'id="completion-candidates"' in response.text
        assert 'id="cc-list"' in response.text
        assert 'id="cc-count"' in response.text
        # Header text confirms server-rendered shell.
        assert "Ready to close?" in response.text

    def test_section_hidden_initially(self, tmp_path: Path) -> None:
        # The shell ships with `hidden` so it doesn't flash before the
        # JS populates it.
        client = _client(tmp_path)
        html = client.get("/specs").text
        # Find the section opening tag and verify it carries the
        # `hidden` attribute.
        assert 'id="completion-candidates"' in html
        idx = html.find('id="completion-candidates"')
        section_tag = html[max(0, idx - 80) : idx + 80]
        assert "hidden" in section_tag

    def test_section_absent_when_feature_flag_off(self, tmp_path: Path) -> None:
        client = _client(tmp_path, specs_candidates_enabled=False, allow_run=True)
        html = client.get("/specs").text
        assert 'id="completion-candidates"' not in html
        assert "Ready to close?" not in html

    def test_section_absent_when_read_only(self, tmp_path: Path) -> None:
        client = _client(tmp_path, specs_candidates_enabled=True, allow_run=False)
        html = client.get("/specs").text
        assert 'id="completion-candidates"' not in html
        assert "Ready to close?" not in html

    def test_section_absent_when_both_off(self, tmp_path: Path) -> None:
        client = _client(tmp_path, specs_candidates_enabled=False, allow_run=False)
        html = client.get("/specs").text
        assert 'id="completion-candidates"' not in html


class TestJsInclude:
    def test_js_included_when_section_rendered(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        html = client.get("/specs").text
        assert "completion_candidates.js" in html

    def test_js_excluded_when_feature_flag_off(self, tmp_path: Path) -> None:
        client = _client(tmp_path, specs_candidates_enabled=False)
        html = client.get("/specs").text
        assert "completion_candidates.js" not in html

    def test_js_excluded_when_read_only(self, tmp_path: Path) -> None:
        client = _client(tmp_path, allow_run=False)
        html = client.get("/specs").text
        assert "completion_candidates.js" not in html

    def test_js_has_cache_buster(self, tmp_path: Path) -> None:
        # Per the existing CLAUDE.md lesson about cache-busting static
        # JS on release — version query string prevents stale JS after
        # a release.
        client = _client(tmp_path)
        html = client.get("/specs").text
        # The exact version isn't important to assert; just confirm
        # the buster is present.
        assert "completion_candidates.js?v=" in html


class TestJsFileServes:
    """The static JS file must be reachable via /static/js/."""

    def test_js_file_returns_200(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        response = client.get("/static/js/completion_candidates.js")
        assert response.status_code == 200
        # Sanity-check it's the actual module, not a 404 page.
        assert "completion-candidates" in response.text
        assert "Ready to close" in response.text or "candidate-card" in response.text
