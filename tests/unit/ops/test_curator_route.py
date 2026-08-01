"""Tests for the dashboard /curator route (bulletin-curator Phase 3, Task 3.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.curator.result import CuratorItem, CuratorResult, SuggestedAction
from attune.ops.config import Config
from attune.ops.server import create_app


@pytest.fixture
def attune_home(tmp_path: Path) -> Path:
    return tmp_path / "ah"


@pytest.fixture
def client(tmp_path: Path, attune_home: Path) -> TestClient:
    cfg = Config(
        project_root=tmp_path,
        attune_home=attune_home,
        allow_run=False,
        trusted_hosts=("testserver", "test"),
    )
    return TestClient(create_app(cfg))


def _result(
    items: list[CuratorItem], summary: str = "Two things need attention [a:1]."
) -> CuratorResult:
    return CuratorResult(
        summary=summary,
        items=items,
        sources_consulted=["bulletin", "specs"],
        cost_usd=0.0321,
        model="claude-opus-4-8",
    )


def _inject(monkeypatch, result: CuratorResult) -> None:
    async def _fake(**kwargs):
        return result

    monkeypatch.setattr("attune.ops.routes.curator.run_curator", _fake)


def _items() -> list[CuratorItem]:
    return [
        CuratorItem(
            id="i1",
            title="Spec alpha looks ready to close",
            severity="warn",
            rationale="All tasks done [a:1].",
            sources=["spec:alpha"],
            suggested_action=SuggestedAction(kind="open", label="Open spec", url="/specs/alpha"),
        ),
        CuratorItem(
            id="i2",
            title="Security finding unreviewed",
            severity="nudge",
            rationale="HIGH finding 22 min ago [r:2].",
            sources=["rec:r2"],
            suggested_action=SuggestedAction(
                kind="ask",
                question="Mark reviewed?",
                choices=["Yes", "No"],
            ),
        ),
    ]


class TestGetCuratorPage:
    def test_renders_summary_and_items(self, client, monkeypatch):
        _inject(monkeypatch, _result(_items()))
        resp = client.get("/curator")
        assert resp.status_code == 200
        body = resp.text
        assert "Two things need attention" in body
        assert "Spec alpha looks ready to close" in body
        assert "Security finding unreviewed" in body
        assert "claude-opus-4-8" in body

    def test_empty_items_shows_empty_state(self, client, monkeypatch):
        _inject(monkeypatch, _result([], summary="Nothing pressing."))
        resp = client.get("/curator")
        assert resp.status_code == 200
        assert "Nothing pressing" in resp.text
        assert "no items rank above noise" in resp.text


class TestDismiss:
    def test_dismiss_persists_and_filters(self, client, monkeypatch, attune_home):
        _inject(monkeypatch, _result(_items()))

        resp = client.post("/curator/dismiss", json={"item_id": "i1"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        dismissals = json.loads((attune_home / "curator" / "dismissals.json").read_text())
        assert "i1" in dismissals
        assert "snoozed_until" in dismissals["i1"]

        # Subsequent GET filters the snoozed item out.
        page = client.get("/curator")
        assert "Spec alpha looks ready to close" not in page.text
        assert "Security finding unreviewed" in page.text

    def test_dismiss_requires_item_id(self, client, monkeypatch):
        _inject(monkeypatch, _result(_items()))
        resp = client.post("/curator/dismiss", json={})
        assert resp.status_code == 400
        assert resp.json()["ok"] is False


class TestAnswer:
    def test_answer_journals(self, client, monkeypatch, attune_home):
        _inject(monkeypatch, _result(_items()))
        resp = client.post("/curator/answer", json={"item_id": "i2", "choice": "Yes"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        journal = attune_home / "curator" / "answers.jsonl"
        lines = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
        assert len(lines) == 1
        assert lines[0]["item_id"] == "i2"
        assert lines[0]["choice"] == "Yes"

    def test_answer_requires_choice(self, client, monkeypatch):
        _inject(monkeypatch, _result(_items()))
        resp = client.post("/curator/answer", json={"item_id": "i2"})
        assert resp.status_code == 400

    def test_answer_write_failure_is_best_effort(self, client, monkeypatch):
        """A journal-write failure is logged, not surfaced — the response
        still reports ``ok: True`` (lines 159, 161: the except branch)."""
        _inject(monkeypatch, _result(_items()))
        monkeypatch.setattr(
            "attune.ops.routes.curator._validate_file_path",
            lambda *a, **kw: (_ for _ in ()).throw(ValueError("boom")),
        )
        resp = client.post("/curator/answer", json={"item_id": "i2", "choice": "Yes"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "item_id": "i2", "choice": "Yes"}


class TestDismissWriteFailure:
    def test_dismiss_write_failure_returns_500(self, client, monkeypatch):
        """A dismissals-write failure surfaces as a 500 (lines 121-123)."""
        _inject(monkeypatch, _result(_items()))
        monkeypatch.setattr(
            "attune.ops.routes.curator._validate_file_path",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("disk full")),
        )
        resp = client.post("/curator/dismiss", json={"item_id": "i1"})
        assert resp.status_code == 500
        assert resp.json() == {"ok": False, "error": "write failed"}


class TestActiveDismissedIdsEdgeCases:
    """Direct coverage of the malformed/edge-case branches in
    ``_load_dismissals`` and ``_active_dismissed_ids`` (lines 56-57, 68,
    71-72, 74) — exercised through the ``/curator`` GET route, which is
    the only caller of both helpers."""

    def test_malformed_json_file_degrades_to_no_dismissals(self, client, monkeypatch, attune_home):
        _inject(monkeypatch, _result(_items()))
        dismissals_path = attune_home / "curator" / "dismissals.json"
        dismissals_path.parent.mkdir(parents=True, exist_ok=True)
        dismissals_path.write_text("{not valid json", encoding="utf-8")

        resp = client.get("/curator")
        assert resp.status_code == 200
        # Malformed file -> treated as empty dismissals -> both items show.
        assert "Spec alpha looks ready to close" in resp.text
        assert "Security finding unreviewed" in resp.text

    def test_record_missing_snoozed_until_is_skipped(self, client, monkeypatch, attune_home):
        _inject(monkeypatch, _result(_items()))
        dismissals_path = attune_home / "curator" / "dismissals.json"
        dismissals_path.parent.mkdir(parents=True, exist_ok=True)
        dismissals_path.write_text(json.dumps({"i1": {}}), encoding="utf-8")

        resp = client.get("/curator")
        assert resp.status_code == 200
        # No snoozed_until -> not treated as actively dismissed -> still shown.
        assert "Spec alpha looks ready to close" in resp.text

    def test_record_with_unparseable_date_is_skipped(self, client, monkeypatch, attune_home):
        _inject(monkeypatch, _result(_items()))
        dismissals_path = attune_home / "curator" / "dismissals.json"
        dismissals_path.parent.mkdir(parents=True, exist_ok=True)
        dismissals_path.write_text(
            json.dumps({"i1": {"snoozed_until": "not-a-date"}}), encoding="utf-8"
        )

        resp = client.get("/curator")
        assert resp.status_code == 200
        # Bad date string -> caught, skipped -> item still shown.
        assert "Spec alpha looks ready to close" in resp.text

    def test_naive_snoozed_until_treated_as_utc(self, client, monkeypatch, attune_home):
        _inject(monkeypatch, _result(_items()))
        dismissals_path = attune_home / "curator" / "dismissals.json"
        dismissals_path.parent.mkdir(parents=True, exist_ok=True)
        # No timezone offset -> exercises the naive-datetime UTC-replace path.
        dismissals_path.write_text(
            json.dumps({"i1": {"snoozed_until": "2099-01-01T00:00:00"}}), encoding="utf-8"
        )

        resp = client.get("/curator")
        assert resp.status_code == 200
        # Future naive date, treated as UTC -> still active -> item filtered out.
        assert "Spec alpha looks ready to close" not in resp.text
        assert "Security finding unreviewed" in resp.text
