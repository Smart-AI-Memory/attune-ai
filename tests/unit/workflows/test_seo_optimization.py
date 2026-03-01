"""Tests for SEOOptimizationWorkflow.

Covers initialization, stage skipping, file scanning, SEO analysis,
confidence scoring, and educational explanations.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from pathlib import Path

import pytest

from attune.models import ModelTier
from attune.workflows.seo_optimization import (
    SEOOptimizationConfig,
)


@pytest.mark.unit
class TestSEOOptimizationInit:
    """Verify class attributes and initialization."""

    def test_class_attributes(self, seo_optimization_workflow):
        wf = seo_optimization_workflow
        assert wf.name == "seo-optimization"
        assert wf.stages == ["scan", "analyze", "recommend", "implement"]
        assert wf.tier_map == {
            "scan": ModelTier.CHEAP,
            "analyze": ModelTier.CAPABLE,
            "recommend": ModelTier.PREMIUM,
            "implement": ModelTier.CAPABLE,
        }

    def test_default_state(self, seo_optimization_workflow):
        wf = seo_optimization_workflow
        assert wf._mode == "audit"
        assert wf._interactive is True
        assert wf._user_goal is None
        assert wf._scan_result is None
        assert wf._analyze_result is None
        assert wf._recommend_result is None


@pytest.mark.unit
class TestShouldSkipStage:
    """Tests for should_skip_stage() mode-based logic."""

    def test_audit_mode_skips_recommend(self, seo_optimization_workflow):
        seo_optimization_workflow._mode = "audit"
        skip, reason = seo_optimization_workflow.should_skip_stage("recommend", {})
        assert skip is True
        assert "Audit mode" in reason

    def test_audit_mode_skips_implement(self, seo_optimization_workflow):
        seo_optimization_workflow._mode = "audit"
        skip, reason = seo_optimization_workflow.should_skip_stage("implement", {})
        assert skip is True

    def test_suggest_mode_skips_implement(self, seo_optimization_workflow):
        seo_optimization_workflow._mode = "suggest"
        skip, reason = seo_optimization_workflow.should_skip_stage("implement", {})
        assert skip is True
        assert "suggest" in reason

    def test_fix_mode_runs_all_stages(self, seo_optimization_workflow):
        seo_optimization_workflow._mode = "fix"

        for stage in ["scan", "analyze", "recommend", "implement"]:
            skip, reason = seo_optimization_workflow.should_skip_stage(stage, {})
            assert skip is False, f"Stage {stage} should not be skipped in fix mode"

    def test_scan_and_analyze_never_skipped(self, seo_optimization_workflow):
        for mode in ["audit", "suggest", "fix"]:
            seo_optimization_workflow._mode = mode
            for stage in ["scan", "analyze"]:
                skip, _ = seo_optimization_workflow.should_skip_stage(stage, {})
                assert skip is False


@pytest.mark.unit
class TestScanFiles:
    """Tests for _scan_files()."""

    @pytest.mark.asyncio
    async def test_scans_markdown_files(self, seo_optimization_workflow, tmp_path):
        (tmp_path / "index.md").write_text("# Home")
        (tmp_path / "about.md").write_text("# About")
        (tmp_path / "style.css").write_text("body {}")

        config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=["test"],
        )

        result = await seo_optimization_workflow._scan_files(config)

        assert result["file_count"] == 2
        assert len(result["files"]) == 2
        assert result["site_url"] == "https://example.com"


@pytest.mark.unit
class TestAnalyzeSeo:
    """Tests for _analyze_seo()."""

    @pytest.mark.asyncio
    async def test_detects_missing_meta_description(self, seo_optimization_workflow, tmp_path):
        doc = tmp_path / "page.md"
        doc.write_text("# My Page\n\nSome content here.")

        config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=[],
        )
        scan_data = {"files": [str(doc)]}

        result = await seo_optimization_workflow._analyze_seo(config, scan_data)

        meta_issues = [i for i in result["issues"] if i["element"] == "meta_description"]
        assert len(meta_issues) == 1
        assert meta_issues[0]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_detects_multiple_h1(self, seo_optimization_workflow, tmp_path):
        doc = tmp_path / "page.md"
        doc.write_text("# First\n\n# Second\n\ndescription: test")

        config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=[],
        )
        scan_data = {"files": [str(doc)]}

        result = await seo_optimization_workflow._analyze_seo(config, scan_data)

        h1_issues = [i for i in result["issues"] if i["element"] == "h1_count"]
        assert len(h1_issues) == 1
        assert "Multiple H1" in h1_issues[0]["message"]

    @pytest.mark.asyncio
    async def test_handles_unreadable_files(self, seo_optimization_workflow):
        config = SEOOptimizationConfig(
            docs_path=Path("/tmp"),
            site_url="https://example.com",
            target_keywords=[],
        )
        scan_data = {"files": ["/nonexistent/file.md"]}

        result = await seo_optimization_workflow._analyze_seo(config, scan_data)

        assert result["total_issues"] == 0


@pytest.mark.unit
class TestConfidenceScoring:
    """Tests for _calculate_confidence()."""

    def test_critical_best_practice_high_confidence(self, seo_optimization_workflow):
        issue = {"element": "meta_description", "severity": "critical"}
        confidence = seo_optimization_workflow._calculate_confidence(issue)
        assert confidence == pytest.approx(0.6)  # 0.3 + 0.3

    def test_content_fix_reduces_confidence(self, seo_optimization_workflow):
        issue = {"element": "keyword_density", "severity": "warning"}
        confidence = seo_optimization_workflow._calculate_confidence(issue)
        assert confidence < 0.5

    def test_confidence_clamped_to_zero_one(self, seo_optimization_workflow):
        # Worst case: unknown element, no severity match
        issue = {"element": "unknown_thing", "severity": "info"}
        confidence = seo_optimization_workflow._calculate_confidence(issue)
        assert 0.0 <= confidence <= 1.0

    def test_technical_fix_adds_confidence(self, seo_optimization_workflow):
        issue = {"element": "sitemap", "severity": "critical"}
        confidence = seo_optimization_workflow._calculate_confidence(issue)
        # sitemap: best_practice(0.3) + critical(0.3) + technical(0.2) = 0.8
        assert confidence == pytest.approx(0.8)


@pytest.mark.unit
class TestEducationalExplanation:
    """Tests for _format_educational_explanation()."""

    def test_returns_required_keys(self, seo_optimization_workflow):
        issue = {"element": "meta_description", "severity": "critical"}
        explanation = seo_optimization_workflow._format_educational_explanation(
            issue, confidence=0.6
        )

        assert "impact" in explanation
        assert "time" in explanation
        assert "why" in explanation
        assert "confidence" in explanation

    def test_critical_has_high_impact(self, seo_optimization_workflow):
        issue = {"element": "h1_count", "severity": "critical"}
        explanation = seo_optimization_workflow._format_educational_explanation(
            issue, confidence=0.5
        )

        assert "High" in explanation["impact"]


@pytest.mark.unit
class TestGetReasoning:
    """Tests for _get_reasoning()."""

    def test_known_element_returns_specific_reasoning(self, seo_optimization_workflow):
        issue = {"element": "meta_description"}
        reasoning = seo_optimization_workflow._get_reasoning(issue)
        assert "click-through" in reasoning

    def test_unknown_element_returns_default(self, seo_optimization_workflow):
        issue = {"element": "something_new"}
        reasoning = seo_optimization_workflow._get_reasoning(issue)
        assert "search engines" in reasoning


@pytest.mark.unit
class TestGenerateRecommendations:
    """Tests for _generate_recommendations()."""

    @pytest.mark.asyncio
    async def test_high_confidence_goes_to_recommendations(
        self, seo_optimization_workflow, tmp_path
    ):
        config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=[],
        )
        analysis = {
            "issues": [
                {
                    "file": str(tmp_path / "test.md"),
                    "element": "sitemap",
                    "severity": "critical",
                    "message": "Missing sitemap",
                }
            ]
        }

        result = await seo_optimization_workflow._generate_recommendations(config, analysis)

        assert result["total_recommendations"] >= 1

    @pytest.mark.asyncio
    async def test_low_confidence_goes_to_clarification(self, seo_optimization_workflow, tmp_path):
        config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=[],
        )
        analysis = {
            "issues": [
                {
                    "file": str(tmp_path / "test.md"),
                    "element": "keyword_density",
                    "severity": "info",
                    "message": "Low keyword density",
                }
            ]
        }

        result = await seo_optimization_workflow._generate_recommendations(config, analysis)

        assert result["needs_clarification"] >= 1


@pytest.mark.unit
class TestSEOOptimizationConfig:
    """Tests for the SEOOptimizationConfig dataclass."""

    def test_defaults(self):
        config = SEOOptimizationConfig(
            docs_path=Path("docs"),
            site_url="https://example.com",
            target_keywords=["ai"],
        )
        assert config.mode == "audit"
        assert config.interactive is True
