"""Tests for the security-audit severity dashboard renderer.

Spec: docs/specs/security-audit-rich-output/.
"""

from __future__ import annotations

import pytest

from attune.workflows.security_audit_dashboard import security_findings_dashboard_html

pytestmark = pytest.mark.unit


def _f(**over):
    base = {
        "severity": "high",
        "file": "src/x.py",
        "line": 10,
        "message": "risky thing",
        "code": None,
    }
    base.update(over)
    return base


class TestStructure:
    def test_renders_dashboard_container(self):
        html = security_findings_dashboard_html([_f()])
        assert 'id="sa-dash"' in html

    def test_severity_count_chips(self):
        html = security_findings_dashboard_html(
            [_f(severity="critical"), _f(severity="critical"), _f(severity="low")]
        )
        assert "critical <b>2</b>" in html
        assert "low <b>1</b>" in html
        # a severity with zero findings gets no chip
        assert "medium <b>" not in html

    def test_score_chip_shown_when_given(self):
        assert "health 80/100" in security_findings_dashboard_html([_f()], score=80)

    def test_score_chip_omitted_when_none(self):
        assert "health" not in security_findings_dashboard_html([_f()])

    def test_empty_findings_says_clean(self):
        html = security_findings_dashboard_html([])
        assert "no findings — clean" in html


class TestSeverity:
    def test_cards_sorted_critical_first(self):
        html = security_findings_dashboard_html(
            [_f(severity="low", message="LOW-ONE"), _f(severity="critical", message="CRIT-ONE")]
        )
        assert html.index("CRIT-ONE") < html.index("LOW-ONE")

    def test_unknown_severity_does_not_crash(self):
        assert "risky thing" in security_findings_dashboard_html([_f(severity="weird")])


class TestFields:
    def test_missing_location_renders_dash(self):
        assert "—" in security_findings_dashboard_html([_f(file=None, line=None)])

    def test_file_without_line_no_dangling_colon(self):
        html = security_findings_dashboard_html([_f(file="src/y.py", line=None)])
        assert "src/y.py" in html and "src/y.py:" not in html

    def test_code_rendered_when_present(self):
        html = security_findings_dashboard_html([_f(code="subprocess.run(x, shell=True)")])
        assert "subprocess.run(x, shell=True)" in html
        assert '<pre class="sa-code">' in html

    def test_no_code_block_when_absent(self):
        # the .sa-code CSS rule is always in <style>; assert no <pre> element.
        html = security_findings_dashboard_html([_f(code=None)])
        assert '<pre class="sa-code">' not in html


class TestRobustness:
    def test_string_findings_render_as_info_cards(self):
        # legacy/flat path can hand back bare strings — must not crash.
        html = security_findings_dashboard_html(["just a string finding", _f(severity="high")])
        assert "just a string finding" in html
        assert "info <b>1</b>" in html  # the string finding counts as info
        assert "high <b>1</b>" in html

    def test_string_finding_escaped(self):
        html = security_findings_dashboard_html(["<script>alert(1)</script>"])
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html


class TestInjectionSafety:
    def test_finding_text_escaped(self):
        html = security_findings_dashboard_html(
            [_f(message="<script>alert(1)</script>", file="a<b>", code="<img src=x onerror=y>")]
        )
        assert "<script>alert(1)</script>" not in html
        assert "<img src=x" not in html
        assert "&lt;script&gt;" in html
        assert "a&lt;b&gt;" in html

    def test_no_script_tag_in_output(self):
        assert "<script" not in security_findings_dashboard_html([_f()]).lower()
