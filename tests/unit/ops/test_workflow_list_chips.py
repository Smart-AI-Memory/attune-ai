"""Phase 3 — chip-count loader + UI plumbing tests.

Covers ``data.read_sweep_chip_counts`` (missing/corrupt/populated)
plus the workflow-list page integration: discovery-sweep row emits
the chip block with the right anchors and chip-row JS hooks are
present in ``runner.js``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.ops import data, sweep_results
from attune.ops.config import Config
from attune.ops.server import create_app

_RUNNER_JS = (
    Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "static" / "js" / "runner.js"
)
_RUN_VIEW_JS = (
    Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "static" / "js" / "run_view.js"
)


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    project = tmp_path / "project"
    project.mkdir()
    return Config(
        project_root=project,
        attune_home=tmp_path / "attune-home",
    )


@pytest.fixture()
def client(cfg: Config) -> TestClient:
    app = create_app(cfg)
    c = TestClient(app)
    c.headers["Host"] = f"{cfg.host}:{cfg.port}"
    return c


class TestReadSweepChipCounts:
    def test_missing_file_returns_zero_no_result(self, cfg: Config) -> None:
        counts = data.read_sweep_chip_counts("src/", cfg)
        assert counts.has_result is False
        assert counts.queue == 0
        assert counts.questions == 0
        assert counts.rejected == 0
        assert counts.scope_hash == sweep_results.scope_hash("src/")

    def test_populated_file_returns_counts(self, cfg: Config) -> None:
        payload = {
            "queue": [{"a": i} for i in range(5)],
            "questions": [{"finding": {}, "reason": "r", "next_step": "ns"}],
            "rejected": [],
            "metadata": {},
        }
        sweep_results.persist_result("src/", payload, cfg)
        counts = data.read_sweep_chip_counts("src/", cfg)
        assert counts.has_result is True
        assert counts.queue == 5
        assert counts.questions == 1
        assert counts.rejected == 0

    def test_corrupt_file_falls_back_to_zero(self, cfg: Config) -> None:
        # Write a syntactically-broken sidecar; read_result logs a
        # warning and returns None, so chips read False/0/0/0.
        out_dir = sweep_results.results_dir(cfg)
        digest = sweep_results.scope_hash("src/")
        (out_dir / f"{digest}.json").write_text("{not json", encoding="utf-8")
        counts = data.read_sweep_chip_counts("src/", cfg)
        assert counts.has_result is False
        assert (counts.queue, counts.questions, counts.rejected) == (0, 0, 0)

    def test_buckets_missing_in_payload_treated_as_empty(self, cfg: Config) -> None:
        # Old sidecars or hand-edited files may omit fields entirely.
        # The loader treats those as empty buckets (has_result True
        # because read_result returned a dict).
        out_dir = sweep_results.results_dir(cfg)
        digest = sweep_results.scope_hash("src/")
        (out_dir / f"{digest}.json").write_text("{}", encoding="utf-8")
        counts = data.read_sweep_chip_counts("src/", cfg)
        assert counts.has_result is True
        assert (counts.queue, counts.questions, counts.rejected) == (0, 0, 0)


class TestWorkflowsPageChips:
    def test_discovery_sweep_row_renders_chips(self, client: TestClient, cfg: Config) -> None:
        resp = client.get("/workflows")
        assert resp.status_code == 200
        body = resp.text
        # Chip block markers exist for the discovery-sweep row.
        assert "data-sweep-chips" in body
        assert 'data-chip="queue"' in body
        assert 'data-chip="questions"' in body
        assert 'data-chip="rejected"' in body
        # Chips are anchors to the scope-keyed detail route filtered
        # by bucket.
        assert "/workflows/discovery-sweep/results/" in body
        assert "?bucket=queue" in body
        assert "?bucket=questions" in body
        assert "?bucket=rejected" in body

    def test_chips_reflect_persisted_counts(self, client: TestClient, cfg: Config) -> None:
        # Persist for the default scope of discovery-sweep on this project
        # (no features.yaml present, so scope falls back to project_root).
        default_scope = data.workflow_default_scope("discovery-sweep", cfg.project_root) or str(
            cfg.project_root
        )
        payload = {
            "queue": [{"a": 1}, {"a": 2}, {"a": 3}, {"a": 4}],
            "questions": [],
            "rejected": [{"finding": {}, "rule": "r"}, {"finding": {}, "rule": "s"}],
            "metadata": {},
        }
        sweep_results.persist_result(default_scope, payload, cfg)
        resp = client.get("/workflows")
        assert resp.status_code == 200
        body = resp.text
        # The chip span carries the count value directly. Look for the
        # discovery-sweep row's chip block then check the rendered counts.
        chip_block = re.search(r"data-sweep-chips[^>]*>(.*?)</div>", body, re.DOTALL)
        assert chip_block is not None
        block_text = chip_block.group(1)
        # Counts appear inside data-chip-count spans.
        queue_match = re.search(
            r'data-chip="queue"[^>]*>.*?data-chip-count>(\d+)<', block_text, re.DOTALL
        )
        rejected_match = re.search(
            r'data-chip="rejected"[^>]*>.*?data-chip-count>(\d+)<',
            block_text,
            re.DOTALL,
        )
        assert queue_match is not None and queue_match.group(1) == "4"
        assert rejected_match is not None and rejected_match.group(1) == "2"


class TestRunnerJsSweepHooks:
    """The Phase 3 chip-refresh + sweep-progress entry points exist."""

    def test_runner_js_exposes_chip_helpers(self) -> None:
        text = _RUNNER_JS.read_text(encoding="utf-8")
        assert "refreshSweepChips" in text
        assert "applyChipCounts" in text
        assert "wireSweepChipRefresh" in text
        # The fetch path uses the API endpoint, not the HTML page URL.
        assert "/api/workflows/discovery-sweep/chips" in text

    def test_run_view_js_parses_sweep_events(self) -> None:
        text = _RUN_VIEW_JS.read_text(encoding="utf-8")
        assert "parseSweepEventLine" in text
        assert "updateSweepProgress" in text
        # All three event kinds handled.
        for ev in ("source_started", "source_finished", "source_failed"):
            assert ev in text


class TestRunViewProgressMarkup:
    """run_view.html ships the static progress markup for discovery-sweep."""

    @pytest.fixture()
    def run_client(self, tmp_path: Path) -> TestClient:
        """A client with ``allow_run=True`` so the runner has disk persistence.

        ``_build_default_runner`` skips persistence when ``allow_run=False``
        (read-only dashboards don't write to ``~/.attune``). The disk-
        fallback path under test only fires when the runner has a
        persistence_dir, so this test needs its own client.
        """
        project = tmp_path / "project"
        project.mkdir()
        cfg = Config(
            project_root=project,
            attune_home=tmp_path / "attune-home",
            allow_run=True,
        )
        app = create_app(cfg)
        c = TestClient(app)
        c.headers["Host"] = f"{cfg.host}:{cfg.port}"
        # Stash the cfg on the client for the test body.
        c._cfg = cfg  # type: ignore[attr-defined]
        return c

    def test_discovery_sweep_row_emits_progress_panel(self, run_client: TestClient) -> None:
        client = run_client
        cfg: Config = client._cfg  # type: ignore[attr-defined]
        # Build a synthetic disk-only run so the route's disk-fallback
        # branch fires without spinning up the runner. The persistence
        # shape mirrors ``_persist_run`` in ``attune.ops.runner``.
        import json

        run_id = "0123456789abcdef"
        record = {
            "id": run_id,
            "workflow": "discovery-sweep",
            "status": "completed",
            "exit_code": 0,
            "started_at": "2026-05-16T00:00:00+00:00",
            "completed_at": "2026-05-16T00:00:10+00:00",
            "path": "src/",
            "lines": [
                "ATTUNE_DS_VERSION 1",
                "ATTUNE_DS source_started bug-predict ts=2026-05-16T00:00:01+00:00",
                "ATTUNE_DS source_finished bug-predict ts=2026-05-16T00:00:05+00:00 findings=3",
            ],
            "config_meta": {},
        }
        wf_dir = cfg.runs_dir / "discovery-sweep"
        wf_dir.mkdir(parents=True, exist_ok=True)
        (wf_dir / f"{run_id}.json").write_text(json.dumps(record), encoding="utf-8")
        resp = client.get(f"/runs/{run_id}/view")
        assert resp.status_code == 200
        body = resp.text
        assert "data-sweep-progress" in body
        # Each canonical source has its own static <li>.
        for src in (
            "bug-predict",
            "dependency-check",
            "doc-audit",
            "pattern-scan",
            "perf-audit",
            "security-audit",
            "test-audit",
        ):
            assert f'data-source="{src}"' in body
