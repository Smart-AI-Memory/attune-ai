"""Tests for S3b dashboard wire-up: HTML compare mode + JSON API.

The deterministic S2/S3a tests already cover the data-layer
heuristic. These tests cover:

- ``/api/sessions`` returns the spec'd JSON shape
- ``?compare=1`` renders both heuristic and haiku columns
- Over-budget marker appears when the budget is exhausted
- Source chips render correctly (heuristic vs haiku vs cached)

Anthropic calls are mocked; no real LLM hits in CI.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops import data  # noqa: E402
from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixtures + helpers (mirror tests/unit/ops/test_sessions.py)
# ---------------------------------------------------------------------------


def _patch_home(monkeypatch, home_path: Path) -> None:
    """Patch ``Path.home()`` to ``home_path`` on every platform.

    Mirrors the helper in test_sessions.py — must set both env vars
    so the test works on Windows runners too.
    """
    home_str = str(home_path)
    monkeypatch.setenv("HOME", home_str)
    monkeypatch.setenv("USERPROFILE", home_str)


def _write_session(home: Path, project_root: Path, session_id: str, content: str) -> Path:
    sessions_dir = home / ".claude" / "projects" / data._encoded_project_path(project_root)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f"{session_id}.jsonl"
    path.write_text(
        json.dumps({"timestamp": "2026-05-14T10:00:00Z", "content": content}) + "\n",
        encoding="utf-8",
    )
    return path


def _install_fake_anthropic(monkeypatch, *, summary_text: str = "Worked on X. Resume: continue."):
    """Install a fake ``anthropic`` module that returns ``summary_text``."""
    from unittest.mock import MagicMock

    content_block = types.SimpleNamespace(text=summary_text, type="text")
    usage = types.SimpleNamespace(input_tokens=100, output_tokens=20)
    response = types.SimpleNamespace(content=[content_block], usage=usage)

    create_mock = MagicMock(return_value=response)
    client = types.SimpleNamespace(messages=types.SimpleNamespace(create=create_mock))

    class _FakeAnthropic:
        def __new__(cls, *, api_key):
            return client

    fake_module = types.ModuleType("anthropic")
    fake_module.Anthropic = _FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    return create_mock


def _make_app(tmp_path: Path, monkeypatch) -> object:
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    _patch_home(monkeypatch, tmp_path / "home")
    config = build_config(
        project_root=tmp_path / "project",
        trusted_hosts=("testserver", "test"),
    )
    return create_app(config)


# ---------------------------------------------------------------------------
# /api/sessions JSON
# ---------------------------------------------------------------------------


def test_api_sessions_returns_spec_shape_with_haiku(tmp_path, monkeypatch):
    """``GET /api/sessions`` returns ``{sessions: [...], meta: {...}}``
    with each session carrying the source field.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    _install_fake_anthropic(monkeypatch, summary_text="Worked on auth.")

    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_session(tmp_path / "home", project_root, "abc12345-def", "Help with auth")

    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/sessions")

    assert resp.status_code == 200
    body = resp.json()
    assert "sessions" in body
    assert "meta" in body
    assert body["meta"]["llm_enabled"] is True
    assert body["meta"]["budget_exceeded"] is False

    assert len(body["sessions"]) == 1
    row = body["sessions"][0]
    expected_keys = {
        "id",
        "started_at",
        "last_activity",
        "duration_seconds",
        "message_count",
        "starter_prompt",
        "source",
    }
    assert expected_keys.issubset(row.keys())
    assert row["id"] == "abc12345-def"
    assert row["source"] == "haiku"
    assert row["starter_prompt"] == "Worked on auth."


def test_api_sessions_returns_heuristic_when_llm_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ATTUNE_OPS_SESSIONS_LLM", "0")

    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_session(tmp_path / "home", project_root, "xyz-001", "Heuristic prompt content")

    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/sessions")

    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["llm_enabled"] is False
    assert len(body["sessions"]) == 1
    row = body["sessions"][0]
    assert row["source"] == "heuristic"
    assert "Heuristic prompt content" in row["starter_prompt"]


def test_api_sessions_returns_empty_on_no_data(tmp_path, monkeypatch):
    """No sessions dir → empty list, 200 OK (not 404)."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/sessions")

    assert resp.status_code == 200
    body = resp.json()
    assert body["sessions"] == []


# ---------------------------------------------------------------------------
# Cached source field on second load
# ---------------------------------------------------------------------------


def test_api_sessions_second_load_returns_cached_source(tmp_path, monkeypatch):
    """First load runs Haiku; second load (cache hit) reports source=cached."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    create_mock = _install_fake_anthropic(monkeypatch, summary_text="Auth work.")

    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_session(tmp_path / "home", project_root, "session-cached-001", "Help with auth")

    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        first = client.get("/api/sessions").json()
        second = client.get("/api/sessions").json()

    assert first["sessions"][0]["source"] == "haiku"
    assert second["sessions"][0]["source"] == "cached"
    # Cache hit means only one LLM call across two HTTP requests.
    assert create_mock.call_count == 1


# ---------------------------------------------------------------------------
# ?compare=1 dev mode
# ---------------------------------------------------------------------------


def test_sessions_page_compare_mode_renders_both_columns(tmp_path, monkeypatch):
    """``?compare=1`` renders Heuristic and Haiku side-by-side."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    _install_fake_anthropic(monkeypatch, summary_text="HAIKU_SUMMARY_TEXT")

    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_session(tmp_path / "home", project_root, "abc12345-cmp", "ORIGINAL_PROMPT_TEXT")

    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/sessions?compare=1")

    assert resp.status_code == 200
    body = resp.text
    assert "Compare mode" in body
    # Heuristic column header
    assert "Heuristic" in body
    # Haiku column header
    assert "Haiku" in body
    # Both prompts present
    assert "ORIGINAL_PROMPT_TEXT" in body
    assert "HAIKU_SUMMARY_TEXT" in body


def test_sessions_page_normal_mode_does_not_show_compare_chrome(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_session(tmp_path / "home", project_root, "abc12345-norm", "Test prompt")

    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/sessions")

    assert resp.status_code == 200
    body = resp.text
    assert "Compare mode" not in body


# ---------------------------------------------------------------------------
# Over-budget marker
# ---------------------------------------------------------------------------


def test_sessions_page_renders_over_budget_marker(tmp_path, monkeypatch):
    """Setting the budget to 0 forces a breach on the first call →
    the over-budget marker appears in the rendered page.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    monkeypatch.setenv("ATTUNE_OPS_SESSIONS_BUDGET_USD", "0.0")
    _install_fake_anthropic(monkeypatch, summary_text="Should not appear")

    project_root = tmp_path / "project"
    project_root.mkdir()
    # Write 2 sessions; the first call would breach with cap=0, so
    # both rows render heuristic. The marker fires once.
    _write_session(tmp_path / "home", project_root, "s-001", "First prompt")
    _write_session(tmp_path / "home", project_root, "s-002", "Second prompt")

    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/sessions")

    assert resp.status_code == 200
    body = resp.text
    assert "Per-page Haiku budget exceeded" in body
    # Heuristic content survived
    assert "First prompt" in body
    assert "Second prompt" in body


# ---------------------------------------------------------------------------
# Regression: Anthropic SDK calls must run OFF the main event-loop thread.
#
# The ``anthropic`` SDK's ``Anthropic(...).messages.create(...)`` is
# SYNCHRONOUS. Calling it directly inside an async FastAPI route blocks
# the uvicorn event loop for the duration of the Haiku batch
# (~0.5–2s per session × N sessions), freezing every other request —
# SSE streams, runner control, page renders.
#
# Fix: ``await asyncio.to_thread(enrich_with_summaries, ...)`` in
# ``routes/sessions.py:list_sessions`` and the equivalent in
# ``routes/dashboard.py:sessions_page`` (both branches). These tests
# guard the fix by asserting the Anthropic call captures a thread id
# DIFFERENT from the test's main thread — proving the chain runs in a
# worker thread, not on the loop.
# ---------------------------------------------------------------------------


def _install_thread_recording_anthropic(monkeypatch, *, summary_text: str = "Recorded."):
    """Like _install_fake_anthropic, but records the thread id of each call.

    Returns the recorded-ids list (mutated by ``create``). Test asserts
    every recorded id != ``threading.get_ident()`` captured on the
    main thread.
    """
    import threading

    content_block = types.SimpleNamespace(text=summary_text, type="text")
    usage = types.SimpleNamespace(input_tokens=100, output_tokens=20)
    response = types.SimpleNamespace(content=[content_block], usage=usage)
    recorded_thread_ids: list[int] = []

    def _create(**_kwargs):
        recorded_thread_ids.append(threading.get_ident())
        return response

    client = types.SimpleNamespace(messages=types.SimpleNamespace(create=_create))

    class _FakeAnthropic:
        def __new__(cls, *, api_key):
            return client

    fake_module = types.ModuleType("anthropic")
    fake_module.Anthropic = _FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    return recorded_thread_ids


@pytest.mark.asyncio
async def test_api_sessions_runs_anthropic_off_event_loop_thread(tmp_path, monkeypatch):
    """``GET /api/sessions`` must defer the sync Anthropic call to a
    worker thread via ``asyncio.to_thread``. Reverting the wrap would
    make ``recorded_thread_ids[0] == main_thread_id``.
    """
    import threading

    from httpx import ASGITransport, AsyncClient

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    recorded = _install_thread_recording_anthropic(monkeypatch)

    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_session(tmp_path / "home", project_root, "sess-001", "Some content")

    app = _make_app(tmp_path, monkeypatch)
    main_thread_id = threading.get_ident()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/sessions")

    assert resp.status_code == 200
    assert len(recorded) >= 1, "Anthropic was never called — test setup is wrong"
    assert all(tid != main_thread_id for tid in recorded), (
        f"Anthropic SDK ran on the event-loop thread {main_thread_id} "
        f"(recorded: {recorded}). The ``asyncio.to_thread`` wrap in "
        f"``routes/sessions.py:list_sessions`` was reverted — every "
        f"slow Haiku call now blocks the uvicorn loop."
    )


@pytest.mark.asyncio
async def test_sessions_page_runs_anthropic_off_event_loop_thread(tmp_path, monkeypatch):
    """The HTML ``GET /sessions`` page (normal branch) must also defer
    Anthropic to a worker thread. Symmetric to the JSON test above
    but covers ``routes/dashboard.py:sessions_page``.
    """
    import threading

    from httpx import ASGITransport, AsyncClient

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret
    recorded = _install_thread_recording_anthropic(monkeypatch)

    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_session(tmp_path / "home", project_root, "sess-002", "Other content")

    app = _make_app(tmp_path, monkeypatch)
    main_thread_id = threading.get_ident()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/sessions")

    assert resp.status_code == 200
    assert len(recorded) >= 1, "Anthropic was never called — test setup is wrong"
    assert all(tid != main_thread_id for tid in recorded), (
        f"Anthropic SDK ran on the event-loop thread {main_thread_id} "
        f"(recorded: {recorded}). The ``asyncio.to_thread`` wrap in "
        f"``routes/dashboard.py:sessions_page`` was reverted — every "
        f"slow Haiku call now blocks the uvicorn loop."
    )
