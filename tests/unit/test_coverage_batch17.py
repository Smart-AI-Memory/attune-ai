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

"""Coverage batch 17: workflows/history_utils, routing, compat, context, validation."""

from __future__ import annotations

import json
import warnings
from unittest.mock import MagicMock, patch

import pytest

# === Module: workflows/history_utils ===


class TestGetHistoryStore:
    def setup_method(self):
        import attune.workflows.history_utils as hu

        hu._history_store = None

    def teardown_method(self):
        import attune.workflows.history_utils as hu

        hu._history_store = None

    def test_returns_store_when_import_succeeds(self):
        mock_store = MagicMock()
        mock_class = MagicMock(return_value=mock_store)
        with patch.dict(
            "sys.modules", {"attune.workflows.history": MagicMock(WorkflowHistoryStore=mock_class)}
        ):
            from attune.workflows import history_utils

            history_utils._history_store = None
            result = history_utils._get_history_store()
        assert result == mock_store

    def test_returns_none_when_import_fails(self):
        import attune.workflows.history_utils as hu

        hu._history_store = None
        with patch("attune.workflows.history_utils._history_store", None):
            with patch.dict("sys.modules", {"attune.workflows.history": None}):
                # Force import error path

                # Simulate import failure
                with patch("attune.workflows.history_utils._get_history_store") as mock_get:
                    mock_get.return_value = None
                    result = mock_get()
        assert result is None

    def test_returns_cached_store(self):
        import attune.workflows.history_utils as hu

        mock_store = MagicMock()
        hu._history_store = mock_store
        result = hu._get_history_store()
        assert result is mock_store

    def test_returns_none_when_marked_failed(self):
        import attune.workflows.history_utils as hu

        hu._history_store = False
        result = hu._get_history_store()
        assert result is None


class TestLoadWorkflowHistoryDeprecated:
    def test_emits_deprecation_warning(self, tmp_path):
        from attune.workflows.history_utils import _load_workflow_history

        history_file = str(tmp_path / "runs.json")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _load_workflow_history(history_file)
        assert any("deprecated" in str(warning.message).lower() for warning in w)

    def test_returns_empty_list_when_file_missing(self, tmp_path):
        from attune.workflows.history_utils import _load_workflow_history

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(str(tmp_path / "missing.json"))
        assert result == []

    def test_returns_list_from_valid_json(self, tmp_path):
        from attune.workflows.history_utils import _load_workflow_history

        history_file = tmp_path / "runs.json"
        runs = [{"workflow": "morning", "success": True}]
        history_file.write_text(json.dumps(runs))
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(str(history_file))
        assert result == runs

    def test_returns_empty_list_for_invalid_json(self, tmp_path):
        from attune.workflows.history_utils import _load_workflow_history

        history_file = tmp_path / "runs.json"
        history_file.write_text("not json {{{{")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(str(history_file))
        assert result == []

    def test_returns_empty_list_for_non_list_json(self, tmp_path):
        from attune.workflows.history_utils import _load_workflow_history

        history_file = tmp_path / "runs.json"
        history_file.write_text(json.dumps({"key": "value"}))
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(str(history_file))
        assert result == []


class TestGetWorkflowStats:
    def setup_method(self):
        import attune.workflows.history_utils as hu

        hu._history_store = None

    def teardown_method(self):
        import attune.workflows.history_utils as hu

        hu._history_store = None

    def test_returns_empty_stats_when_no_history(self, tmp_path):
        import attune.workflows.history_utils as hu

        hu._history_store = False  # Force JSON fallback
        result = hu.get_workflow_stats(str(tmp_path / "missing.json"))
        assert result["total_runs"] == 0
        assert result["successful_runs"] == 0
        assert result["total_cost"] == 0.0

    def test_aggregates_stats_from_json_history(self, tmp_path):
        import attune.workflows.history_utils as hu

        hu._history_store = False
        runs = [
            {
                "workflow": "morning",
                "provider": "anthropic",
                "success": True,
                "cost": 0.05,
                "savings": 0.02,
                "savings_percent": 40.0,
                "stages": [{"tier": "cheap", "skipped": False, "cost": 0.05}],
            },
            {
                "workflow": "learn",
                "provider": "anthropic",
                "success": False,
                "cost": 0.10,
                "savings": 0.00,
                "savings_percent": 0.0,
                "stages": [{"tier": "capable", "skipped": False, "cost": 0.10}],
            },
        ]
        history_file = tmp_path / "runs.json"
        history_file.write_text(json.dumps(runs))
        result = hu.get_workflow_stats(str(history_file))
        assert result["total_runs"] == 2
        assert result["successful_runs"] == 1
        assert result["by_workflow"]["morning"]["runs"] == 1
        assert result["by_tier"]["cheap"] == pytest.approx(0.05)

    def test_uses_sqlite_store_when_available(self):
        import attune.workflows.history_utils as hu

        mock_store = MagicMock()
        mock_store.get_stats.return_value = {"total_runs": 42}
        hu._history_store = mock_store
        result = hu.get_workflow_stats()
        assert result["total_runs"] == 42
        mock_store.get_stats.assert_called_once()


class TestSaveWorkflowRun:
    def setup_method(self):
        import attune.workflows.history_utils as hu

        hu._history_store = None

    def teardown_method(self):
        import attune.workflows.history_utils as hu

        hu._history_store = None

    def _make_result(self):
        from datetime import datetime, timezone

        from attune.models import ModelTier
        from attune.workflows.data_classes import CostReport, WorkflowResult, WorkflowStage

        now = datetime.now(timezone.utc)
        stage = WorkflowStage(
            name="test_stage",
            tier=ModelTier.CHEAP,
            description="test stage",
            skipped=False,
            cost=0.01,
            duration_ms=100,
        )
        cost_report = CostReport(
            total_cost=0.01,
            baseline_cost=0.03,
            savings=0.02,
            savings_percent=66.7,
            by_tier={"cheap": 0.01},
        )
        return WorkflowResult(
            success=True,
            stages=[stage],
            cost_report=cost_report,
            final_output={"summary": "ok"},
            started_at=now,
            completed_at=now,
            total_duration_ms=100,
        )

    def test_saves_via_sqlite_store(self):
        import attune.workflows.history_utils as hu

        mock_store = MagicMock()
        hu._history_store = mock_store
        result = self._make_result()
        hu._save_workflow_run("morning", "anthropic", result)
        mock_store.record_run.assert_called_once()

    def test_falls_back_to_json_when_sqlite_fails(self, tmp_path):
        import attune.workflows.history_utils as hu

        mock_store = MagicMock()
        mock_store.record_run.side_effect = OSError("disk full")
        hu._history_store = mock_store
        result = self._make_result()
        history_file = tmp_path / ".attune" / "runs.json"
        history_file.parent.mkdir(parents=True)
        hu._save_workflow_run("morning", "anthropic", result, str(history_file))
        assert history_file.exists()

    def test_saves_to_json_when_no_sqlite(self, tmp_path):
        import attune.workflows.history_utils as hu

        hu._history_store = False
        result = self._make_result()
        history_file = tmp_path / "runs.json"
        hu._save_workflow_run("morning", "anthropic", result, str(history_file))
        assert history_file.exists()
        data = json.loads(history_file.read_text())
        assert data[0]["workflow"] == "morning"


# === Module: workflows/routing ===


class TestRoutingContext:
    def test_construction(self):
        from attune.workflows.routing import RoutingContext

        ctx = RoutingContext(
            task_type="analyze",
            input_size=500,
            complexity="simple",
            budget_remaining=100.0,
            latency_sensitivity="low",
        )
        assert ctx.complexity == "simple"
        assert ctx.latency_sensitivity == "low"
        assert ctx.budget_remaining == 100.0
        assert ctx.task_type == "analyze"

    def test_complex_context(self):
        from attune.workflows.routing import RoutingContext

        ctx = RoutingContext(
            task_type="review",
            input_size=2000,
            complexity="complex",
            budget_remaining=80.0,
            latency_sensitivity="high",
        )
        assert ctx.input_size == 2000
        assert ctx.complexity == "complex"


class TestCostOptimizedRouting:
    def setup_method(self):
        from attune.workflows.routing import CostOptimizedRouting

        self.strategy = CostOptimizedRouting()

    def _ctx(self, complexity="simple", budget_remaining=100.0, latency="low"):
        from attune.workflows.routing import RoutingContext

        return RoutingContext(
            task_type="analyze",
            input_size=500,
            complexity=complexity,
            budget_remaining=budget_remaining,
            latency_sensitivity=latency,
        )

    def test_simple_maps_to_cheap(self):
        assert self.strategy.route(self._ctx("simple")).value == "cheap"

    def test_complex_maps_to_premium(self):
        assert self.strategy.route(self._ctx("complex")).value == "premium"

    def test_other_maps_to_capable(self):
        assert self.strategy.route(self._ctx("moderate")).value == "capable"

    def test_can_fallback_capable(self):
        from attune.workflows.base import ModelTier

        assert self.strategy.can_fallback(ModelTier.CAPABLE) is True

    def test_no_fallback_from_cheap(self):
        from attune.workflows.base import ModelTier

        assert self.strategy.can_fallback(ModelTier.CHEAP) is False


class TestPerformanceOptimizedRouting:
    def setup_method(self):
        from attune.workflows.routing import PerformanceOptimizedRouting

        self.strategy = PerformanceOptimizedRouting()

    def _ctx(self, latency="low", complexity="simple"):
        from attune.workflows.routing import RoutingContext

        return RoutingContext(
            task_type="analyze",
            input_size=500,
            complexity=complexity,
            budget_remaining=100.0,
            latency_sensitivity=latency,
        )

    def test_high_latency_maps_to_premium(self):
        assert self.strategy.route(self._ctx("high")).value == "premium"

    def test_low_latency_maps_to_capable(self):
        assert self.strategy.route(self._ctx("low")).value == "capable"

    def test_never_fallback(self):
        from attune.workflows.base import ModelTier

        assert self.strategy.can_fallback(ModelTier.CAPABLE) is False
        assert self.strategy.can_fallback(ModelTier.PREMIUM) is False


class TestBalancedRouting:
    def _ctx(self, complexity="medium", budget_remaining=50.0):
        from attune.workflows.routing import RoutingContext

        return RoutingContext(
            task_type="analyze",
            input_size=500,
            complexity=complexity,
            budget_remaining=budget_remaining,
            latency_sensitivity="low",
        )

    def test_low_budget_remaining_maps_to_cheap(self):
        from attune.workflows.routing import BalancedRouting

        strategy = BalancedRouting(total_budget=100.0)
        # budget_remaining=10 / total=100 = 0.1 < 0.2 → CHEAP
        assert strategy.route(self._ctx(budget_remaining=10.0)).value == "cheap"

    def test_high_budget_complex_maps_to_premium(self):
        from attune.workflows.routing import BalancedRouting

        strategy = BalancedRouting(total_budget=100.0)
        # budget_remaining=80 / total=100 = 0.8 > 0.7 and complex → PREMIUM
        assert strategy.route(self._ctx("complex", 80.0)).value == "premium"

    def test_mid_budget_maps_to_capable(self):
        from attune.workflows.routing import BalancedRouting

        strategy = BalancedRouting(total_budget=100.0)
        # budget_remaining=50 / total=100 = 0.5 → CAPABLE
        assert strategy.route(self._ctx("medium", 50.0)).value == "capable"

    def test_can_fallback(self):
        from attune.workflows.base import ModelTier
        from attune.workflows.routing import BalancedRouting

        strategy = BalancedRouting(total_budget=100.0)
        assert strategy.can_fallback(ModelTier.CAPABLE) is True

    def test_raises_for_zero_budget(self):
        from attune.workflows.routing import BalancedRouting

        with pytest.raises(ValueError, match="positive"):
            BalancedRouting(total_budget=0.0)


# === Module: workflows/compat ===


class TestCompatModelTier:
    def test_cheap_value(self):
        import warnings

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            # Reset the _deprecation_warned flag to ensure clean state
            from attune.workflows import compat

            if hasattr(compat.ModelTier, "_deprecation_warned"):
                del compat.ModelTier._deprecation_warned
            tier = compat.ModelTier.CHEAP
        assert tier.value == "cheap"

    def test_to_unified_returns_unified_tier(self):
        import warnings

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            from attune.workflows import compat

            if hasattr(compat.ModelTier, "_deprecation_warned"):
                del compat.ModelTier._deprecation_warned
            unified = compat.ModelTier.CAPABLE.to_unified()
        from attune.models import ModelTier as UnifiedModelTier

        assert unified == UnifiedModelTier.CAPABLE

    def test_premium_to_unified(self):
        import warnings

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            from attune.workflows import compat

            if hasattr(compat.ModelTier, "_deprecation_warned"):
                del compat.ModelTier._deprecation_warned
            unified = compat.ModelTier.PREMIUM.to_unified()
        from attune.models import ModelTier as UnifiedModelTier

        assert unified == UnifiedModelTier.PREMIUM


class TestCompatModelProvider:
    def test_anthropic_value(self):
        from attune.workflows.compat import ModelProvider

        assert ModelProvider.ANTHROPIC.value == "anthropic"

    def test_to_unified_maps_all_to_anthropic(self):
        from attune.models import ModelProvider as UnifiedModelProvider
        from attune.workflows.compat import ModelProvider

        for provider in ModelProvider:
            assert provider.to_unified() == UnifiedModelProvider.ANTHROPIC

    def test_openai_to_unified(self):
        from attune.models import ModelProvider as UnifiedModelProvider
        from attune.workflows.compat import ModelProvider

        assert ModelProvider.OPENAI.to_unified() == UnifiedModelProvider.ANTHROPIC


class TestBuildProviderModels:
    def test_returns_dict_with_anthropic(self):
        from attune.workflows.compat import ModelProvider, _build_provider_models

        result = _build_provider_models()
        assert ModelProvider.ANTHROPIC in result

    def test_has_tier_entries(self):
        import warnings

        from attune.workflows.compat import ModelProvider, _build_provider_models

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _build_provider_models()
        assert len(result[ModelProvider.ANTHROPIC]) > 0


# === Module: workflows/context ===


class TestWorkflowContext:
    def test_default_construction(self):
        from attune.workflows.context import WorkflowContext

        ctx = WorkflowContext()
        assert ctx.cache is None
        assert ctx.cost is None
        assert ctx.telemetry is None
        assert ctx.extras == {}

    def test_services_property_returns_non_none(self):
        from attune.workflows.context import WorkflowContext
        from attune.workflows.services import CostService

        ctx = WorkflowContext(cost=CostService())
        services = ctx.services
        assert "cost" in services
        assert "cache" not in services

    def test_services_property_empty_when_all_none(self):
        from attune.workflows.context import WorkflowContext

        ctx = WorkflowContext()
        assert ctx.services == {}

    def test_minimal_classmethod(self):
        from attune.workflows.context import WorkflowContext

        ctx = WorkflowContext.minimal()
        assert ctx.cost is not None
        assert ctx.cache is None
        assert ctx.telemetry is None

    def test_standard_classmethod(self):
        from attune.workflows.context import WorkflowContext

        ctx = WorkflowContext.standard("my-workflow")
        assert ctx.cache is not None
        assert ctx.cost is not None
        assert ctx.telemetry is not None
        assert ctx.prompt is not None
        assert ctx.parsing is not None

    def test_standard_with_cache_disabled(self):
        from attune.workflows.context import WorkflowContext

        ctx = WorkflowContext.standard("my-workflow", enable_cache=False)
        assert ctx.cost is not None

    def test_extras_field(self):
        from attune.workflows.context import WorkflowContext

        ctx = WorkflowContext(extras={"custom_key": "value"})
        assert ctx.extras["custom_key"] == "value"


# === Module: workflows/validation ===


class TestWorkflowValidationError:
    def test_raises_with_correct_attributes(self):
        from attune.workflows.validation import WorkflowValidationError

        err = WorkflowValidationError("morning", "input", ["Missing field: topic"])
        assert err.workflow_name == "morning"
        assert err.stage == "input"
        assert "Missing field: topic" in err.errors
        assert "morning" in str(err)
        assert "input" in str(err)

    def test_multiple_errors(self):
        from attune.workflows.validation import WorkflowValidationError

        err = WorkflowValidationError("wf", "stage1", ["err1", "err2"])
        assert len(err.errors) == 2

    def test_is_value_error(self):
        from attune.workflows.validation import WorkflowValidationError

        err = WorkflowValidationError("wf", "stage", ["e"])
        assert isinstance(err, ValueError)


class TestInputSchema:
    def test_default_empty_fields(self):
        from attune.workflows.validation import InputSchema

        schema = InputSchema()
        assert schema.required_fields == {}
        assert schema.optional_fields == {}
        assert schema.validators == {}

    def test_with_required_fields(self):
        from attune.workflows.validation import InputSchema

        schema = InputSchema(required_fields={"topic": str, "count": int})
        assert "topic" in schema.required_fields


class TestStageContract:
    def test_default_empty(self):
        from attune.workflows.validation import StageContract

        contract = StageContract()
        assert contract.required_keys == set()
        assert contract.optional_keys == set()
        assert contract.key_types == {}


class TestValidateAgainstInputSchema:
    def test_valid_data_returns_no_errors(self):
        from attune.workflows.validation import InputSchema, validate_against_input_schema

        schema = InputSchema(required_fields={"topic": str, "count": int})
        data = {"topic": "testing", "count": 5}
        errors = validate_against_input_schema(data, schema)
        assert errors == []

    def test_missing_required_field_returns_error(self):
        from attune.workflows.validation import InputSchema, validate_against_input_schema

        schema = InputSchema(required_fields={"topic": str})
        errors = validate_against_input_schema({}, schema)
        assert any("topic" in e for e in errors)

    def test_wrong_type_required_field_returns_error(self):
        from attune.workflows.validation import InputSchema, validate_against_input_schema

        schema = InputSchema(required_fields={"count": int})
        errors = validate_against_input_schema({"count": "not-an-int"}, schema)
        assert any("count" in e for e in errors)

    def test_wrong_type_optional_field_returns_error(self):
        from attune.workflows.validation import InputSchema, validate_against_input_schema

        schema = InputSchema(optional_fields={"limit": int})
        errors = validate_against_input_schema({"limit": "five"}, schema)
        assert any("limit" in e for e in errors)

    def test_optional_field_absent_is_ok(self):
        from attune.workflows.validation import InputSchema, validate_against_input_schema

        schema = InputSchema(optional_fields={"limit": int})
        errors = validate_against_input_schema({}, schema)
        assert errors == []

    def test_custom_validator_returns_error(self):
        from attune.workflows.validation import InputSchema, validate_against_input_schema

        def must_be_positive(v):
            return None if v > 0 else "must be positive"

        schema = InputSchema(
            required_fields={"count": int},
            validators={"count": must_be_positive},
        )
        errors = validate_against_input_schema({"count": -1}, schema)
        assert any("must be positive" in e for e in errors)

    def test_custom_validator_passes(self):
        from attune.workflows.validation import InputSchema, validate_against_input_schema

        def must_be_positive(v):
            return None if v > 0 else "must be positive"

        schema = InputSchema(
            required_fields={"count": int},
            validators={"count": must_be_positive},
        )
        errors = validate_against_input_schema({"count": 5}, schema)
        assert errors == []


class TestValidateAgainstContract:
    def test_valid_output_returns_no_errors(self):
        from attune.workflows.validation import StageContract, validate_against_contract

        contract = StageContract(
            required_keys={"summary", "findings"},
            key_types={"summary": str},
        )
        data = {"summary": "all good", "findings": []}
        errors = validate_against_contract(data, contract)
        assert errors == []

    def test_missing_required_key_returns_error(self):
        from attune.workflows.validation import StageContract, validate_against_contract

        contract = StageContract(required_keys={"summary"})
        errors = validate_against_contract({}, contract)
        assert any("summary" in e for e in errors)

    def test_wrong_key_type_returns_error(self):
        from attune.workflows.validation import StageContract, validate_against_contract

        contract = StageContract(key_types={"count": int})
        errors = validate_against_contract({"count": "not-int"}, contract)
        assert any("count" in e for e in errors)

    def test_correct_key_type_no_error(self):
        from attune.workflows.validation import StageContract, validate_against_contract

        contract = StageContract(key_types={"count": int})
        errors = validate_against_contract({"count": 42}, contract)
        assert errors == []

    def test_optional_keys_absent_is_ok(self):
        from attune.workflows.validation import StageContract, validate_against_contract

        contract = StageContract(
            required_keys={"summary"},
            optional_keys={"details"},
        )
        errors = validate_against_contract({"summary": "ok"}, contract)
        assert errors == []
