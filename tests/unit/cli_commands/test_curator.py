"""Tests for the ``attune curator`` CLI command (Phase 3, Task 3.2)."""

from __future__ import annotations

import argparse
import json

from attune.cli_commands import curator as cli_curator
from attune.curator.result import CuratorItem, CuratorResult, SuggestedAction


def _result(items=None, summary="Two things need attention [a:1]."):
    return CuratorResult(
        summary=summary,
        items=items or [],
        sources_consulted=["bulletin", "specs"],
        cost_usd=0.0321,
        model="claude-opus-4-8",
    )


def _items():
    return [
        CuratorItem(
            id="i1",
            title="Spec alpha ready to close",
            severity="warn",
            rationale="All tasks done [a:1].",
            sources=["spec:alpha"],
            suggested_action=SuggestedAction(kind="open", url="/specs/alpha"),
        ),
        CuratorItem(
            id="i2",
            title="Security finding unreviewed",
            severity="nudge",
            rationale="HIGH finding [r:2].",
            sources=["rec:r2"],
            suggested_action=SuggestedAction(
                kind="ask", question="Mark reviewed?", choices=["Yes", "No"]
            ),
        ),
    ]


def _patch(monkeypatch, result, captured: dict | None = None):
    async def _fake(**kwargs):
        if captured is not None:
            captured.update(kwargs)
        return result

    monkeypatch.setattr("attune.cli_commands.curator.run_curator", _fake)


def _args(**kw):
    base = {"refresh": False, "json": False, "max_items": 5}
    base.update(kw)
    return argparse.Namespace(**base)


def test_default_render(monkeypatch, capsys):
    _patch(monkeypatch, _result(_items()))
    rc = cli_curator.cmd_curator(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "Briefing (claude-opus-4-8)" in out
    assert "Two things need attention" in out
    assert "[warn] Spec alpha ready to close" in out
    assert "Sources: spec:alpha" in out
    assert "open /specs/alpha" in out


def test_json_output(monkeypatch, capsys):
    _patch(monkeypatch, _result(_items()))
    rc = cli_curator.cmd_curator(_args(json=True))
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"].startswith("Two things")
    assert len(payload["items"]) == 2
    assert payload["model"] == "claude-opus-4-8"


def test_empty_state(monkeypatch, capsys):
    _patch(monkeypatch, _result([], summary="Quiet."))
    cli_curator.cmd_curator(_args())
    assert "Nothing pressing right now" in capsys.readouterr().out


def test_refresh_flag_reaches_run_curator(monkeypatch):
    captured: dict = {}
    _patch(monkeypatch, _result(), captured)
    cli_curator.cmd_curator(_args(refresh=True))
    assert captured["force_refresh"] is True


def test_max_items_reaches_run_curator(monkeypatch):
    captured: dict = {}
    _patch(monkeypatch, _result(), captured)
    cli_curator.cmd_curator(_args(max_items=3))
    assert captured["max_items"] == 3


def test_json_serializes_cached_at(monkeypatch, capsys):
    from datetime import datetime, timezone

    result = CuratorResult(summary="s", model="m", cached_at=datetime.now(timezone.utc))
    _patch(monkeypatch, result)
    cli_curator.cmd_curator(_args(json=True))
    payload = json.loads(capsys.readouterr().out)  # must not raise
    assert isinstance(payload["cached_at"], str)


def test_render_run_action_with_scope(monkeypatch, capsys):
    item = CuratorItem(
        id="i3",
        title="Coverage lane ready",
        severity="nudge",
        rationale="",
        suggested_action=SuggestedAction(kind="run", workflow="smart-test", scope="src/attune"),
    )
    _patch(monkeypatch, _result([item]))
    cli_curator.cmd_curator(_args())
    out = capsys.readouterr().out
    assert "Suggest: run smart-test on src/attune" in out


def test_render_run_action_without_scope(monkeypatch, capsys):
    item = CuratorItem(
        id="i4",
        title="Coverage lane ready",
        severity="nudge",
        rationale="",
        suggested_action=SuggestedAction(kind="run", workflow="smart-test"),
    )
    _patch(monkeypatch, _result([item]))
    cli_curator.cmd_curator(_args())
    out = capsys.readouterr().out
    assert "Suggest: run smart-test" in out
    assert " on " not in out.split("Suggest: run smart-test")[1].splitlines()[0]


def test_render_dismiss_action(monkeypatch, capsys):
    item = CuratorItem(
        id="i5",
        title="Stale nudge",
        severity="nudge",
        rationale="",
        suggested_action=SuggestedAction(kind="dismiss"),
    )
    _patch(monkeypatch, _result([item]))
    cli_curator.cmd_curator(_args())
    out = capsys.readouterr().out
    assert "Suggest: snooze" in out


def test_action_hint_fallback_uses_label(monkeypatch, capsys):
    # kind="open" with no url falls through every branch to the label/kind
    # fallback — exercises the unmatched-kind default path.
    item = CuratorItem(
        id="i6",
        title="Unusual action",
        severity="nudge",
        rationale="",
        suggested_action=SuggestedAction(kind="open", label="custom label"),
    )
    _patch(monkeypatch, _result([item]))
    cli_curator.cmd_curator(_args())
    out = capsys.readouterr().out
    assert "Suggest: custom label" in out


def test_action_hint_fallback_uses_kind_when_no_label(monkeypatch, capsys):
    item = CuratorItem(
        id="i7",
        title="Unusual action",
        severity="nudge",
        rationale="",
        suggested_action=SuggestedAction(kind="open"),
    )
    _patch(monkeypatch, _result([item]))
    cli_curator.cmd_curator(_args())
    out = capsys.readouterr().out
    assert "Suggest: open" in out
