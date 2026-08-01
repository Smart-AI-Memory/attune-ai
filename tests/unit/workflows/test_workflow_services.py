"""Tests for workflow capability services.

Covers all 7 service classes extracted from workflow mixins:
- ParsingService
- CoordinationService
- TierService
- CacheService
- PromptService
- CostService
- TelemetryService

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.caching import CachedResponse

# =============================================================================
# ParsingService Tests
# =============================================================================


class TestParsingService:
    """Tests for ParsingService."""

    def _make_service(self, xml_config=None):
        from attune.workflows.services.parsing_service import ParsingService

        return ParsingService(xml_config=xml_config)

    def test_init_default(self):
        svc = self._make_service()
        assert svc._xml_config == {}

    def test_init_with_config(self):
        svc = self._make_service({"enforce_response_xml": True})
        assert svc._xml_config["enforce_response_xml"] is True

    def test_parse_xml_response_not_enforced(self):
        svc = self._make_service()
        result = svc.parse_xml_response("some response")
        assert result["_parsed_response"] is None
        assert result["_raw"] == "some response"

    def test_parse_xml_response_enforced(self):
        svc = self._make_service({"enforce_response_xml": True})
        with patch("attune.prompts.XmlResponseParser") as mock_cls:
            mock_parser = MagicMock()
            mock_parsed = MagicMock()
            mock_parsed.summary = "test summary"
            mock_parsed.findings = []
            mock_parsed.checklist = []
            mock_parsed.success = True
            mock_parsed.errors = []
            mock_parser.parse.return_value = mock_parsed
            mock_cls.return_value = mock_parser

            result = svc.parse_xml_response("<response>test</response>")
            assert result["summary"] == "test summary"
            assert result["xml_parsed"] is True

    def test_extract_findings_regex_file_line_col_msg(self):
        svc = self._make_service()
        response = "Found issue at src/auth.py:42:5: SQL injection vulnerability"
        findings = svc.extract_findings(response, ["src/auth.py"])
        assert len(findings) == 1
        assert findings[0]["file"] == "src/auth.py"
        assert findings[0]["line"] == 42
        assert findings[0]["column"] == 5
        assert "SQL injection" in findings[0]["message"]

    def test_extract_findings_regex_file_line_msg(self):
        svc = self._make_service()
        response = "Problem at config.py:10: deprecated function call"
        findings = svc.extract_findings(response, ["config.py"])
        assert len(findings) == 1
        assert findings[0]["file"] == "config.py"
        assert findings[0]["line"] == 10

    def test_extract_findings_deduplicates(self):
        svc = self._make_service()
        response = (
            "src/auth.py:42:5: first issue\n"
            "src/auth.py:42:5: duplicate issue\n"
            "src/auth.py:50:1: different line"
        )
        findings = svc.extract_findings(response, ["src/auth.py"])
        assert len(findings) == 2

    def test_extract_findings_no_matches(self):
        svc = self._make_service()
        result = svc.extract_findings("no findings here", ["file.py"])
        assert result == []

    def test_extract_findings_with_xml_tags(self):
        svc = self._make_service()
        response = "<finding>test</finding>"
        with patch("attune.prompts.XmlResponseParser") as mock_cls:
            mock_parser = MagicMock()
            mock_parsed = MagicMock()
            mock_parsed.success = False
            mock_parsed.findings = []
            mock_parser.parse.return_value = mock_parsed
            mock_cls.return_value = mock_parser
            result = svc.extract_findings(response, ["file.py"])
            assert isinstance(result, list)

    def test_extract_findings_xml_success_enriches_from_real_parser(self):
        """A well-formed <findings> block is parsed by the REAL XmlResponseParser
        (no mock) and routed through _enrich_finding, covering the parsed.success
        branch plus location/category enrichment.
        """
        svc = self._make_service()
        response = (
            "<response>"
            "<summary>Reviewed the diff</summary>"
            "<findings>"
            '<item severity="high">'
            "<title>SQL Injection</title>"
            "<location>src/auth.py:42:5</location>"
            "<details>User input reaches the query unescaped</details>"
            "<fix>Use parameterized queries</fix>"
            "</item>"
            "</findings>"
            "</response>"
        )
        findings = svc.extract_findings(response, ["src/auth.py"])
        assert len(findings) == 1
        finding = findings[0]
        assert finding["file"] == "src/auth.py"
        assert finding["line"] == 42
        assert finding["column"] == 5
        assert finding["severity"] == "high"
        assert finding["category"] == "security"
        assert finding["message"] == "SQL Injection"
        assert finding["details"] == "User input reaches the query unescaped"
        assert finding["recommendation"] == "Use parameterized queries"

    def test_extract_findings_paren_line_with_column(self):
        """'(line N, column M)' regex branch: match has 3 groups and the
        column group is present + digits -> column parsed, message empty.
        """
        svc = self._make_service()
        response = "See file.py (line 42, column 5) for the issue"
        findings = svc.extract_findings(response, ["file.py"])
        assert len(findings) == 1
        assert findings[0]["file"] == "file.py"
        assert findings[0]["line"] == 42
        assert findings[0]["column"] == 5
        assert findings[0]["message"] == ""

    def test_extract_findings_paren_line_without_column(self):
        """'(line N)' regex branch: match has 3 groups but the optional column
        group did not participate -> falls to the else branch (column=1, no message).
        """
        svc = self._make_service()
        response = "See file.py (line 42) for the issue"
        findings = svc.extract_findings(response, ["file.py"])
        assert len(findings) == 1
        assert findings[0]["file"] == "file.py"
        assert findings[0]["line"] == 42
        assert findings[0]["column"] == 1
        assert findings[0]["message"] == ""

    def test_parse_location_empty(self):
        svc = self._make_service()
        file, line, col = svc.parse_location("", ["fallback.py"])
        assert file == "fallback.py"
        assert line == 1
        assert col == 1

    def test_parse_location_empty_no_files(self):
        svc = self._make_service()
        file, line, col = svc.parse_location("", [])
        assert file == ""

    def test_parse_location_file_line_col(self):
        svc = self._make_service()
        file, line, col = svc.parse_location("src/main.py:42:5", [])
        assert file == "src/main.py"
        assert line == 42
        assert col == 5

    def test_parse_location_file_line_only(self):
        svc = self._make_service()
        file, line, col = svc.parse_location("src/main.py:42", [])
        assert file == "src/main.py"
        assert line == 42
        assert col == 1

    def test_parse_location_line_in_file(self):
        svc = self._make_service()
        file, line, col = svc.parse_location("line 55 in utils.py", [])
        assert file == "utils.py"
        assert line == 55

    def test_parse_location_file_line_keyword(self):
        svc = self._make_service()
        file, line, col = svc.parse_location("utils.py line 55", [])
        assert file == "utils.py"
        assert line == 55

    def test_parse_location_just_line_number(self):
        svc = self._make_service()
        file, line, col = svc.parse_location("line 99", ["fallback.py"])
        assert file == "fallback.py"
        assert line == 99

    def test_parse_location_unrecognized(self):
        svc = self._make_service()
        file, line, col = svc.parse_location("somewhere unknown", ["fallback.py"])
        assert file == "fallback.py"
        assert line == 1

    def test_infer_severity_critical(self):
        assert self._make_service().infer_severity("Remote Code Execution found") == "critical"

    def test_infer_severity_high(self):
        assert self._make_service().infer_severity("Unsafe password storage") == "high"

    def test_infer_severity_medium(self):
        assert self._make_service().infer_severity("Deprecated API warning") == "medium"

    def test_infer_severity_low(self):
        assert self._make_service().infer_severity("Minor typo found") == "low"

    def test_infer_severity_info(self):
        assert self._make_service().infer_severity("Normal operation") == "info"

    def test_infer_category_security(self):
        assert self._make_service().infer_category("XSS vulnerability found") == "security"

    def test_infer_category_performance(self):
        assert self._make_service().infer_category("Memory leak detected") == "performance"

    def test_infer_category_maintainability(self):
        assert (
            self._make_service().infer_category("Complex function needs refactor")
            == "maintainability"
        )

    def test_infer_category_style(self):
        assert self._make_service().infer_category("Lint formatting issue") == "style"

    def test_infer_category_correctness(self):
        assert self._make_service().infer_category("Return value incorrect") == "correctness"


# =============================================================================
# PromptService Tests
# =============================================================================


class TestPromptService:
    """Tests for PromptService."""

    def _make_service(self, xml_config=None):
        from attune.workflows.services.prompt_service import PromptService

        return PromptService("test-workflow", xml_config=xml_config)

    def test_init_default(self):
        svc = self._make_service()
        assert svc._workflow_name == "test-workflow"
        assert svc.xml_enabled is True

    def test_xml_explicitly_disabled(self):
        svc = self._make_service({"enabled": False})
        assert svc.xml_enabled is False

    def test_xml_enabled_true(self):
        svc = self._make_service({"enabled": True})
        assert svc.xml_enabled is True

    def test_xml_config_property(self):
        cfg = {"enabled": True, "template_name": "test"}
        svc = self._make_service(cfg)
        assert svc.xml_config == cfg

    def test_build_cached_system_prompt_minimal(self):
        svc = self._make_service()
        prompt = svc.build_cached_system_prompt("expert reviewer")
        assert "You are a expert reviewer." in prompt
        assert "# Instructions" in prompt

    def test_build_cached_system_prompt_with_guidelines(self):
        svc = self._make_service()
        prompt = svc.build_cached_system_prompt(
            "reviewer",
            guidelines=["Check for bugs", "Review style"],
        )
        assert "# Guidelines" in prompt
        assert "1. Check for bugs" in prompt
        assert "2. Review style" in prompt

    def test_build_cached_system_prompt_with_documentation(self):
        svc = self._make_service()
        prompt = svc.build_cached_system_prompt(
            "reviewer",
            documentation="Reference: PEP 8 style guide",
        )
        assert "# Reference Documentation" in prompt
        assert "PEP 8" in prompt

    def test_build_cached_system_prompt_with_examples(self):
        svc = self._make_service()
        prompt = svc.build_cached_system_prompt(
            "reviewer",
            examples=[{"input": "bad code", "output": "fixed code"}],
        )
        assert "# Examples" in prompt
        assert "Example 1:" in prompt
        assert "bad code" in prompt

    def test_render_plain(self):
        svc = self._make_service()
        result = svc.render_plain(
            role="security analyst",
            goal="Find vulnerabilities",
            instructions=["Check SQL injection", "Check XSS"],
            constraints=["Focus on user input"],
            input_type="code",
            input_payload="def login(): pass",
        )
        assert "security analyst" in result
        assert "Find vulnerabilities" in result
        assert "1. Check SQL injection" in result
        assert "- Focus on user input" in result
        assert "Input (code):" in result

    def test_render_plain_no_instructions(self):
        svc = self._make_service()
        result = svc.render_plain(
            role="analyst",
            goal="Review",
            instructions=[],
            constraints=[],
            input_type="code",
            input_payload="",
        )
        assert "Instructions:" not in result

    def test_render_xml_falls_back_to_plain(self):
        svc = self._make_service()  # xml not enabled
        result = svc.render_xml(
            role="reviewer",
            goal="Review code",
            instructions=["Check style"],
            constraints=["Be thorough"],
            input_type="code",
            input_payload="print('hello')",
        )
        assert "reviewer" in result
        assert "Review code" in result

    def test_render_xml_enabled(self):
        svc = self._make_service({"enabled": True})
        with patch("attune.prompts.get_template") as mock_get:
            mock_template = MagicMock()
            mock_template.render.return_value = "<xml>rendered</xml>"
            mock_get.return_value = mock_template
            result = svc.render_xml(
                role="reviewer",
                goal="Review",
                instructions=["Check"],
                constraints=["Be careful"],
                input_type="code",
                input_payload="code",
            )
            assert result == "<xml>rendered</xml>"

    def test_render_xml_no_template_found(self):
        svc = self._make_service({"enabled": True, "schema_version": "2.0"})
        with patch("attune.prompts.get_template", return_value=None):
            with patch("attune.prompts.XmlPromptTemplate") as mock_cls:
                mock_template = MagicMock()
                mock_template.render.return_value = "<xml>fallback</xml>"
                mock_cls.return_value = mock_template
                result = svc.render_xml(
                    role="r",
                    goal="g",
                    instructions=["i"],
                    constraints=["c"],
                    input_type="code",
                    input_payload="p",
                )
                assert result == "<xml>fallback</xml>"
                mock_cls.assert_called_once_with(
                    name="test-workflow",
                    schema_version="2.0",
                )


# =============================================================================
# CoordinationService Tests
# =============================================================================


class TestCoordinationService:
    """Tests for CoordinationService."""

    def _make_service(self, **kwargs):
        from attune.workflows.services.coordination_service import CoordinationService

        return CoordinationService("test-workflow", **kwargs)

    def test_init_defaults(self):
        svc = self._make_service()
        assert svc._workflow_name == "test-workflow"
        assert svc._enable_heartbeat is False
        assert svc._enable_coordination is False

    def test_heartbeat_disabled(self):
        svc = self._make_service(enable_heartbeat=False)
        assert svc.get_heartbeat_coordinator() is None

    def test_heartbeat_import_failure(self):
        svc = self._make_service(enable_heartbeat=True)
        with (
            patch(
                "attune.workflows.services.coordination_service.HeartbeatCoordinator",
                side_effect=ImportError("not available"),
                create=True,
            ),
            patch.dict(
                "sys.modules",
                {
                    "attune.telemetry": MagicMock(
                        HeartbeatCoordinator=MagicMock(side_effect=ImportError("not available")),
                    ),
                },
            ),
        ):
            result = svc.get_heartbeat_coordinator()
            # Should gracefully degrade
            assert svc._enable_heartbeat is False or result is None

    def test_send_signal_coordination_disabled(self):
        svc = self._make_service(enable_coordination=False)
        result = svc.send_signal("task_complete")
        assert result == ""

    def test_wait_for_signal_coordination_disabled(self):
        svc = self._make_service(enable_coordination=False)
        result = svc.wait_for_signal("task_complete")
        assert result is None

    def test_check_signal_coordination_disabled(self):
        svc = self._make_service(enable_coordination=False)
        result = svc.check_signal("task_complete")
        assert result is None

    def test_send_signal_with_mock_coordinator(self):
        svc = self._make_service(enable_coordination=True)
        mock_signals = MagicMock()
        mock_signals.signal.return_value = "signal-123"
        svc._coordination_signals = mock_signals
        result = svc.send_signal(
            "task_complete",
            target_agent="agent-2",
            payload={"status": "done"},
        )
        assert result == "signal-123"

    def test_send_signal_exception_returns_empty(self):
        svc = self._make_service(enable_coordination=True)
        mock_signals = MagicMock()
        mock_signals.signal.side_effect = RuntimeError("Redis down")
        svc._coordination_signals = mock_signals
        result = svc.send_signal("error")
        assert result == ""

    def test_wait_for_signal_with_mock_coordinator(self):
        svc = self._make_service(enable_coordination=True)
        mock_signals = MagicMock()
        mock_signal = MagicMock()
        mock_signals.wait_for_signal.return_value = mock_signal
        svc._coordination_signals = mock_signals
        result = svc.wait_for_signal("ready", source_agent="agent-1", timeout=5.0)
        assert result == mock_signal

    def test_wait_for_signal_exception_returns_none(self):
        svc = self._make_service(enable_coordination=True)
        mock_signals = MagicMock()
        mock_signals.wait_for_signal.side_effect = RuntimeError("timeout")
        svc._coordination_signals = mock_signals
        result = svc.wait_for_signal("ready")
        assert result is None

    def test_check_signal_with_mock_coordinator(self):
        svc = self._make_service(enable_coordination=True)
        mock_signals = MagicMock()
        mock_signal_obj = MagicMock()
        mock_signals.check_signal.return_value = mock_signal_obj
        svc._coordination_signals = mock_signals
        result = svc.check_signal("ready", consume=False)
        assert result == mock_signal_obj
        mock_signals.check_signal.assert_called_once_with(
            signal_type="ready",
            source_agent=None,
            consume=False,
        )

    def test_check_signal_exception_returns_none(self):
        svc = self._make_service(enable_coordination=True)
        mock_signals = MagicMock()
        mock_signals.check_signal.side_effect = RuntimeError("error")
        svc._coordination_signals = mock_signals
        result = svc.check_signal("ready")
        assert result is None

    def test_get_coordination_signals_import_failure(self):
        svc = self._make_service(enable_coordination=True)
        with patch.dict("sys.modules", {"attune.telemetry": None}):
            result = svc._get_coordination_signals()
            # Should gracefully degrade
            assert result is None or svc._enable_coordination is False


# =============================================================================
# TierService Tests
# =============================================================================


class TestTierService:
    """Tests for TierService."""

    def _make_service(self, **kwargs):
        from attune.models import ModelTier
        from attune.workflows.services.tier_service import TierService

        defaults = {
            "workflow_name": "test-workflow",
            "stages": ["analyze", "report"],
            "tier_map": {"analyze": ModelTier.CAPABLE, "report": ModelTier.CHEAP},
        }
        defaults.update(kwargs)
        return TierService(**defaults)

    def test_get_tier_static(self):

        svc = self._make_service()
        tier = svc.get_tier("analyze")
        # Returns the ModelTier from tier_map
        assert tier.value == "capable"

    def test_get_tier_static_fallback(self):
        svc = self._make_service()
        tier = svc.get_tier("unknown_stage")
        assert tier.value == "capable"  # default

    def test_get_static_tier(self):

        svc = self._make_service()
        tier = svc.get_static_tier("report")
        assert tier.value == "cheap"

    def test_get_static_tier_fallback(self):
        svc = self._make_service()
        tier = svc.get_static_tier("nonexistent")
        assert tier.value == "capable"

    def test_get_tier_with_routing_strategy(self):
        from attune.models import ModelTier

        mock_strategy = MagicMock()
        mock_strategy.route.return_value = ModelTier.PREMIUM
        svc = self._make_service(routing_strategy=mock_strategy)
        tier = svc.get_tier("analyze", {"data": "test"})
        assert tier.value == "premium"

    def test_assess_complexity_simple(self):
        from attune.models import ModelTier

        svc = self._make_service(
            stages=["s1"],
            tier_map={"s1": ModelTier.CHEAP},
        )
        assert svc._assess_complexity({}) == "simple"

    def test_assess_complexity_moderate(self):
        from attune.models import ModelTier

        svc = self._make_service(
            stages=["s1", "s2", "s3"],
            tier_map={"s1": ModelTier.CHEAP, "s2": ModelTier.CAPABLE, "s3": ModelTier.PREMIUM},
        )
        assert svc._assess_complexity({}) == "moderate"

    def test_assess_complexity_complex(self):
        from attune.models import ModelTier

        svc = self._make_service(
            stages=["s1", "s2", "s3", "s4", "s5"],
            tier_map={
                "s1": ModelTier.PREMIUM,
                "s2": ModelTier.PREMIUM,
                "s3": ModelTier.CAPABLE,
                "s4": ModelTier.CHEAP,
                "s5": ModelTier.CHEAP,
            },
        )
        assert svc._assess_complexity({}) == "complex"

    def test_estimate_input_tokens(self):
        svc = self._make_service()
        tokens = svc._estimate_input_tokens({"key": "value"})
        assert tokens > 0

    def test_estimate_input_tokens_error(self):
        svc = self._make_service()
        # An object that can't be serialized
        tokens = svc._estimate_input_tokens({"circular": float("inf")})
        # json.dumps handles inf by default in some configs, but the method should still work
        assert isinstance(tokens, int)

    def test_adaptive_upgrade_disabled(self):

        svc = self._make_service(enable_adaptive=False)
        tier = svc.get_tier("analyze")
        assert tier.value == "capable"

    def test_adaptive_upgrade_router_unavailable(self):
        from attune.models import ModelTier

        svc = self._make_service(enable_adaptive=True)
        # Force router to fail
        with patch.dict("sys.modules", {"attune.telemetry": None}):
            svc._adaptive_router = None
            svc._enable_adaptive = True
            result = svc._check_adaptive_upgrade("analyze", ModelTier.CAPABLE)
            assert result.value == "capable"

    def test_adaptive_upgrade_recommended(self):
        from attune.workflows.compat import ModelTier

        svc = self._make_service(enable_adaptive=True)
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (True, "low quality scores")
        svc._adaptive_router = mock_router
        result = svc._check_adaptive_upgrade("analyze", ModelTier.CHEAP)
        assert result.value == "capable"

    def test_adaptive_upgrade_from_capable_to_premium(self):
        from attune.workflows.compat import ModelTier

        svc = self._make_service(enable_adaptive=True)
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (True, "needs premium")
        svc._adaptive_router = mock_router
        result = svc._check_adaptive_upgrade("analyze", ModelTier.CAPABLE)
        assert result.value == "premium"

    def test_adaptive_upgrade_premium_stays_premium(self):
        from attune.workflows.compat import ModelTier

        svc = self._make_service(enable_adaptive=True)
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (True, "already max")
        svc._adaptive_router = mock_router
        result = svc._check_adaptive_upgrade("analyze", ModelTier.PREMIUM)
        assert result.value == "premium"

    def test_adaptive_no_upgrade(self):
        from attune.workflows.compat import ModelTier

        svc = self._make_service(enable_adaptive=True)
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (False, "")
        svc._adaptive_router = mock_router
        result = svc._check_adaptive_upgrade("analyze", ModelTier.CHEAP)
        assert result.value == "cheap"


# =============================================================================
# CacheService Tests
# =============================================================================


class TestCacheService:
    """Tests for CacheService (no-op — Anthropic handles caching server-side)."""

    def _make_service(self, **kwargs):
        from attune.workflows.services.cache_service import CacheService

        defaults = {"workflow_name": "test-workflow"}
        defaults.update(kwargs)
        return CacheService(**defaults)

    def test_always_disabled(self):
        svc = self._make_service()
        assert svc.enabled is False
        assert svc._cache is None

    def test_lookup_returns_none(self):
        svc = self._make_service()
        assert svc.lookup("stage1", "sys", "user", "model") is None

    def test_store_returns_false(self):
        svc = self._make_service()
        result = svc.store("s", "sys", "usr", "m", CachedResponse("r", 1, 1))
        assert result is False

    def test_cache_type_is_anthropic(self):
        svc = self._make_service()
        assert svc.get_cache_type() == "anthropic"

    def test_stats_are_empty(self):
        svc = self._make_service()
        assert svc.get_stats() == {"hits": 0, "misses": 0, "hit_rate": 0.0}

    def test_setup_is_noop(self):
        svc = self._make_service()
        svc.setup()
        assert svc._cache is None

    def test_make_key_with_system(self):
        svc = self._make_service()
        assert svc.make_key("sys", "usr") == "sys\n\nusr"

    def test_make_key_without_system(self):
        svc = self._make_service()
        assert svc.make_key("", "usr") == "usr"


# =============================================================================
# CostService Tests
# =============================================================================


class TestCostService:
    """Tests for CostService."""

    def _make_service(self, cache_stats_fn=None):
        from attune.workflows.services.cost_service import CostService

        return CostService(cache_stats_fn=cache_stats_fn)

    def test_init(self):
        svc = self._make_service()
        assert svc._cache_stats_fn is None

    def test_calculate_cost(self):
        from attune.models import ModelTier

        svc = self._make_service()
        cost = svc.calculate_cost(ModelTier.CAPABLE, input_tokens=1000, output_tokens=500)
        assert isinstance(cost, float)
        assert cost > 0

    def test_calculate_baseline_cost(self):
        svc = self._make_service()
        cost = svc.calculate_baseline_cost(input_tokens=1000, output_tokens=500)
        assert isinstance(cost, float)
        assert cost > 0

    def test_baseline_cost_higher_than_cheap(self):
        from attune.models import ModelTier

        svc = self._make_service()
        cheap_cost = svc.calculate_cost(ModelTier.CHEAP, 1000, 500)
        baseline = svc.calculate_baseline_cost(1000, 500)
        assert baseline >= cheap_cost

    def test_generate_report_empty(self):
        svc = self._make_service()
        report = svc.generate_report([])
        assert report.total_cost == 0.0
        assert report.savings_percent == 0.0

    def test_generate_report_with_stages(self):
        from attune.models import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        svc = self._make_service()
        stages = [
            WorkflowStage(
                name="analyze",
                tier=ModelTier.CAPABLE,
                description="Analysis",
                input_tokens=500,
                output_tokens=200,
                cost=0.01,
            ),
            WorkflowStage(
                name="report",
                tier=ModelTier.CHEAP,
                description="Reporting",
                input_tokens=300,
                output_tokens=100,
                cost=0.002,
            ),
        ]
        report = svc.generate_report(stages)
        assert report.total_cost == pytest.approx(0.012)
        assert "analyze" in report.by_stage
        assert "report" in report.by_stage

    def test_generate_report_skipped_stages(self):
        from attune.models import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        svc = self._make_service()
        stages = [
            WorkflowStage(
                name="s1",
                tier=ModelTier.CAPABLE,
                description="d",
                input_tokens=500,
                output_tokens=200,
                cost=0.01,
            ),
            WorkflowStage(
                name="s2",
                tier=ModelTier.CHEAP,
                description="d",
                skipped=True,
            ),
        ]
        report = svc.generate_report(stages)
        assert "s2" not in report.by_stage

    def test_generate_report_with_cache_stats(self):
        from attune.models import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        def cache_fn():
            return {"hits": 5, "misses": 10, "hit_rate": 0.333}

        svc = self._make_service(cache_stats_fn=cache_fn)
        stages = [
            WorkflowStage(
                name="s1",
                tier=ModelTier.CAPABLE,
                description="d",
                input_tokens=1000,
                output_tokens=500,
                cost=0.05,
            ),
        ]
        report = svc.generate_report(stages)
        assert report.cache_hits == 5
        assert report.cache_misses == 10
        assert report.savings_from_cache > 0

    def test_get_cache_stats_no_fn(self):
        svc = self._make_service()
        stats = svc._get_cache_stats()
        assert stats == {"hits": 0, "misses": 0, "hit_rate": 0.0}

    def test_get_cache_stats_fn_error(self):
        svc = self._make_service(cache_stats_fn=lambda: (_ for _ in ()).throw(TypeError("bad")))
        stats = svc._get_cache_stats()
        assert stats == {"hits": 0, "misses": 0, "hit_rate": 0.0}


# =============================================================================
# TelemetryService Tests
# =============================================================================


class TestTelemetryService:
    """Tests for TelemetryService."""

    def _make_service(self, **kwargs):
        from attune.workflows.services.telemetry_service import TelemetryService

        defaults = {"workflow_name": "test-workflow", "provider": "anthropic"}
        defaults.update(kwargs)
        with patch("attune.models.get_telemetry_store"):
            return TelemetryService(**defaults)

    def test_init(self):
        svc = self._make_service()
        assert svc._workflow_name == "test-workflow"
        assert svc._provider == "anthropic"

    def test_run_id_initially_none(self):
        svc = self._make_service()
        assert svc.run_id is None

    def test_generate_run_id(self):
        svc = self._make_service()
        run_id = svc.generate_run_id()
        assert run_id is not None
        assert len(run_id) > 0
        assert svc.run_id == run_id

    def test_track_call_disabled(self):
        svc = self._make_service()
        svc._enabled = False
        # Should not raise
        svc.track_call(
            stage="s",
            tier=MagicMock(value="capable"),
            model="m",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
        )

    def test_track_call_no_tracker(self):
        svc = self._make_service()
        svc._tracker = None
        svc.track_call(
            stage="s",
            tier=MagicMock(value="capable"),
            model="m",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
        )

    def test_track_call_success(self):
        svc = self._make_service()
        mock_tracker = MagicMock()
        svc._tracker = mock_tracker
        svc._enabled = True
        tier_mock = MagicMock()
        tier_mock.value = "capable"
        svc.track_call(
            stage="analyze",
            tier=tier_mock,
            model="claude-3-sonnet",
            cost=0.01,
            tokens={"input": 500, "output": 200},
            cache_hit=False,
            cache_type=None,
            duration_ms=1200,
        )
        mock_tracker.track_llm_call.assert_called_once()

    def test_track_call_exception_handled(self):
        svc = self._make_service()
        mock_tracker = MagicMock()
        mock_tracker.track_llm_call.side_effect = OSError("disk full")
        svc._tracker = mock_tracker
        svc._enabled = True
        # Should not raise
        svc.track_call(
            stage="s",
            tier=MagicMock(value="capable"),
            model="m",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
        )

    def test_emit_call_record(self):
        svc = self._make_service()
        mock_backend = MagicMock()
        svc._backend = mock_backend
        svc.emit_call_record(
            step_name="analyze",
            task_type="code-review:analyze",
            tier="capable",
            model_id="claude-3-sonnet",
            input_tokens=500,
            output_tokens=200,
            cost=0.01,
            latency_ms=1200,
        )
        mock_backend.log_call.assert_called_once()

    def test_emit_call_record_with_error(self):
        svc = self._make_service()
        mock_backend = MagicMock()
        svc._backend = mock_backend
        svc.emit_call_record(
            step_name="s",
            task_type="t",
            tier="capable",
            model_id="m",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            latency_ms=100,
            success=False,
            error_message="API timeout",
            fallback_used=True,
        )
        mock_backend.log_call.assert_called_once()
        record = mock_backend.log_call.call_args[0][0]
        assert record.success is False
        assert record.error_message == "API timeout"
        assert record.fallback_used is True

    def test_emit_call_record_backend_error(self):
        svc = self._make_service()
        mock_backend = MagicMock()
        mock_backend.log_call.side_effect = OSError("disk full")
        svc._backend = mock_backend
        # Should not raise
        svc.emit_call_record(
            step_name="s",
            task_type="t",
            tier="c",
            model_id="m",
            input_tokens=1,
            output_tokens=1,
            cost=0.0,
            latency_ms=0,
        )

    def test_emit_call_record_no_backend(self):
        svc = self._make_service()
        svc._backend = None
        # Should not raise
        svc.emit_call_record(
            step_name="s",
            task_type="t",
            tier="c",
            model_id="m",
            input_tokens=1,
            output_tokens=1,
            cost=0.0,
            latency_ms=0,
        )

    def test_emit_workflow_record(self):
        from datetime import datetime

        svc = self._make_service()
        svc.generate_run_id()
        mock_backend = MagicMock()
        svc._backend = mock_backend

        # Build mock result
        mock_stage = MagicMock()
        mock_stage.name = "analyze"
        mock_stage.tier.value = "capable"
        mock_stage.input_tokens = 500
        mock_stage.output_tokens = 200
        mock_stage.cost = 0.01
        mock_stage.duration_ms = 1200
        mock_stage.skipped = False
        mock_stage.skip_reason = None

        mock_result = MagicMock()
        mock_result.stages = [mock_stage]
        mock_result.started_at = datetime(2026, 2, 13, 10, 0, 0)
        mock_result.completed_at = datetime(2026, 2, 13, 10, 0, 5)
        mock_result.total_duration_ms = 5000
        mock_result.success = True
        mock_result.error = None
        mock_result.cost_report.total_cost = 0.01
        mock_result.cost_report.baseline_cost = 0.05
        mock_result.cost_report.savings = 0.04
        mock_result.cost_report.savings_percent = 80.0
        mock_result.cost_report.by_tier = {"capable": 0.01}

        svc.emit_workflow_record(mock_result)
        mock_backend.log_workflow.assert_called_once()

    def test_emit_workflow_record_backend_error(self):
        from datetime import datetime

        svc = self._make_service()
        mock_backend = MagicMock()
        mock_backend.log_workflow.side_effect = OSError("disk full")
        svc._backend = mock_backend

        mock_result = MagicMock()
        mock_result.stages = []
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.total_duration_ms = 0
        mock_result.success = True
        mock_result.error = None
        mock_result.cost_report.total_cost = 0
        mock_result.cost_report.baseline_cost = 0
        mock_result.cost_report.savings = 0
        mock_result.cost_report.savings_percent = 0
        mock_result.cost_report.by_tier = {}

        # Should not raise
        svc.emit_workflow_record(mock_result)

    def test_emit_workflow_record_unexpected_error(self):
        from datetime import datetime

        svc = self._make_service()
        mock_backend = MagicMock()
        mock_backend.log_workflow.side_effect = RuntimeError("unexpected")
        svc._backend = mock_backend

        mock_result = MagicMock()
        mock_result.stages = []
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.total_duration_ms = 0
        mock_result.success = True
        mock_result.error = None
        mock_result.cost_report.total_cost = 0
        mock_result.cost_report.baseline_cost = 0
        mock_result.cost_report.savings = 0
        mock_result.cost_report.savings_percent = 0
        mock_result.cost_report.by_tier = {}

        # Should not raise (caught by BLE001)
        svc.emit_workflow_record(mock_result)

    def test_init_backend_default(self):
        """Test backend auto-initialization."""
        with patch("attune.models.get_telemetry_store") as mock_store:
            mock_backend = MagicMock()
            mock_store.return_value = mock_backend
            from attune.workflows.services.telemetry_service import TelemetryService

            svc = TelemetryService("test", "anthropic")
            assert svc._backend is mock_backend

    def test_init_tracker_unavailable(self):
        """Test tracker initialization when telemetry unavailable."""
        import attune.workflows.services.telemetry_service as ts_mod

        original = ts_mod._TELEMETRY_AVAILABLE
        try:
            ts_mod._TELEMETRY_AVAILABLE = False
            with patch("attune.models.get_telemetry_store"):
                svc = ts_mod.TelemetryService("test", "anthropic")
                assert svc._tracker is None
        finally:
            ts_mod._TELEMETRY_AVAILABLE = original
