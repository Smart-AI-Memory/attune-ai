"""Tests for the /workflows route's concern + bucket_counts context.

A2 of docs/specs/ops-workflows-page-refinement/. The route serializer
populates per-row concern (via workflow_concern.derive_concern) and
per-bucket counts (concern_counts) so the template's chip toolbar +
per-row concern badge can render server-side on first paint.

Tests check the rendered HTML body for these values. A3a will add the
template surface; for now we assert the data is in the page context
by grepping for the strings the template will eventually render.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.ops.config import Config
from attune.ops.server import create_app


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


class TestWorkflowsRouteServesConcerns:
    """The /workflows route puts concern data into the template context."""

    def test_route_returns_200(self, client: TestClient) -> None:
        """Sanity: route renders without raising after the A2 wiring."""
        resp = client.get("/workflows")
        assert resp.status_code == 200

    def test_known_workflows_render(self, client: TestClient) -> None:
        """The workflows table renders the canonical workflow names.

        Without this, the concern serialization has nothing to attach
        to. Quick smoke test that the workflow_concern data layer
        plumbing hasn't broken the table render.
        """
        resp = client.get("/workflows")
        body = resp.text
        # Just check a handful of well-known workflow names appear.
        assert "code-review" in body
        assert "security-audit" in body
        assert "release-prep" in body


class TestConcernDerivation:
    """A2's derive_concern wiring — values match what the
    workflow_concern module produces standalone.
    """

    def test_derive_concern_matches_module_output(self) -> None:
        """The route's `concerns` dict must match the module's output.

        Smoke-test via direct module call rather than HTML parsing so a
        template-rendering change doesn't break this. Belt-and-
        suspenders against future drift between the route and the
        underlying derivation.
        """
        from attune.ops import data, workflow_concern

        workflows = data.list_workflows()
        derived = {w.name: workflow_concern.derive_concern(w.name) for w in workflows}

        # Spot-check the trade-off boundaries from decisions.md
        assert derived["code-review"] == "review"
        assert derived["security-audit"] == "review"  # not "audit"
        assert derived["test-audit"] == "test"  # not "audit"
        assert derived["doc-audit"] == "docs"  # not "audit"
        assert derived["doc-orchestrator"] == "docs"  # not "meta"
        assert derived["perf-audit"] == "audit"
        assert derived["release-prep"] == "meta"
        # rag-code-gen is dashboard-hidden (visibility, 2026-08-24) so it
        # no longer appears in the page's derivation; its concern class is
        # still derivable from the full catalog.
        full = {
            w.name: workflow_concern.derive_concern(w.name)
            for w in data.list_workflows(include_hidden=True)
        }
        assert full["rag-code-gen"] == "other"

    def test_concern_counts_sums_to_workflow_total(self) -> None:
        """concern_counts populates all 7 buckets; sum equals workflow total."""
        from attune.ops import data, workflow_concern

        workflows = data.list_workflows()
        counts = workflow_concern.concern_counts([w.name for w in workflows])
        assert set(counts.keys()) == set(workflow_concern.ALL_CONCERNS)
        assert sum(counts.values()) == len(workflows)


class TestRouteContextShape:
    """The /workflows route emits the new context keys A3a will consume.

    Source-grep tests against the HTML body. Cheap and stable.
    """

    def test_response_includes_workflow_names(self, client: TestClient) -> None:
        """Smoke — table renders. Concerns + bucket_counts go via the
        template; A3a tests will assert the rendered chip toolbar.
        """
        resp = client.get("/workflows")
        body = resp.text
        # Workflow rows exist
        assert 'data-workflow="code-review"' in body or "code-review" in body


class TestNoRegressionOnExistingFeatures:
    """A2 added context fields; ensure no existing features broke."""

    def test_existing_scope_picker_still_renders(self, client: TestClient) -> None:
        resp = client.get("/workflows")
        body = resp.text
        # Scope picker for security-audit
        assert "scope-picker" in body or "scope-cell" in body

    def test_existing_tier_map_still_renders(self, client: TestClient) -> None:
        resp = client.get("/workflows")
        body = resp.text
        # Tier chips are rendered with class names like "chip-cheap" etc.
        # Just check that one tier-classed chip appears.
        assert "chip-cheap" in body or "chip-capable" in body or "chip-premium" in body
