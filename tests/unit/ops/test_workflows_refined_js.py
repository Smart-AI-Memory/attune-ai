"""Source-grep tests for workflows_refined.js (A3a).

Same pattern as test_specs_routes.py::test_specs_refined_js_exposes_*
and test_runner_js_parsing.py — grep the JS source for the documented
exports and key behaviors so future PRs can't accidentally remove
them without the test failing loudly.

A3a ships the chip filter + search + per-row concern pill. A3b and
A3c hook the same state/surface; this test guards against accidental
removal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

JS_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "attune"
    / "ops"
    / "static"
    / "js"
    / "workflows_refined.js"
)


@pytest.fixture(scope="module")
def js_text() -> str:
    """Read workflows_refined.js once for the module."""
    return JS_PATH.read_text(encoding="utf-8")


class TestExposedSurface:
    """workflows_refined.js exposes the documented API surface."""

    def test_namespace_export(self, js_text: str) -> None:
        """Window export — namespace mirrors __attuneSpecs convention."""
        assert "window.__attuneWorkflows" in js_text

    def test_exposes_valid_buckets(self, js_text: str) -> None:
        assert "VALID_BUCKETS" in js_text

    def test_exposes_state(self, js_text: str) -> None:
        assert "state" in js_text

    def test_exposes_apply_filters(self, js_text: str) -> None:
        assert "applyFilters" in js_text

    def test_exposes_set_chip_state(self, js_text: str) -> None:
        """Future PRs (A3b kebab) may toggle chips programmatically."""
        assert "setChipState" in js_text

    def test_exposes_init(self, js_text: str) -> None:
        assert "init" in js_text


class TestBucketSet:
    """The 7 concern buckets all appear in VALID_BUCKETS."""

    @pytest.mark.parametrize(
        "bucket",
        ["review", "test", "docs", "refactor", "audit", "meta", "other"],
    )
    def test_bucket_present(self, js_text: str, bucket: str) -> None:
        """Each of the 7 buckets must be in the JS source.

        If a bucket is renamed in decisions.md, this test catches the
        JS-side drift at CI level rather than at runtime.
        """
        # Bucket strings appear inside the VALID_BUCKETS Set literal.
        # Asserting the quoted form catches both single and double
        # quotes; specs_refined.js uses double, so we mirror.
        assert f'"{bucket}"' in js_text


class TestDefaultBehavior:
    """Default state per decisions.md D1/D2."""

    def test_all_buckets_default_on(self, js_text: str) -> None:
        """state.buckets initializes from VALID_BUCKETS (all 7 on).

        Unlike specs_refined.js (which defaults Complete off), Workflows
        page has no chip that's structurally "noise" — all 7 are
        relevant defaults.
        """
        # state.buckets = new Set(VALID_BUCKETS) is the literal default.
        assert "new Set(VALID_BUCKETS)" in js_text


class TestDOMSelectors:
    """The JS targets the template's expected DOM hooks."""

    def test_targets_workflows_table_tbody(self, js_text: str) -> None:
        """JS reads rows from `.workflows-table tbody`."""
        assert ".workflows-table tbody" in js_text

    def test_targets_workflows_toolbar_chips(self, js_text: str) -> None:
        """Chip click handler binds to `.workflows-toolbar .chip[data-bucket]`."""
        assert ".workflows-toolbar .chip[data-bucket]" in js_text

    def test_targets_search_input(self, js_text: str) -> None:
        """Search input ID is `#workflows-search`."""
        assert "#workflows-search" in js_text

    def test_reads_data_concern(self, js_text: str) -> None:
        """JS reads `data-concern` attribute from each <tr>."""
        assert "data-concern" in js_text

    def test_reads_data_workflow(self, js_text: str) -> None:
        """JS reads `data-workflow` attribute for name-based search."""
        assert "data-workflow" in js_text


class TestEmptyStateBehavior:
    """A3a injects an empty-state element when all rows hide."""

    def test_creates_empty_state_element(self, js_text: str) -> None:
        assert "workflows-empty-state" in js_text

    def test_handles_all_chips_off_message(self, js_text: str) -> None:
        """Message names the recovery action."""
        assert "All concerns filtered out" in js_text

    def test_handles_no_match_message(self, js_text: str) -> None:
        """Message shows search query."""
        assert "No workflows" in js_text


class TestTemplateIntegration:
    """The template references the JS file at the documented path."""

    def test_template_loads_workflows_refined_js(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "attune"
            / "ops"
            / "templates"
            / "workflows.html"
        )
        template_text = template_path.read_text(encoding="utf-8")
        assert "workflows_refined.js" in template_text


class TestURLStateSurface:
    """A3c — URL param parsing + state sync.

    The JS module exposes readURLState/syncURL on the namespace and
    wires them into chip + search handlers so ?bucket=…&q=… is the
    source of truth on init and updates as the user toggles.
    """

    def test_exposes_read_url_state(self, js_text: str) -> None:
        """readURLState is on the public surface."""
        assert "readURLState" in js_text

    def test_exposes_sync_url(self, js_text: str) -> None:
        """syncURL is on the public surface."""
        assert "syncURL" in js_text

    def test_exposes_buckets_are_default(self, js_text: str) -> None:
        """bucketsAreDefault helper for clean-URL detection."""
        assert "bucketsAreDefault" in js_text

    def test_parses_bucket_query_param(self, js_text: str) -> None:
        """URL ?bucket= is read into state.buckets."""
        assert 'searchParams.get("bucket")' in js_text

    def test_parses_q_query_param(self, js_text: str) -> None:
        """URL ?q= is read into state.search."""
        assert 'searchParams.get("q")' in js_text

    def test_uses_replace_state_not_push(self, js_text: str) -> None:
        """Toggling a chip uses replaceState — toggles don't pollute
        browser history.
        """
        assert "history.replaceState" in js_text

    def test_clean_url_when_defaults(self, js_text: str) -> None:
        """When all buckets are on and search is empty, both params
        are removed from the URL.
        """
        assert 'searchParams.delete("bucket")' in js_text
        assert 'searchParams.delete("q")' in js_text

    def test_sync_url_called_on_chip_toggle(self, js_text: str) -> None:
        """The chip click handler calls syncURL() after applyFilters()."""
        # Pattern: applyFilters() is called, then syncURL() within the
        # same handler. Just check syncURL() appears more than once
        # (definition + at least one call site).
        assert js_text.count("syncURL()") >= 2

    def test_init_calls_read_url_state(self, js_text: str) -> None:
        """init() reads URL state before wiring handlers."""
        assert "readURLState()" in js_text
