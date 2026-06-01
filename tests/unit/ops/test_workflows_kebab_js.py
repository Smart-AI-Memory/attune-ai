"""Source-grep tests for workflows_kebab.js (A3b).

Mirrors the test_workflows_refined_js.py pattern from A3a +
the test_specs_routes.py::test_specs_kebab_js_* convention.
Grep the JS source for the documented exports and key behaviors
so future PRs can't accidentally remove them.

A3b ships the row-level kebab action menu with 3 actions per
decisions.md D5:
- View recent runs   → toggles per-row .recent-runs strip
- Copy run command   → `attune workflow run <name>` (+scope)
- View docs          → /help/<workflow-name> in new tab
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
    / "workflows_kebab.js"
)


@pytest.fixture(scope="module")
def js_text() -> str:
    return JS_PATH.read_text(encoding="utf-8")


class TestExposedSurface:
    """workflows_kebab.js exposes the documented API surface."""

    def test_namespace_export(self, js_text: str) -> None:
        """Mirrors __attuneSpecsKebab / __attuneWorkflows convention."""
        assert "window.__attuneWorkflowsKebab" in js_text

    @pytest.mark.parametrize(
        "name", ["openMenuFor", "closeMenu", "handleAction", "showToast", "init"]
    )
    def test_export_present(self, js_text: str, name: str) -> None:
        """Each documented export must appear in the source."""
        assert name in js_text, f"missing export: {name}"


class TestThreeActions:
    """The kebab menu offers exactly 3 actions per decisions.md D5."""

    def test_action_view_recent_runs(self, js_text: str) -> None:
        """Action 1: View recent runs."""
        assert '"recent"' in js_text
        assert "View recent runs" in js_text

    def test_action_copy_run_command(self, js_text: str) -> None:
        """Action 2: Copy run command."""
        assert '"copy"' in js_text
        assert "Copy run command" in js_text

    def test_action_view_docs(self, js_text: str) -> None:
        """Action 3: View docs."""
        assert '"docs"' in js_text
        assert "View docs" in js_text


class TestActionBehavior:
    """Each action's implementation is recognizable in source."""

    def test_recent_action_toggles_strip(self, js_text: str) -> None:
        """View recent runs toggles `data-recent-runs` attribute element."""
        assert "data-recent-runs" in js_text

    def test_copy_action_builds_run_command(self, js_text: str) -> None:
        """Copy run command formats `attune workflow run <name>`."""
        # Avoid CodeQL py/incomplete-url-substring-sanitization issues
        # by anchoring on the literal prefix.
        assert "attune workflow run " in js_text

    def test_copy_action_includes_scope_when_picker_set(self, js_text: str) -> None:
        """When the row's scope picker has a value, --path is appended."""
        assert "--path" in js_text
        assert ".scope-picker" in js_text

    def test_docs_action_opens_help_page(self, js_text: str) -> None:
        """View docs opens /help/<name> in a new tab."""
        # Anchored on the path fragment to dodge the CodeQL URL-
        # substring rule (per the existing CLAUDE.md lesson).
        assert '"/help/"' in js_text
        # Opens in new tab with noopener/noreferrer for safety.
        assert "_blank" in js_text
        assert "noopener" in js_text


class TestMenuLifecycle:
    """Menu open/close behaviors per decisions.md."""

    def test_closes_on_escape(self, js_text: str) -> None:
        """Escape key closes the menu."""
        assert "Escape" in js_text

    def test_closes_on_outside_click(self, js_text: str) -> None:
        """Click outside closes the menu (delegated handler)."""
        # `document.addEventListener("click", ...)` is the outside-click
        # listener; check the literal pattern.
        assert 'document.addEventListener("click"' in js_text

    def test_one_menu_at_a_time(self, js_text: str) -> None:
        """openMenu / closeMenu enforce single-instance behavior."""
        assert "closeMenu()" in js_text


class TestDOMSelectors:
    """JS targets the template's expected DOM hooks."""

    def test_targets_kebab_buttons(self, js_text: str) -> None:
        """Kebab click handler binds to `.kebab-btn[data-kebab]`."""
        assert ".kebab-btn[data-kebab]" in js_text


class TestTemplateIntegration:
    """The template references the JS file and renders kebab buttons."""

    def test_template_loads_workflows_kebab_js(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "attune"
            / "ops"
            / "templates"
            / "workflows.html"
        )
        template_text = template_path.read_text(encoding="utf-8")
        assert "workflows_kebab.js" in template_text

    def test_template_renders_kebab_column_header(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "attune"
            / "ops"
            / "templates"
            / "workflows.html"
        )
        template_text = template_path.read_text(encoding="utf-8")
        assert "col-kebab" in template_text

    def test_template_renders_kebab_button_per_row(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "attune"
            / "ops"
            / "templates"
            / "workflows.html"
        )
        template_text = template_path.read_text(encoding="utf-8")
        assert 'class="kebab-btn"' in template_text
        assert 'data-kebab="{{ w.name }}"' in template_text


class TestReadOnlyModeSafe:
    """All 3 actions are non-mutating; menu works in read-only mode."""

    def test_no_allow_run_gate_in_template(self) -> None:
        """Kebab column header is rendered without allow_run gating."""
        template_path = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "attune"
            / "ops"
            / "templates"
            / "workflows.html"
        )
        template_text = template_path.read_text(encoding="utf-8")
        # The col-kebab header should NOT be inside an `{% if allow_run %}`
        # block. Grep for the literal context — col-kebab appears
        # immediately after the closing `{% endif %}` of the Action column,
        # so it's rendered for both run and read-only modes.
        assert "col-kebab" in template_text
        # No `{% if allow_run %}...col-kebab` pattern.
        idx = template_text.find("col-kebab")
        # Look backwards 200 chars; should not contain `{% if allow_run %}`
        # that opens a block enclosing col-kebab.
        prefix = template_text[max(0, idx - 200) : idx]
        # The col-kebab header line is OUTSIDE the allow_run conditional.
        # Should follow `{% endif %}` (the closing of the Action col).
        assert "{% endif %}" in prefix
