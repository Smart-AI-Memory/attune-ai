"""Unit tests for DiscoverySweepWorkflow.execute().

Covers:

- Happy path with two fake sources (one returns findings, one raises)
- Budget allocation between LLM and non-LLM sources
- ``no_llm`` filter
- ``path`` validation
- Source-failure isolation (per spec NFR-1)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from attune.workflows.discovery_sweep import (
    DEFAULT_BUDGET_USD,
    DiscoverySweepWorkflow,
    Finding,
    SweepResult,
)


@dataclass
class FakeSource:
    """Test double conforming structurally to FindingSource.

    ``budget_multiplier`` defaults to ``1.0`` for LLM sources and
    ``0.0`` for non-LLM sources via ``__post_init__`` so tests can omit
    it unless they want a specific share.
    """

    name: str
    is_llm: bool = True
    budget_multiplier: float | None = None
    findings: list[Finding] | None = None
    raises: BaseException | None = None
    received_budget: float | None = None
    received_paths: list[str] | None = None
    # Mirrors LLMSource.spent_usd — what each real source accumulates via
    # ``_record_cost`` and the engine sums into ``SweepMetadata.spent_usd``.
    spent_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.budget_multiplier is None:
            self.budget_multiplier = 1.0 if self.is_llm else 0.0

    async def discover(self, paths: list[str], budget_usd: float) -> list[Finding]:
        self.received_paths = list(paths)
        self.received_budget = budget_usd
        if self.raises is not None:
            raise self.raises
        return list(self.findings or [])


def _finding(**overrides: object) -> Finding:
    base: dict[str, object] = {
        "source": "fake",
        "severity": "high",
        "title": "t",
        "description": "d",
        "file": "src/a.py",
        "line": 10,
        "evidence": None,
        "confidence": 0.9,
        "tags": (),
    }
    base.update(overrides)
    return Finding(**base)  # type: ignore[arg-type]


class TestExecuteHappyPath:
    def test_findings_route_to_queue(self) -> None:
        src = FakeSource(name="fake-src", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        assert res.success is True
        sweep: SweepResult = res.metadata["sweep"]
        assert len(sweep.queue) == 1
        assert sweep.queue[0].source == "fake"
        assert sweep.metadata.sources == ["fake-src"]
        assert sweep.metadata.failures == []

    def test_two_sources_one_findings_one_raises(self) -> None:
        good = FakeSource(name="good", findings=[_finding()])
        bad = FakeSource(name="bad", raises=RuntimeError("boom"))
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[good, bad]))
        sweep: SweepResult = res.metadata["sweep"]
        # Good source's finding makes it through.
        assert len(sweep.queue) == 1
        # Bad source surfaces as a question, not a sweep-level failure.
        assert any(q.reason == "SOURCE_FAILED" for q in sweep.questions)
        assert sweep.metadata.failures == ["bad: RuntimeError"]
        assert sweep.metadata.sources == ["good", "bad"]
        assert res.success is True

    def test_final_output_renders_buckets(self) -> None:
        src = FakeSource(name="fake-src", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        assert isinstance(res.final_output, str)
        assert "## Queue" in res.final_output
        assert "## Questions" in res.final_output
        assert "## Rejected" in res.final_output


def _failure_marker(source: str) -> Finding:
    """The shape every LLM source emits when its wrapped workflow
    reports success=False (see llm_source_base.workflow_unsuccessful_
    finding) — info severity, file set, tagged source-failure."""
    return _finding(
        source=source,
        severity="info",
        title=f"{source} returned an unsuccessful result for src/",
        file="src/",
        line=None,
        confidence=1.0,
        tags=("source-failure",),
    )


class TestSourceFailureSurfacing:
    """Regression suite for the 2026-07-14 silent-failure class: six of
    seven sources returned only success=False markers, which routing
    buried in ``rejected`` while the sweep rendered success=True with
    no failures named (docs/reports/library-health-2026-07-14.md,
    finding 1)."""

    def test_majority_dead_sources_fail_the_sweep(self) -> None:
        # The live 6-of-7 scenario: one healthy pattern source, six
        # sources that produced nothing but failure markers.
        healthy = FakeSource(name="pattern-scan", is_llm=False, findings=[_finding()])
        dead = [
            FakeSource(name=n, findings=[_failure_marker(n)])
            for n in (
                "bug-predict",
                "security-audit",
                "dependency-check",
                "perf-audit",
                "doc-audit",
                "test-audit",
            )
        ]
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[healthy, *dead]))
        sweep: SweepResult = res.metadata["sweep"]

        # The sweep is FAILED, and says why.
        assert res.success is False
        assert res.error is not None
        assert "6 of 7 sources failed" in res.error
        # Every dead source is named in metadata.failures.
        assert len(sweep.metadata.failures) == 6
        assert all("returned only failure markers" in f for f in sweep.metadata.failures)
        # Failure markers surface as questions — never buried in rejected.
        assert sum(q.reason == "SOURCE_FAILED" for q in sweep.questions) == 6
        assert not any(
            "source-failure" in r.finding.tags for r in sweep.rejected
        ), "failure markers must never land in the rejected bucket"
        # The healthy source's finding still flows to the queue.
        assert len(sweep.queue) == 1

    def test_minority_failures_keep_success_but_are_named(self) -> None:
        healthy = [FakeSource(name=f"ok-{i}", findings=[_finding()]) for i in range(3)]
        dead = FakeSource(name="doc-audit", findings=[_failure_marker("doc-audit")])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[*healthy, dead]))
        sweep: SweepResult = res.metadata["sweep"]

        assert res.success is True
        assert sweep.metadata.failures == ["doc-audit: returned only failure markers"]

    def test_markdown_banner_names_partial_sweep(self) -> None:
        healthy = [FakeSource(name=f"ok-{i}", findings=[_finding()]) for i in range(3)]
        dead = FakeSource(name="doc-audit", findings=[_failure_marker("doc-audit")])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[*healthy, dead]))

        assert "PARTIAL SWEEP: 1 of 4 source(s) failed" in res.final_output
        assert "doc-audit" in res.final_output

    def test_healthy_source_with_incidental_failure_marker_not_counted(self) -> None:
        # A source that produced real findings PLUS one failure marker
        # (e.g. one path of several failed) is degraded, not dead — it
        # must not count toward the failure majority.
        mixed = FakeSource(
            name="doc-audit",
            findings=[_finding(source="doc-audit"), _failure_marker("doc-audit")],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[mixed]))
        sweep: SweepResult = res.metadata["sweep"]

        assert res.success is True
        assert sweep.metadata.failures == []
        # The marker itself still surfaces as a question.
        assert any(q.reason == "SOURCE_FAILED" for q in sweep.questions)


class TestBudgetAllocation:
    def test_per_source_budget_splits_across_llm_only(self) -> None:
        # Two LLM sources with default multiplier=1.0; one non-LLM
        # source with multiplier=0.0 (excluded from the pool).
        llm_a = FakeSource(name="llm-a", is_llm=True, findings=[])
        llm_b = FakeSource(name="llm-b", is_llm=True, findings=[])
        non_llm = FakeSource(name="pattern", is_llm=False, findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(
            wf.execute(
                path="src/",
                budget_usd=10.0,
                sources=[llm_a, llm_b, non_llm],
            )
        )
        # 10.00 * (1.0 / 2.0) = 5.00 to each LLM source.
        assert llm_a.received_budget == pytest.approx(5.0)
        assert llm_b.received_budget == pytest.approx(5.0)
        # Non-LLM gets 0.0 — it sums to a zero share of the pool.
        assert non_llm.received_budget == pytest.approx(0.0)

    def test_proportional_allocation_by_multiplier(self) -> None:
        # Mirrors the spec defaults: security-audit gets a 4x share,
        # dependency-check 0.5x, default 1.0x.
        heavy = FakeSource(name="security", is_llm=True, budget_multiplier=4.0, findings=[])
        light = FakeSource(name="deps", is_llm=True, budget_multiplier=0.5, findings=[])
        default = FakeSource(name="bug", is_llm=True, budget_multiplier=1.0, findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(
            wf.execute(path="src/", budget_usd=11.0, sources=[heavy, light, default]),
        )
        total = 4.0 + 0.5 + 1.0
        assert heavy.received_budget == pytest.approx(11.0 * 4.0 / total)
        assert light.received_budget == pytest.approx(11.0 * 0.5 / total)
        assert default.received_budget == pytest.approx(11.0 * 1.0 / total)

    def test_no_llm_sources_passes_full_budget(self) -> None:
        non_llm = FakeSource(name="pattern", is_llm=False, findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="src/", budget_usd=7.50, sources=[non_llm]))
        # With no positive-multiplier sources, the engine passes the
        # full budget through as a signal — non-LLM ignores it anyway.
        assert non_llm.received_budget == pytest.approx(7.50)

    def test_default_budget_is_ten_dollars(self) -> None:
        assert DEFAULT_BUDGET_USD == 10.00


class TestSpentUsdTracking:
    """Regression guard: real per-source API spend must reach both the
    ``SweepMetadata`` footer and the ``WorkflowResult`` cost_report.

    Before this guard, ``_build_sweep_result`` hardcoded
    ``spent_usd=0.0`` and every LLM source discarded its
    ``result.cost_report``, so a sweep that spent real money always
    reported ``$0.00``.
    """

    def test_engine_sums_source_spent_usd(self) -> None:
        # Two LLM sources accumulated spend during their fan-out; the
        # non-LLM source carries the default 0.0.
        a = FakeSource(name="a", is_llm=True, findings=[], spent_usd=1.50)
        b = FakeSource(name="b", is_llm=True, findings=[], spent_usd=2.25)
        pattern = FakeSource(name="pattern", is_llm=False, findings=[])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[a, b, pattern]))
        sweep: SweepResult = res.metadata["sweep"]
        assert sweep.metadata.spent_usd == pytest.approx(3.75)
        # The WorkflowResult cost_report mirrors the same total.
        assert res.cost_report.total_cost == pytest.approx(3.75)

    def test_zero_spend_reports_zero(self) -> None:
        # Pattern-only / --no-llm sweep: no source accrued cost.
        src = FakeSource(name="pattern", is_llm=False, findings=[])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        sweep: SweepResult = res.metadata["sweep"]
        assert sweep.metadata.spent_usd == pytest.approx(0.0)

    def test_llmsource_record_cost_accumulates(self) -> None:
        from types import SimpleNamespace

        from attune.workflows.discovery_sweep.llm_source_base import LLMSource

        source = LLMSource()
        source._record_cost(SimpleNamespace(cost_report=SimpleNamespace(total_cost=0.40)))
        source._record_cost(SimpleNamespace(cost_report=SimpleNamespace(total_cost=1.10)))
        assert source.spent_usd == pytest.approx(1.50)

    def test_record_cost_ignores_missing_or_null_cost_report(self) -> None:
        from types import SimpleNamespace

        from attune.workflows.discovery_sweep.llm_source_base import LLMSource

        source = LLMSource()
        source._record_cost(SimpleNamespace())  # no cost_report attribute
        source._record_cost(SimpleNamespace(cost_report=None))
        assert source.spent_usd == pytest.approx(0.0)


class TestPathExpansion:
    def test_non_glob_path_passed_through(self) -> None:
        src = FakeSource(name="s", findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="src/attune/", sources=[src]))
        assert src.received_paths == ["src/attune/"]

    def test_glob_pattern_expanded(self, tmp_path: object) -> None:
        # Build two files matching a glob, one not.
        from pathlib import Path as _P

        base = _P(str(tmp_path))
        (base / "a.py").write_text("x = 1\n", encoding="utf-8")
        (base / "b.py").write_text("x = 1\n", encoding="utf-8")
        (base / "c.txt").write_text("ignore\n", encoding="utf-8")

        src = FakeSource(name="s", findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path=str(base / "*.py"), sources=[src]))
        assert src.received_paths is not None
        # Sorted glob result. Only .py files matched.
        assert all(p.endswith(".py") for p in src.received_paths)
        assert len(src.received_paths) == 2

    def test_glob_with_no_matches_forwards_raw_glob_to_sources(self) -> None:
        """Unmatched glob → raw path forwarded so sources can emit a
        "no files matched" finding (see ``_expand_path`` docstring)."""
        src = FakeSource(name="s", is_llm=True, findings=[])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="nonexistent/**/*.zzz", sources=[src]))
        sweep: SweepResult = res.metadata["sweep"]
        assert src.received_paths == ["nonexistent/**/*.zzz"]
        assert sweep.queue == []


class TestSourceFiltering:
    def test_no_llm_filters_llm_sources(self) -> None:
        llm = FakeSource(name="llm", is_llm=True, findings=[_finding()])
        pat = FakeSource(name="pat", is_llm=False, findings=[])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[llm, pat], no_llm=True))
        sweep: SweepResult = res.metadata["sweep"]
        assert sweep.metadata.sources == ["pat"]
        # llm source never ran (no findings reached the queue).
        assert sweep.queue == []

    def test_no_sources_after_filter_errors(self) -> None:
        llm = FakeSource(name="llm", is_llm=True, findings=[])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[llm], no_llm=True))
        assert res.success is False
        assert "no sources to run" in (res.error or "")


class TestValidation:
    def test_missing_path_errors(self) -> None:
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(sources=[]))
        assert res.success is False
        assert "path argument is required" in (res.error or "")


class TestSourceNameFilter:
    """Phase 3 P3.5 — ``source`` kwarg narrows fan-out to one adapter."""

    def test_source_filter_runs_only_named_source(self) -> None:
        bug = FakeSource(name="bug-predict", is_llm=True, findings=[_finding()])
        sec = FakeSource(name="security-audit", is_llm=True, findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[bug, sec], source="bug-predict"))
        sweep: SweepResult = res.metadata["sweep"]
        assert sweep.metadata.sources == ["bug-predict"]

    def test_source_filter_unknown_name_errors(self) -> None:
        bug = FakeSource(name="bug-predict", is_llm=True, findings=[])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[bug], source="missing"))
        assert res.success is False
        assert "no sources to run" in (res.error or "")

    def test_source_and_no_llm_combine(self) -> None:
        """``no_llm`` applies first, then ``source`` filters survivors."""
        bug = FakeSource(name="bug-predict", is_llm=True, findings=[])
        pat = FakeSource(name="pattern-scan", is_llm=False, findings=[])
        wf = DiscoverySweepWorkflow()
        # no-LLM keeps only pat; source="bug-predict" then matches nothing.
        res = asyncio.run(
            wf.execute(
                path="src/",
                sources=[bug, pat],
                no_llm=True,
                source="bug-predict",
            )
        )
        assert res.success is False


class TestOutputFormatJson:
    """Phase 3 P3.1 — ``output_format='json'`` renders SweepResult as JSON."""

    def test_json_output_is_parseable_with_expected_top_level(self) -> None:
        import json as _json

        src = FakeSource(
            name="s",
            is_llm=False,
            findings=[_finding(severity="high", file="a.py", line=1)],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src], output_format="json"))
        payload = _json.loads(res.final_output)
        assert set(payload.keys()) == {"queue", "questions", "rejected", "metadata"}
        assert len(payload["queue"]) == 1
        assert payload["queue"][0]["severity"] == "high"
        assert payload["queue"][0]["file"] == "a.py"
        assert payload["metadata"]["sources"] == ["s"]

    def test_json_output_serializes_tuple_tags_as_array(self) -> None:
        import json as _json

        src = FakeSource(
            name="s",
            is_llm=False,
            findings=[
                _finding(
                    severity="medium",
                    file="b.py",
                    line=2,
                    tags=("cwe-95", "review-me"),
                )
            ],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src], output_format="json"))
        payload = _json.loads(res.final_output)
        assert payload["queue"][0]["tags"] == ["cwe-95", "review-me"]

    def test_markdown_is_the_default_output_format(self) -> None:
        src = FakeSource(name="s", is_llm=False, findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        assert "## Queue" in res.final_output
        assert not res.final_output.lstrip().startswith("{")


class TestVerboseFlag:
    """Phase 3 P3.3 — ``verbose=True`` includes rejected bucket in markdown."""

    def test_verbose_false_hides_rejected_details(self) -> None:
        # Severity below threshold (info) → routed to rejected.
        src = FakeSource(
            name="s",
            is_llm=False,
            findings=[_finding(severity="info", file="a.py", line=1)],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        assert "use --verbose to see" in res.final_output

    def test_verbose_true_shows_rejected_details(self) -> None:
        src = FakeSource(
            name="s",
            is_llm=False,
            findings=[_finding(severity="info", file="a.py", line=1)],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src], verbose=True))
        assert "## Rejected" in res.final_output
        assert "Rule:" in res.final_output


class TestSeverityColorBadges:
    """Phase 3.2 — ANSI severity badges when stdout is a TTY.

    ``NO_COLOR`` and ``FORCE_COLOR`` both follow no-color.org
    convention. Tests use ``monkeypatch`` on env so they're
    deterministic regardless of where they run (TTY-on local,
    TTY-off CI).
    """

    def test_no_color_env_forces_plain_brackets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        src = FakeSource(
            name="s",
            is_llm=False,
            findings=[_finding(severity="high", file="a.py", line=1)],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        # Plain bracket with no ANSI escape codes.
        assert "[high]" in res.final_output
        assert "\x1b[" not in res.final_output

    def test_force_color_injects_ansi_codes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        src = FakeSource(
            name="s",
            is_llm=False,
            findings=[_finding(severity="high", file="a.py", line=1)],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        # Red severity wrapped in ANSI codes.
        assert "\x1b[31m[high]\x1b[0m" in res.final_output

    def test_force_color_critical_is_bold_red(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Critical is bumped to bold-red (`\\x1b[1;31m`) to distinguish from high."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        src = FakeSource(
            name="s",
            is_llm=False,
            findings=[_finding(severity="critical", file="a.py", line=1)],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        assert "\x1b[1;31m[critical]\x1b[0m" in res.final_output

    def test_no_color_takes_precedence_over_force_color(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NO_COLOR wins (per no-color.org); FORCE_COLOR doesn't override it."""
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("FORCE_COLOR", "1")
        src = FakeSource(
            name="s",
            is_llm=False,
            findings=[_finding(severity="high", file="a.py", line=1)],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        assert "\x1b[" not in res.final_output

    def test_json_output_never_includes_ansi_codes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Even with FORCE_COLOR, the JSON path must stay clean."""
        monkeypatch.setenv("FORCE_COLOR", "1")
        src = FakeSource(
            name="s",
            is_llm=False,
            findings=[_finding(severity="high", file="a.py", line=1)],
        )
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src], output_format="json"))
        assert "\x1b[" not in res.final_output

    def test_unknown_severity_falls_back_to_plain_bracket(self) -> None:
        """Unknown severities skip the ANSI lookup miss and return plain brackets.

        ``_SEVERITY_ANSI`` only covers the five canonical levels. If a future
        source emits a custom severity string, ``_severity_badge`` must still
        produce a readable label rather than crashing or returning empty.
        """
        from attune.workflows.discovery_sweep.workflow import _severity_badge

        # colored=True + severity not in the ANSI map → plain bracket (no codes).
        assert _severity_badge("unknown", colored=True) == "[unknown]"
        # colored=False short-circuits before the lookup, also plain.
        assert _severity_badge("unknown", colored=False) == "[unknown]"
