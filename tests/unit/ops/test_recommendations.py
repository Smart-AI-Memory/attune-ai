"""Tests for the Phase 5 recommendation channel.

Covers:

- ``Run.emit_recommendation`` broadcasts on the SSE channel + buffers
  for replay to late subscribers.
- ``RunnerService._validate_recommendation`` accepts well-formed
  payloads and rejects malformed ones (bad kind, unknown workflow,
  bad args.path, bad open-url scheme).
- ``RunnerService.handle_stdout_line`` parses ``ATTUNE_REC <json>``
  marker lines, drops them from the visible log, and routes the
  payload to the recommendation channel.
- Markup smoke: ``run_view.js`` exports ``renderRecommendationCard``.

Spec: docs/specs/ops-runner-tier2/ Phase 5.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

from attune.ops.runner import Run, RunnerService

# ----------------------------------------------------------------------
# Run.emit_recommendation — broadcast + buffer
# ----------------------------------------------------------------------


def _new_run() -> Run:
    return Run(id="r1", workflow="code-review", status="running")


def test_emit_recommendation_broadcasts_to_existing_subscriber() -> None:
    async def go() -> dict[str, object]:
        run = _new_run()

        async def collect() -> dict[str, object]:
            async for kind, payload in run.subscribe():
                if kind == "recommendation":
                    return payload  # type: ignore[return-value]
                if kind == "done":
                    return {}
            return {}

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)  # let subscribe register
        run.emit_recommendation({"kind": "open-url", "url": "https://x"})
        run.mark_done(0)
        return await task

    out = asyncio.run(go())
    assert out == {"kind": "open-url", "url": "https://x"}


def test_emit_recommendation_replays_to_late_subscriber() -> None:
    async def go() -> list[dict[str, object]]:
        run = _new_run()
        run.emit_recommendation({"kind": "open-url", "url": "https://a"})
        run.emit_recommendation({"kind": "open-url", "url": "https://b"})
        run.mark_done(0)
        out: list[dict[str, object]] = []
        async for kind, payload in run.subscribe():
            if kind == "recommendation":
                out.append(payload)  # type: ignore[arg-type]
            if kind == "done":
                break
        return out

    out = asyncio.run(go())
    assert [r["url"] for r in out] == ["https://a", "https://b"]


def test_emit_recommendation_cap_limits_buffer() -> None:
    run = _new_run()
    for i in range(60):
        run.emit_recommendation({"kind": "open-url", "url": f"https://{i}"})
    assert len(run.recommendations) == 50  # _RECOMMENDATION_CAP


# ----------------------------------------------------------------------
# RunnerService._validate_recommendation — accept / reject
# ----------------------------------------------------------------------


@pytest.fixture()
def svc(tmp_path: Path) -> RunnerService:
    return RunnerService(project_root=tmp_path)


def test_validate_accepts_next_workflow_minimal(svc: RunnerService) -> None:
    out = svc._validate_recommendation({"kind": "next-workflow", "name": "code-review"})
    assert out is not None
    assert out["kind"] == "next-workflow"
    assert out["name"] == "code-review"


def test_validate_accepts_next_workflow_with_valid_path(svc: RunnerService, tmp_path: Path) -> None:
    scope = tmp_path / "src"
    scope.mkdir()
    out = svc._validate_recommendation(
        {
            "kind": "next-workflow",
            "name": "code-review",
            "args": {"path": str(scope)},
            "label": "Run on src/",
        }
    )
    assert out is not None
    assert out["args"] == {"path": str(scope.resolve())}
    assert out["label"] == "Run on src/"


def test_validate_rejects_path_traversal(
    svc: RunnerService, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="attune.ops.runner")
    out = svc._validate_recommendation(
        {
            "kind": "next-workflow",
            "name": "code-review",
            "args": {"path": "/etc/passwd"},
        }
    )
    assert out is None
    assert any("args.path" in r.message for r in caplog.records)


def test_validate_rejects_unknown_workflow(svc: RunnerService) -> None:
    out = svc._validate_recommendation({"kind": "next-workflow", "name": "not-a-real-workflow-xyz"})
    assert out is None


def test_validate_rejects_bad_kind(svc: RunnerService) -> None:
    out = svc._validate_recommendation({"kind": "make-coffee", "name": "code-review"})
    assert out is None


def test_validate_rejects_non_object(svc: RunnerService) -> None:
    assert svc._validate_recommendation("not an object") is None
    assert svc._validate_recommendation(None) is None
    assert svc._validate_recommendation([1, 2, 3]) is None


def test_validate_accepts_open_url_https(svc: RunnerService) -> None:
    out = svc._validate_recommendation(
        {"kind": "open-url", "url": "https://example.com/docs", "label": "Open docs"}
    )
    assert out is not None
    assert out["url"] == "https://example.com/docs"


def test_validate_rejects_open_url_javascript_scheme(svc: RunnerService) -> None:
    out = svc._validate_recommendation({"kind": "open-url", "url": "javascript:alert(1)"})
    assert out is None


def test_validate_rejects_open_url_file_scheme(svc: RunnerService) -> None:
    out = svc._validate_recommendation({"kind": "open-url", "url": "file:///etc/passwd"})
    assert out is None


# ----------------------------------------------------------------------
# _validate_recommendation — characterization pins (D-block batch 2).
# Exact-shape assertions: the refactor cut must not add, drop, or
# rename response keys, and every coercion below must survive verbatim.
# ----------------------------------------------------------------------


def test_validate_exact_shape_minimal_next_workflow(svc: RunnerService) -> None:
    out = svc._validate_recommendation({"kind": "next-workflow", "name": "code-review"})
    assert out == {"kind": "next-workflow", "name": "code-review"}


def test_validate_exact_shape_open_url_with_label_and_severity(svc: RunnerService) -> None:
    out = svc._validate_recommendation(
        {
            "kind": "open-url",
            "url": "https://example.com",
            "label": "Docs",
            "severity": "High",
            "extra": "dropped",
        }
    )
    assert out == {
        "kind": "open-url",
        "label": "Docs",
        "severity": "high",
        "url": "https://example.com",
    }


def test_validate_label_truncated_to_200(svc: RunnerService) -> None:
    out = svc._validate_recommendation(
        {"kind": "next-workflow", "name": "code-review", "label": "x" * 300}
    )
    assert out is not None
    assert out["label"] == "x" * 200


def test_validate_non_str_label_dropped(svc: RunnerService) -> None:
    out = svc._validate_recommendation(
        {"kind": "next-workflow", "name": "code-review", "label": 42}
    )
    assert out == {"kind": "next-workflow", "name": "code-review"}


def test_validate_severity_lowercased_and_truncated(svc: RunnerService) -> None:
    out = svc._validate_recommendation(
        {"kind": "next-workflow", "name": "code-review", "severity": "URGENT" * 10}
    )
    assert out is not None
    assert out["severity"] == ("urgent" * 10)[:20]


def test_validate_non_str_severity_dropped(svc: RunnerService) -> None:
    out = svc._validate_recommendation(
        {"kind": "next-workflow", "name": "code-review", "severity": 3}
    )
    assert out == {"kind": "next-workflow", "name": "code-review"}


@pytest.mark.parametrize("name", [None, "", 42], ids=["missing", "empty", "non-str"])
def test_validate_rejects_bad_next_workflow_name(svc: RunnerService, name: object) -> None:
    payload: dict[str, object] = {"kind": "next-workflow"}
    if name is not None:
        payload["name"] = name
    assert svc._validate_recommendation(payload) is None


def test_validate_rejects_args_not_an_object(svc: RunnerService) -> None:
    out = svc._validate_recommendation(
        {"kind": "next-workflow", "name": "code-review", "args": "src/"}
    )
    assert out is None


def test_validate_args_without_path_omits_args_key(svc: RunnerService) -> None:
    # Unknown args keys are dropped; an args dict that sanitizes to
    # empty produces NO "args" key at all (not an empty dict).
    out = svc._validate_recommendation(
        {"kind": "next-workflow", "name": "code-review", "args": {"depth": "quick"}}
    )
    assert out == {"kind": "next-workflow", "name": "code-review"}


@pytest.mark.parametrize("bad_path", ["", 42], ids=["empty", "non-str"])
def test_validate_rejects_bad_args_path(svc: RunnerService, bad_path: object) -> None:
    out = svc._validate_recommendation(
        {"kind": "next-workflow", "name": "code-review", "args": {"path": bad_path}}
    )
    assert out is None


def test_validate_path_passes_through_without_project_root() -> None:
    # project_root=None disables path validation (test-fixture wiring);
    # the raw string passes through unvalidated and unresolved.
    svc = RunnerService(project_root=None)
    out = svc._validate_recommendation(
        {"kind": "next-workflow", "name": "code-review", "args": {"path": "src/anything"}}
    )
    assert out == {
        "kind": "next-workflow",
        "name": "code-review",
        "args": {"path": "src/anything"},
    }


def test_validate_accepts_open_url_plain_http(svc: RunnerService) -> None:
    out = svc._validate_recommendation({"kind": "open-url", "url": "http://localhost:8765/x"})
    assert out == {"kind": "open-url", "url": "http://localhost:8765/x"}


def test_validate_rejects_non_str_url(svc: RunnerService) -> None:
    assert svc._validate_recommendation({"kind": "open-url", "url": 7}) is None
    assert svc._validate_recommendation({"kind": "open-url"}) is None


# ----------------------------------------------------------------------
# RunnerService.handle_stdout_line — marker parsing
# ----------------------------------------------------------------------


def test_handle_stdout_line_routes_marker_to_recommendation(svc: RunnerService) -> None:
    run = _new_run()
    svc.handle_stdout_line(
        run,
        'ATTUNE_REC {"kind": "open-url", "url": "https://x"}',
    )
    assert run.lines == []  # marker dropped from log
    assert run.recommendations == [{"kind": "open-url", "url": "https://x"}]


def test_handle_stdout_line_appends_non_marker_lines_normally(svc: RunnerService) -> None:
    run = _new_run()
    svc.handle_stdout_line(run, "Starting analysis...")
    assert run.lines == ["Starting analysis..."]
    assert run.recommendations == []


def test_handle_stdout_line_ignores_malformed_json(
    svc: RunnerService, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="attune.ops.runner")
    run = _new_run()
    svc.handle_stdout_line(run, "ATTUNE_REC {not valid json")
    assert run.lines == []
    assert run.recommendations == []
    assert any("malformed JSON" in r.message for r in caplog.records)


def test_handle_stdout_line_drops_invalid_payload(svc: RunnerService) -> None:
    run = _new_run()
    svc.handle_stdout_line(run, 'ATTUNE_REC {"kind": "no-such-kind"}')
    assert run.lines == []
    assert run.recommendations == []


# ----------------------------------------------------------------------
# Markup smoke — run_view.js exports
# ----------------------------------------------------------------------


def test_run_view_js_exports_recommendation_card_renderer() -> None:
    js_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "attune"
        / "ops"
        / "static"
        / "js"
        / "run_view.js"
    )
    text = js_path.read_text(encoding="utf-8")
    assert "function renderRecommendationCard(" in text
    assert "renderRecommendationCard: renderRecommendationCard" in text
    assert "function isSafeUrl(" in text
    # SSE listener wired
    assert 'addEventListener("recommendation"' in text
    # Slot selector
    assert "[data-recommendations]" in text
