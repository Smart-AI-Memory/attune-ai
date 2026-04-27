# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Coverage batch 18: workflows/config, output, output_schemas, migration, tier_tracking."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

# === Module: workflows/output_schemas ===


class TestWorkflowOutputSchema:
    def test_schema_is_dict(self):
        from attune.workflows.output_schemas import WORKFLOW_OUTPUT_SCHEMA

        assert isinstance(WORKFLOW_OUTPUT_SCHEMA, dict)

    def test_schema_type_is_json_schema(self):
        from attune.workflows.output_schemas import WORKFLOW_OUTPUT_SCHEMA

        assert WORKFLOW_OUTPUT_SCHEMA["type"] == "json_schema"

    def test_schema_has_required_properties(self):
        from attune.workflows.output_schemas import WORKFLOW_OUTPUT_SCHEMA

        props = WORKFLOW_OUTPUT_SCHEMA["schema"]["properties"]
        assert "summary" in props
        assert "findings" in props
        assert "suggestions" in props

    def test_schema_required_fields(self):
        from attune.workflows.output_schemas import WORKFLOW_OUTPUT_SCHEMA

        required = WORKFLOW_OUTPUT_SCHEMA["schema"]["required"]
        assert set(required) == {"summary", "findings", "suggestions"}


# === Module: workflows/config ===


class TestModelConfig:
    def test_basic_construction(self):
        from attune.workflows.config import ModelConfig

        mc = ModelConfig(
            name="claude-haiku-4-5",
            provider="anthropic",
            tier="cheap",
        )
        assert mc.name == "claude-haiku-4-5"
        assert mc.provider == "anthropic"
        assert mc.tier == "cheap"
        assert mc.supports_tools is True

    def test_from_model_info(self):
        from attune.models import ModelInfo
        from attune.workflows.config import ModelConfig

        info = ModelInfo(
            id="claude-haiku-test",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=5.0,
            max_tokens=8192,
            supports_vision=False,
            supports_tools=True,
        )
        mc = ModelConfig.from_model_info(info)
        assert mc.name == "claude-haiku-test"
        assert mc.input_cost_per_million == 1.0
        assert mc.supports_vision is False


class TestWorkflowConfig:
    def test_default_construction(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig()
        assert cfg.default_provider == "anthropic"
        assert cfg.workflow_providers == {}
        assert cfg.compliance_mode == "standard"
        assert cfg.audit_level == "standard"

    def test_get_provider_for_workflow_default(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig()
        assert cfg.get_provider_for_workflow("morning") == "anthropic"

    def test_get_provider_for_workflow_override(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(workflow_providers={"research": "openai"})
        assert cfg.get_provider_for_workflow("research") == "openai"
        assert cfg.get_provider_for_workflow("other") == "anthropic"

    def test_get_model_for_tier_custom(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(custom_models={"anthropic": {"cheap": "claude-haiku-test"}})
        assert cfg.get_model_for_tier("anthropic", "cheap") == "claude-haiku-test"

    def test_get_model_for_tier_env_override(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(custom_models={"env": {"cheap": "overridden-model"}})
        assert cfg.get_model_for_tier("anthropic", "cheap") == "overridden-model"

    def test_get_model_for_tier_no_override(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig()
        assert cfg.get_model_for_tier("anthropic", "cheap") is None

    def test_is_hipaa_mode_false_by_default(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig()
        assert cfg.is_hipaa_mode() is False

    def test_is_hipaa_mode_true_when_set(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(compliance_mode="hipaa")
        assert cfg.is_hipaa_mode() is True

    def test_is_pii_scrubbing_disabled_by_default(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig()
        assert cfg.is_pii_scrubbing_enabled() is False

    def test_is_pii_scrubbing_enabled_in_hipaa(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(compliance_mode="hipaa")
        assert cfg.is_pii_scrubbing_enabled() is True

    def test_is_pii_scrubbing_explicit_override(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(compliance_mode="hipaa", pii_scrubbing_enabled=False)
        assert cfg.is_pii_scrubbing_enabled() is False

    def test_is_workflow_enabled_disabled(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(disabled_workflows=["test-gen"])
        assert cfg.is_workflow_enabled("test-gen") is False

    def test_is_workflow_enabled_explicitly(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(enabled_workflows=["custom-wf"])
        assert cfg.is_workflow_enabled("custom-wf") is True

    def test_is_workflow_enabled_none_for_unknown(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig()
        assert cfg.is_workflow_enabled("unknown-wf") is None

    def test_get_effective_audit_level_standard(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig()
        assert cfg.get_effective_audit_level() == "standard"

    def test_get_effective_audit_level_hipaa(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(compliance_mode="hipaa")
        assert cfg.get_effective_audit_level() == "hipaa"

    def test_get_xml_config_merges_defaults_and_overrides(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(
            xml_prompt_defaults={"enabled": True, "schema_version": "1.0"},
            workflow_xml_configs={"security-audit": {"enforce_response_xml": True}},
        )
        config = cfg.get_xml_config_for_workflow("security-audit")
        assert config["enabled"] is True
        assert config["enforce_response_xml"] is True

    def test_is_xml_enabled_defaults_true(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig()
        assert cfg.is_xml_enabled_for_workflow("any-workflow") is True

    def test_get_pricing_none_for_unknown(self):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig()
        assert cfg.get_pricing("unknown-model") is None

    def test_load_returns_default_when_no_file(self, tmp_path, monkeypatch):
        from attune.workflows.config import WorkflowConfig

        monkeypatch.chdir(tmp_path)
        cfg = WorkflowConfig.load()
        assert cfg.default_provider == "anthropic"

    def test_load_from_json_file(self, tmp_path, monkeypatch):
        from attune.workflows.config import WorkflowConfig

        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".attune"
        config_dir.mkdir()
        config_file = config_dir / "workflows.json"
        config_file.write_text(json.dumps({"default_provider": "openai"}))
        cfg = WorkflowConfig.load(config_file)
        assert cfg.default_provider == "openai"

    def test_save_to_json(self, tmp_path):
        from attune.workflows.config import WorkflowConfig

        cfg = WorkflowConfig(default_provider="anthropic")
        out_path = tmp_path / "out.json"
        cfg.save(str(out_path))
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert data["default_provider"] == "anthropic"


class TestGetModel:
    def test_returns_model_string(self):
        from attune.workflows.config import get_model

        result = get_model("anthropic", "cheap")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_custom_model_when_configured(self):
        from attune.workflows.config import WorkflowConfig, get_model

        cfg = WorkflowConfig(custom_models={"anthropic": {"cheap": "my-custom-haiku"}})
        result = get_model("anthropic", "cheap", config=cfg)
        assert result == "my-custom-haiku"

    def test_fallback_for_unknown_provider(self):
        from attune.workflows.config import get_model

        result = get_model("unknown-provider", "cheap")
        assert isinstance(result, str)


# === Module: workflows/output ===


class TestFinding:
    def test_basic_construction(self):
        from attune.workflows.output import Finding

        f = Finding(severity="high", file="src/app.py", line=42, message="null deref")
        assert f.severity == "high"
        assert f.file == "src/app.py"
        assert f.line == 42

    def test_location_with_line(self):
        from attune.workflows.output import Finding

        f = Finding(severity="medium", file="src/app.py", line=10)
        assert f.location == "src/app.py:10"

    def test_location_without_line(self):
        from attune.workflows.output import Finding

        f = Finding(severity="low", file="src/app.py")
        assert f.location == "src/app.py"

    def test_severity_icon_high(self):
        from attune.workflows.output import Finding

        f = Finding(severity="high", file="f.py")
        assert "x" in f.severity_icon.lower() or "X" in f.severity_icon

    def test_severity_icon_info(self):
        from attune.workflows.output import Finding

        f = Finding(severity="info", file="f.py")
        assert "o" in f.severity_icon.lower()


class TestWorkflowReport:
    def test_basic_construction(self):
        from attune.workflows.output import WorkflowReport

        report = WorkflowReport(title="Test Report", summary="all good", score=90)
        assert report.title == "Test Report"
        assert report.score == 90
        assert report.sections == []

    def test_add_section(self):
        from attune.workflows.output import WorkflowReport

        report = WorkflowReport(title="Test")
        report.add_section("Section 1", "content here")
        assert len(report.sections) == 1
        assert report.sections[0].title == "Section 1"

    def test_render_plain(self):
        from attune.workflows.output import WorkflowReport

        report = WorkflowReport(title="My Report", summary="summary", score=75)
        report.add_section("Details", "some details")
        text = report.render(use_rich=False)
        assert "MY REPORT" in text
        assert "75" in text
        assert "Details".upper() in text

    def test_render_plain_with_dict_section(self):
        from attune.workflows.output import WorkflowReport

        report = WorkflowReport(title="Report")
        report.add_section("Stats", {"key": "value", "count": 5})
        text = report.render(use_rich=False)
        assert "key: value" in text

    def test_render_plain_with_findings(self):
        from attune.workflows.output import Finding, WorkflowReport

        report = WorkflowReport(title="Report")
        findings = [Finding(severity="high", file="app.py", line=1, message="bad")]
        report.add_section("Findings", findings)
        text = report.render(use_rich=False)
        assert "HIGH" in text

    def test_render_plain_no_score(self):
        from attune.workflows.output import WorkflowReport

        report = WorkflowReport(title="No Score Report")
        text = report.render(use_rich=False)
        assert "No Score Report".upper() in text


class TestFindingsTable:
    def test_to_plain_empty(self):
        from attune.workflows.output import FindingsTable

        table = FindingsTable([])
        plain = table.to_plain()
        assert "No findings" in plain

    def test_to_plain_with_findings(self):
        from attune.workflows.output import Finding, FindingsTable

        findings = [
            Finding(severity="high", file="app.py", line=10, message="critical"),
            Finding(severity="low", file="util.py", message="minor"),
        ]
        table = FindingsTable(findings)
        plain = table.to_plain()
        assert "[HIGH]" in plain
        assert "[LOW]" in plain
        assert "app.py:10" in plain
        assert "critical" in plain


class TestMetricsPanel:
    def test_get_level_excellent(self):
        from attune.workflows.output import MetricsPanel

        assert MetricsPanel.get_level(90) == "excellent"

    def test_get_level_good(self):
        from attune.workflows.output import MetricsPanel

        assert MetricsPanel.get_level(75) == "good"

    def test_get_level_needs_work(self):
        from attune.workflows.output import MetricsPanel

        assert MetricsPanel.get_level(60) == "needs work"

    def test_get_level_critical(self):
        from attune.workflows.output import MetricsPanel

        assert MetricsPanel.get_level(40) == "critical"

    def test_get_style_green_for_high(self):
        from attune.workflows.output import MetricsPanel

        assert MetricsPanel.get_style(90) == "green"

    def test_get_style_red_for_low(self):
        from attune.workflows.output import MetricsPanel

        assert MetricsPanel.get_style(30) == "red"

    def test_get_plain_icon_ok(self):
        from attune.workflows.output import MetricsPanel

        assert MetricsPanel.get_plain_icon(90) == "[OK]"

    def test_get_plain_icon_critical(self):
        from attune.workflows.output import MetricsPanel

        assert MetricsPanel.get_plain_icon(30) == "[XX]"

    def test_render_plain(self):
        from attune.workflows.output import MetricsPanel

        result = MetricsPanel.render_plain(75, label="Health")
        assert "Health" in result
        assert "75" in result
        assert "good" in result.lower()


class TestFormatWorkflowResult:
    def test_returns_workflow_report(self):
        from attune.workflows.output import WorkflowReport, format_workflow_result

        report = format_workflow_result(
            title="My Report",
            summary="done",
            score=80,
        )
        assert isinstance(report, WorkflowReport)
        assert report.score == 80

    def test_adds_findings_section(self):
        from attune.workflows.output import format_workflow_result

        findings = [{"severity": "high", "file": "app.py", "line": 1, "message": "error"}]
        report = format_workflow_result("Report", findings=findings)
        section_titles = [s.title for s in report.sections]
        assert "Findings" in section_titles

    def test_adds_recommendations_section(self):
        from attune.workflows.output import format_workflow_result

        report = format_workflow_result("Report", recommendations="Fix everything")
        titles = [s.title for s in report.sections]
        assert "Recommendations" in titles


# === Module: workflows/migration ===


class TestMigrationConstants:
    def test_workflow_aliases_is_dict(self):
        from attune.workflows.migration import WORKFLOW_ALIASES

        assert isinstance(WORKFLOW_ALIASES, dict)
        assert "pro-review" in WORKFLOW_ALIASES

    def test_pro_review_maps_to_code_review(self):
        from attune.workflows.migration import WORKFLOW_ALIASES

        new_name, kwargs = WORKFLOW_ALIASES["pro-review"]
        assert new_name == "code-review"

    def test_removed_workflow_has_none_name(self):
        from attune.workflows.migration import WORKFLOW_ALIASES

        new_name, kwargs = WORKFLOW_ALIASES["test5"]
        assert new_name is None
        assert kwargs.get("_removed") is True


class TestIsInteractive:
    def test_returns_false_in_ci(self):
        from attune.workflows.migration import is_interactive

        with patch.dict(os.environ, {"CI": "true"}):
            assert is_interactive() is False

    def test_returns_false_with_no_interactive_flag(self):
        from attune.workflows.migration import is_interactive

        with patch.dict(os.environ, {"ATTUNE_NO_INTERACTIVE": "1"}, clear=False):
            assert is_interactive() is False

    def test_returns_false_when_not_tty(self):
        from attune.workflows.migration import is_interactive

        env = dict.fromkeys(
            [
                "CI",
                "GITHUB_ACTIONS",
                "GITLAB_CI",
                "JENKINS_URL",
                "CIRCLECI",
                "TRAVIS",
                "ATTUNE_NO_INTERACTIVE",
            ],
            "",
        )
        with patch.dict(os.environ, env, clear=False):
            with patch("sys.stdin.isatty", return_value=False):
                assert is_interactive() is False


class TestGetCanonicalWorkflowName:
    def test_returns_new_name_for_alias(self):
        from attune.workflows.migration import get_canonical_workflow_name

        assert get_canonical_workflow_name("pro-review") == "code-review"

    def test_returns_same_name_for_unknown(self):
        from attune.workflows.migration import get_canonical_workflow_name

        assert get_canonical_workflow_name("unknown-wf") == "unknown-wf"

    def test_removed_workflow_returns_input(self):
        from attune.workflows.migration import get_canonical_workflow_name

        # "test5" maps to None → fallback returns input
        result = get_canonical_workflow_name("test5")
        assert result == "test5"


class TestListMigrations:
    def test_returns_list_of_dicts(self):
        from attune.workflows.migration import list_migrations

        migrations = list_migrations()
        assert isinstance(migrations, list)
        assert all(isinstance(m, dict) for m in migrations)

    def test_each_entry_has_required_keys(self):
        from attune.workflows.migration import list_migrations

        for m in list_migrations():
            assert "old_name" in m
            assert "new_name" in m
            assert "status" in m

    def test_consolidated_status_for_pro_review(self):
        from attune.workflows.migration import list_migrations

        migrations = {m["old_name"]: m for m in list_migrations()}
        assert migrations["pro-review"]["status"] == "consolidated"

    def test_removed_status_for_test5(self):
        from attune.workflows.migration import list_migrations

        migrations = {m["old_name"]: m for m in list_migrations()}
        assert migrations["test5"]["status"] == "removed"


class TestMigrationConfig:
    def test_default_construction(self):
        from attune.workflows.migration import MigrationConfig

        cfg = MigrationConfig()
        assert cfg.mode == "prompt"
        assert cfg.show_tips is True
        assert cfg.remembered_choices == {}

    def test_load_returns_default_when_no_file(self, tmp_path, monkeypatch):
        from attune.workflows.migration import MigrationConfig

        monkeypatch.chdir(tmp_path)
        cfg = MigrationConfig.load()
        assert cfg.mode == "prompt"

    def test_load_from_existing_file(self, tmp_path, monkeypatch):
        from attune.workflows.migration import MigrationConfig

        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".attune"
        config_dir.mkdir()
        (config_dir / "migration.json").write_text(json.dumps({"mode": "auto", "show_tips": False}))
        cfg = MigrationConfig.load()
        assert cfg.mode == "auto"
        assert cfg.show_tips is False

    def test_remember_choice_saves(self, tmp_path, monkeypatch):
        from attune.workflows.migration import MigrationConfig

        monkeypatch.chdir(tmp_path)
        cfg = MigrationConfig()
        cfg.remember_choice("pro-review", "new")
        assert cfg.remembered_choices["pro-review"] == "new"


class TestResolveWorkflowMigration:
    def test_unknown_workflow_returns_as_is(self):
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        name, kwargs, migrated = resolve_workflow_migration("custom-wf", MigrationConfig())
        assert name == "custom-wf"
        assert migrated is False

    def test_ci_env_migrates_silently(self):
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        cfg = MigrationConfig()
        with patch.dict(os.environ, {"CI": "true"}):
            name, kwargs, migrated = resolve_workflow_migration("pro-review", cfg)
        assert name == "code-review"
        assert migrated is True

    def test_removed_workflow_raises_system_exit(self):
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        cfg = MigrationConfig()
        with patch.dict(os.environ, {"CI": "true"}):
            with pytest.raises(SystemExit):
                resolve_workflow_migration("test5", cfg)

    def test_remembered_choice_new_is_used(self):
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        cfg = MigrationConfig(remembered_choices={"pro-review": "new"})
        name, kwargs, migrated = resolve_workflow_migration("pro-review", cfg)
        assert name == "code-review"

    def test_remembered_choice_legacy_is_used(self):
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        cfg = MigrationConfig(remembered_choices={"pro-review": "legacy"})
        name, kwargs, migrated = resolve_workflow_migration("pro-review", cfg)
        assert name == "pro-review"


# === Module: workflows/tier_tracking ===


class TestTierAttempt:
    def test_basic_construction(self):
        from attune.workflows.tier_tracking import TierAttempt

        attempt = TierAttempt(tier="CHEAP", attempt=1, success=True)
        assert attempt.tier == "CHEAP"
        assert attempt.success is True
        assert attempt.quality_gate_failed is None

    def test_failed_attempt(self):
        from attune.workflows.tier_tracking import TierAttempt

        attempt = TierAttempt(
            tier="CHEAP",
            attempt=1,
            success=False,
            quality_gate_failed="test_coverage",
        )
        assert attempt.quality_gate_failed == "test_coverage"


class TestWorkflowTierTracker:
    def test_initialization(self, tmp_path):
        from attune.workflows.tier_tracking import WorkflowTierTracker

        tracker = WorkflowTierTracker("morning", "Morning workflow", patterns_dir=tmp_path)
        assert tracker.workflow_name == "morning"
        assert tracker.tier_attempts == []
        assert tracker.workflow_id is not None

    def test_record_tier_attempt(self, tmp_path):
        from attune.workflows.tier_tracking import WorkflowTierTracker

        tracker = WorkflowTierTracker("learn", "Learn workflow", patterns_dir=tmp_path)
        tracker.record_tier_attempt("CHEAP", 1, success=False, quality_gate_failed="tests")
        tracker.record_tier_attempt("CAPABLE", 2, success=True)
        assert len(tracker.tier_attempts) == 2
        assert tracker.tier_attempts[0].success is False
        assert tracker.tier_attempts[1].success is True

    def test_show_recommendation_falls_back_to_cheap(self, tmp_path):
        from attune.workflows.tier_tracking import WorkflowTierTracker

        tracker = WorkflowTierTracker("morning", "Test", patterns_dir=tmp_path)
        with patch("attune.tier_recommender.TierRecommender", side_effect=ImportError("not found")):
            result = tracker.show_recommendation(show_ui=False)
        assert result == "CHEAP"

    def test_patterns_dir_is_created(self, tmp_path):
        from attune.workflows.tier_tracking import WorkflowTierTracker

        patterns_dir = tmp_path / "nested" / "patterns"
        WorkflowTierTracker("test", "Test", patterns_dir=patterns_dir)
        assert patterns_dir.exists()


class TestAutoRecommendTier:
    def test_returns_string(self, tmp_path):
        from attune.workflows.tier_tracking import auto_recommend_tier

        with patch("attune.workflows.tier_tracking.WorkflowTierTracker") as mock_tracker_cls:
            mock_tracker = MagicMock()
            mock_tracker.show_recommendation.return_value = "CAPABLE"
            mock_tracker_cls.return_value = mock_tracker
            result = auto_recommend_tier("morning", "Test workflow")
        assert result == "CAPABLE"
