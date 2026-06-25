"""Coverage Batch 1 - Comprehensive tests for maximum statement coverage.

Targets modules at 0% coverage:
- src/attune/levels.py (~96 statements)
- src/attune/validation/xml_validator.py (~88 statements)
- src/attune/optimization/context_optimizer.py (~67 statements)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# =============================================================================
# Module 2: levels.py
# =============================================================================


class TestLevels:
    """Tests for levels.py - empathy level implementations."""

    # ---- EmpathyAction dataclass ----

    def test_empathy_action_required_fields(self) -> None:
        """Test EmpathyAction with only required fields."""
        from attune.levels import EmpathyAction

        action = EmpathyAction(level=2, action_type="test", description="desc")
        assert action.level == 2
        assert action.action_type == "test"
        assert action.description == "desc"

    def test_empathy_action_defaults(self) -> None:
        """Test EmpathyAction default values for optional fields."""
        from attune.levels import EmpathyAction

        action = EmpathyAction(level=1, action_type="t", description="d")
        assert action.context == {}
        assert action.outcome is None
        assert isinstance(action.timestamp, datetime)

    def test_empathy_action_all_fields(self) -> None:
        """Test EmpathyAction with all fields explicitly set."""
        from attune.levels import EmpathyAction

        ts = datetime(2026, 1, 1, 12, 0, 0)
        action = EmpathyAction(
            level=5,
            action_type="systems",
            description="Built framework",
            context={"scope": "global"},
            outcome="success",
            timestamp=ts,
        )
        assert action.level == 5
        assert action.context == {"scope": "global"}
        assert action.outcome == "success"
        assert action.timestamp == ts

    # ---- EmpathyLevel base class ----

    def test_record_action_and_get_history(self) -> None:
        """Test record_action appends to actions_taken and get_action_history returns them."""
        from attune.levels import Level1Reactive

        level = Level1Reactive()
        assert level.get_action_history() == []

        level.record_action("test_type", "test desc", {"k": "v"}, "success")
        history = level.get_action_history()
        assert len(history) == 1
        assert history[0].action_type == "test_type"
        assert history[0].description == "test desc"
        assert history[0].context == {"k": "v"}
        assert history[0].outcome == "success"
        assert history[0].level == 1

    def test_record_action_without_outcome(self) -> None:
        """Test record_action with None outcome."""
        from attune.levels import Level1Reactive

        level = Level1Reactive()
        level.record_action("type", "desc", {})
        assert level.get_action_history()[0].outcome is None

    def test_multiple_actions_accumulate(self) -> None:
        """Test multiple record_action calls accumulate in history."""
        from attune.levels import Level2Guided

        level = Level2Guided()
        for i in range(5):
            level.record_action(f"action_{i}", f"desc_{i}", {"i": i})
        assert len(level.get_action_history()) == 5

    # ---- Level1Reactive ----

    def test_level1_respond_complete_response(self) -> None:
        """Test Level1Reactive.respond returns all expected keys."""
        from attune.levels import Level1Reactive

        level = Level1Reactive()
        resp = level.respond({"request": "status", "subject": "project"})

        assert resp["level"] == 1
        assert resp["level_name"] == "Reactive Empathy"
        assert resp["action"] == "provide_requested_information"
        assert "status" in resp["description"]
        assert resp["initiative"] == "none"
        assert resp["additional_offers"] == []
        assert "Level 1" in resp["reasoning"]

    def test_level1_respond_default_request(self) -> None:
        """Test Level1Reactive.respond handles missing request key."""
        from attune.levels import Level1Reactive

        level = Level1Reactive()
        resp = level.respond({})
        assert "unknown" in resp["description"]

    def test_level1_respond_records_action(self) -> None:
        """Test Level1Reactive.respond records action in history."""
        from attune.levels import Level1Reactive

        level = Level1Reactive()
        level.respond({"request": "info", "subject": "tests"})
        history = level.get_action_history()
        assert len(history) == 1
        assert history[0].action_type == "reactive_response"
        assert "info" in history[0].description
        assert "tests" in history[0].description

    def test_level1_class_attributes(self) -> None:
        """Test Level1Reactive class-level attributes."""
        from attune.levels import Level1Reactive

        assert Level1Reactive.level_number == 1
        assert Level1Reactive.level_name == "Reactive Empathy"

    # ---- Level2Guided ----

    def test_level2_respond_complete_response(self) -> None:
        """Test Level2Guided.respond returns all expected keys."""
        from attune.levels import Level2Guided

        level = Level2Guided()
        resp = level.respond({"request": "improve", "ambiguity": "medium"})

        assert resp["level"] == 2
        assert resp["level_name"] == "Guided Empathy"
        assert resp["action"] == "collaborative_exploration"
        assert resp["initiative"] == "guided"
        assert "clarifying_questions" in resp
        assert "suggested_options" in resp
        assert "Level 2" in resp["reasoning"]

    def test_level2_medium_ambiguity_3_questions(self) -> None:
        """Test medium ambiguity generates exactly 3 questions."""
        from attune.levels import Level2Guided

        level = Level2Guided()
        resp = level.respond({"request": "improve", "ambiguity": "medium"})
        assert len(resp["clarifying_questions"]) == 3

    def test_level2_high_ambiguity_4_questions(self) -> None:
        """Test high ambiguity generates 4 questions including broader context."""
        from attune.levels import Level2Guided

        level = Level2Guided()
        resp = level.respond({"request": "improve", "ambiguity": "high"})
        assert len(resp["clarifying_questions"]) == 4
        assert "broader context" in resp["clarifying_questions"][-1]

    def test_level2_default_ambiguity(self) -> None:
        """Test default ambiguity is 'medium' generating 3 questions."""
        from attune.levels import Level2Guided

        level = Level2Guided()
        resp = level.respond({"request": "improve"})
        assert len(resp["clarifying_questions"]) == 3

    def test_level2_suggested_options(self) -> None:
        """Test suggested_options returns 3 exploration paths."""
        from attune.levels import Level2Guided

        level = Level2Guided()
        resp = level.respond({"request": "improve"})
        assert len(resp["suggested_options"]) == 3
        assert any("technical" in opt for opt in resp["suggested_options"])
        assert any("user impact" in opt for opt in resp["suggested_options"])
        assert any("risks" in opt for opt in resp["suggested_options"])

    def test_level2_records_action(self) -> None:
        """Test Level2Guided.respond records guided_exploration action."""
        from attune.levels import Level2Guided

        level = Level2Guided()
        level.respond({"request": "x"})
        history = level.get_action_history()
        assert history[0].action_type == "guided_exploration"
        assert "3" in history[0].description

    # ---- Level3Proactive ----

    def test_level3_respond_high_confidence(self) -> None:
        """Test Level3Proactive.respond with high confidence auto-proceeds."""
        from attune.levels import Level3Proactive

        level = Level3Proactive()
        resp = level.respond({"observed_need": "failing_tests", "confidence": 0.9})

        assert resp["level"] == 3
        assert resp["level_name"] == "Proactive Empathy"
        assert resp["action"] == "proactive_assistance"
        assert resp["initiative"] == "proactive"
        assert resp["observed_need"] == "failing_tests"
        assert resp["confidence"] == 0.9
        assert resp["proactive_offer"]["permission_needed"] is False
        assert resp["proactive_offer"]["action_plan"] == "Will proceed automatically"

    def test_level3_respond_low_confidence(self) -> None:
        """Test Level3Proactive.respond with low confidence asks permission."""
        from attune.levels import Level3Proactive

        level = Level3Proactive()
        resp = level.respond({"observed_need": "test", "confidence": 0.5})

        assert resp["proactive_offer"]["permission_needed"] is True
        assert resp["proactive_offer"]["action_plan"] == "Offering to help, awaiting permission"

    def test_level3_respond_boundary_confidence_0_8(self) -> None:
        """Test confidence exactly 0.8 does not need permission."""
        from attune.levels import Level3Proactive

        level = Level3Proactive()
        resp = level.respond({"observed_need": "test", "confidence": 0.8})
        assert resp["proactive_offer"]["permission_needed"] is False

    def test_level3_respond_boundary_confidence_0_79(self) -> None:
        """Test confidence 0.79 needs permission."""
        from attune.levels import Level3Proactive

        level = Level3Proactive()
        resp = level.respond({"observed_need": "test", "confidence": 0.79})
        assert resp["proactive_offer"]["permission_needed"] is True

    def test_level3_respond_default_values(self) -> None:
        """Test Level3Proactive.respond with empty context uses defaults."""
        from attune.levels import Level3Proactive

        level = Level3Proactive()
        resp = level.respond({})
        assert resp["observed_need"] == "unknown"
        assert resp["confidence"] == 0.5

    def test_level3_proactive_offer_structure(self) -> None:
        """Test proactive_offer dict has all expected keys."""
        from attune.levels import Level3Proactive

        level = Level3Proactive()
        resp = level.respond({"observed_need": "lint_errors", "confidence": 0.85})
        offer = resp["proactive_offer"]

        assert "need_identified" in offer
        assert "proposed_action" in offer
        assert "permission_needed" in offer
        assert "confidence_level" in offer
        assert "action_plan" in offer
        assert offer["need_identified"] == "lint_errors"
        assert offer["confidence_level"] == 0.85

    def test_level3_records_action(self) -> None:
        """Test Level3Proactive.respond records proactive_action."""
        from attune.levels import Level3Proactive

        level = Level3Proactive()
        level.respond({"observed_need": "coverage", "confidence": 0.9})
        assert level.get_action_history()[0].action_type == "proactive_action"

    # ---- Level4Anticipatory ----

    def test_level4_respond_complete(self) -> None:
        """Test Level4Anticipatory.respond returns complete response."""
        from attune.levels import Level4Anticipatory

        level = Level4Anticipatory()
        resp = level.respond(
            {
                "current_state": {"health": "good"},
                "trajectory": "compliance_gap",
                "prediction_horizon": "30_days",
            },
        )

        assert resp["level"] == 4
        assert resp["level_name"] == "Anticipatory Empathy"
        assert resp["action"] == "anticipatory_preparation"
        assert resp["initiative"] == "anticipatory"
        assert resp["current_trajectory"] == "compliance_gap"
        assert resp["prediction_horizon"] == "30_days"
        assert isinstance(resp["predicted_needs"], list)
        assert len(resp["predicted_needs"]) == 3
        assert isinstance(resp["preventive_actions"], list)
        assert len(resp["preventive_actions"]) == 3
        assert resp["confidence"] == 0.85
        assert "Level 4" in resp["reasoning"]

    def test_level4_respond_default_values(self) -> None:
        """Test Level4Anticipatory.respond with empty context uses defaults."""
        from attune.levels import Level4Anticipatory

        level = Level4Anticipatory()
        resp = level.respond({})
        assert resp["current_trajectory"] == "unknown"
        assert resp["prediction_horizon"] == "unknown"

    def test_level4_predicted_needs_include_trajectory(self) -> None:
        """Test predicted needs reference the trajectory."""
        from attune.levels import Level4Anticipatory

        level = Level4Anticipatory()
        resp = level.respond({"trajectory": "scaling_issue", "prediction_horizon": "90_days"})
        assert any("scaling_issue" in need for need in resp["predicted_needs"])
        assert any("90_days" in need for need in resp["predicted_needs"])

    def test_level4_records_action(self) -> None:
        """Test Level4Anticipatory.respond records anticipatory_preparation."""
        from attune.levels import Level4Anticipatory

        level = Level4Anticipatory()
        level.respond({"trajectory": "gap"})
        history = level.get_action_history()
        assert history[0].action_type == "anticipatory_preparation"
        assert "3" in history[0].description

    # ---- Level5Systems ----

    def test_level5_respond_complete(self) -> None:
        """Test Level5Systems.respond returns complete response."""
        from attune.levels import Level5Systems

        level = Level5Systems()
        resp = level.respond(
            {
                "problem_class": "documentation_burden",
                "instances": 18,
                "pattern": "repetitive_structure",
            },
        )

        assert resp["level"] == 5
        assert resp["level_name"] == "Systems Empathy"
        assert resp["action"] == "systems_level_solution"
        assert resp["initiative"] == "systems_thinking"
        assert resp["problem_class"] == "documentation_burden"
        assert resp["instances_addressed"] == 18
        assert "Level 5" in resp["reasoning"]

    def test_level5_system_created_structure(self) -> None:
        """Test system_created dict has name, description, and components."""
        from attune.levels import Level5Systems

        level = Level5Systems()
        resp = level.respond({"problem_class": "doc_burden", "instances": 10})
        system = resp["system_created"]

        assert system["name"] == "doc_burden_framework"
        assert "doc_burden" in system["description"]
        assert isinstance(system["components"], list)
        assert len(system["components"]) == 3

    def test_level5_leverage_point(self) -> None:
        """Test leverage_point references Meadows."""
        from attune.levels import Level5Systems

        level = Level5Systems()
        resp = level.respond({"problem_class": "test"})
        assert "Meadows" in resp["leverage_point"]
        assert "Level 9" in resp["leverage_point"]

    def test_level5_compounding_value(self) -> None:
        """Test compounding_value includes immediate, compounding, multiplier."""
        from attune.levels import Level5Systems

        level = Level5Systems()
        resp = level.respond({"problem_class": "test", "instances": 42})
        cv = resp["compounding_value"]
        assert "42" in cv["immediate"]
        assert "compounding" in cv
        assert "multiplier" in cv

    def test_level5_ai_ai_sharing(self) -> None:
        """Test ai_ai_sharing structure."""
        from attune.levels import Level5Systems

        level = Level5Systems()
        resp = level.respond({"problem_class": "test"})
        sharing = resp["ai_ai_sharing"]
        assert sharing["mechanism"] == "Pattern Library"
        assert sharing["scope"] == "All agents in collective"

    def test_level5_default_values(self) -> None:
        """Test Level5Systems.respond with empty context."""
        from attune.levels import Level5Systems

        level = Level5Systems()
        resp = level.respond({})
        assert resp["problem_class"] == "unknown"
        assert resp["instances_addressed"] == 0

    def test_level5_none_pattern(self) -> None:
        """Test Level5Systems.respond with pattern=None."""
        from attune.levels import Level5Systems

        level = Level5Systems()
        resp = level.respond({"problem_class": "test", "pattern": None})
        # Should not crash with None pattern
        assert resp["system_created"]["name"] == "test_framework"

    def test_level5_records_action(self) -> None:
        """Test Level5Systems.respond records systems_solution."""
        from attune.levels import Level5Systems

        level = Level5Systems()
        level.respond({"problem_class": "bugs", "instances": 5})
        history = level.get_action_history()
        assert history[0].action_type == "systems_solution"
        assert "bugs" in history[0].description

    # ---- get_level_class ----

    def test_get_level_class_all_valid(self) -> None:
        """Test get_level_class returns correct class for levels 1-5."""
        from attune.levels import (
            Level1Reactive,
            Level2Guided,
            Level3Proactive,
            Level4Anticipatory,
            Level5Systems,
            get_level_class,
        )

        expected = {
            1: Level1Reactive,
            2: Level2Guided,
            3: Level3Proactive,
            4: Level4Anticipatory,
            5: Level5Systems,
        }
        for num, cls in expected.items():
            assert get_level_class(num) is cls

    def test_get_level_class_invalid_falls_back_to_level1(self) -> None:
        """Test get_level_class returns Level1Reactive for invalid numbers."""
        from attune.levels import Level1Reactive, get_level_class

        assert get_level_class(0) is Level1Reactive
        assert get_level_class(6) is Level1Reactive
        assert get_level_class(-1) is Level1Reactive
        assert get_level_class(999) is Level1Reactive

    def test_get_level_class_instantiation(self) -> None:
        """Test returned classes can be instantiated."""
        from attune.levels import get_level_class

        for num in range(1, 6):
            instance = get_level_class(num)()
            assert instance.level_number == num
            assert isinstance(instance.level_name, str)


# =============================================================================
# Module 3: validation/xml_validator.py
# =============================================================================


class TestXMLValidator:
    """Tests for xml_validator.py - XML validation with fallbacks."""

    # ---- ValidationResult dataclass ----

    def test_validation_result_valid(self) -> None:
        """Test ValidationResult for valid parsing."""
        from attune.validation.xml_validator import ValidationResult

        r = ValidationResult(is_valid=True, parsed_data={"key": "val"})
        assert r.is_valid is True
        assert r.parsed_data == {"key": "val"}
        assert r.error_message is None
        assert r.fallback_used is False

    def test_validation_result_invalid(self) -> None:
        """Test ValidationResult for invalid parsing."""
        from attune.validation.xml_validator import ValidationResult

        r = ValidationResult(is_valid=False, error_message="Bad XML")
        assert r.is_valid is False
        assert r.error_message == "Bad XML"
        assert r.parsed_data is None

    def test_validation_result_fallback(self) -> None:
        """Test ValidationResult with fallback flag."""
        from attune.validation.xml_validator import ValidationResult

        r = ValidationResult(
            is_valid=True,
            parsed_data={"thinking": "x"},
            fallback_used=True,
            error_message="Used regex fallback",
        )
        assert r.fallback_used is True
        assert r.error_message == "Used regex fallback"

    # ---- XMLValidator init ----

    def test_init_defaults(self) -> None:
        """Test XMLValidator default initialization."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        assert v.strict is False
        assert v.enable_xsd is False
        assert v._schema_cache == {}
        assert v._lxml_available is False
        assert v.schema_dir == Path(".attune/schemas")

    def test_init_strict(self) -> None:
        """Test XMLValidator with strict=True."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator(strict=True)
        assert v.strict is True

    def test_init_custom_schema_dir(self) -> None:
        """Test XMLValidator with custom schema directory."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator(schema_dir="/custom/schemas")
        assert v.schema_dir == Path("/custom/schemas")

    def test_init_enable_xsd_without_lxml(self) -> None:
        """Test enable_xsd=True when lxml is not importable."""
        from attune.validation.xml_validator import XMLValidator

        with patch.dict("sys.modules", {"lxml": None, "lxml.etree": None}):
            v = XMLValidator(enable_xsd=True)
            assert v.enable_xsd is True
            assert v._lxml_available is False

    def test_init_enable_xsd_with_lxml(self) -> None:
        """Test enable_xsd=True when lxml is available."""
        from attune.validation.xml_validator import XMLValidator

        mock_lxml_etree = MagicMock()
        with patch.dict("sys.modules", {"lxml": MagicMock(), "lxml.etree": mock_lxml_etree}):
            v = XMLValidator(enable_xsd=True)
            assert v.enable_xsd is True
            assert v._lxml_available is True

    # ---- validate method ----

    def test_validate_well_formed_xml(self) -> None:
        """Test validate with well-formed XML."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v.validate("<root><child>text</child></root>")

        assert r.is_valid is True
        assert r.parsed_data == {"child": "text"}
        assert r.fallback_used is False

    def test_validate_nested_xml(self) -> None:
        """Test validate with nested elements."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v.validate("<root><parent><child>val</child></parent></root>")

        assert r.is_valid is True
        assert r.parsed_data["parent"]["child"] == "val"

    def test_validate_xml_with_attributes(self) -> None:
        """Test validate preserves attributes in _attributes key."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v.validate('<root id="42" type="test"><item>x</item></root>')

        assert r.is_valid is True
        assert r.parsed_data["_attributes"]["id"] == "42"
        assert r.parsed_data["_attributes"]["type"] == "test"
        assert r.parsed_data["item"] == "x"

    def test_validate_empty_child(self) -> None:
        """Test validate with empty child element returns empty string."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v.validate("<root><empty/></root>")

        assert r.is_valid is True
        assert r.parsed_data["empty"] == ""

    def test_validate_multiple_children(self) -> None:
        """Test validate with multiple siblings."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v.validate("<root><a>1</a><b>2</b><c>3</c></root>")

        assert r.parsed_data == {"a": "1", "b": "2", "c": "3"}

    def test_validate_malformed_xml_strict_fails(self) -> None:
        """Test validate in strict mode fails on malformed XML."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator(strict=True)
        r = v.validate("<broken xml <<invalid>")

        assert r.is_valid is False
        assert "XML parsing failed" in r.error_message
        assert r.fallback_used is False

    def test_validate_malformed_xml_non_strict_fallback(self) -> None:
        """Test validate in non-strict mode uses fallback for malformed XML."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator(strict=False)
        r = v.validate("prefix <thinking>Analysis</thinking> <answer>Result</answer> suffix")

        assert r.is_valid is True
        assert r.fallback_used is True
        assert r.parsed_data["thinking"] == "Analysis"
        assert r.parsed_data["answer"] == "Result"

    def test_validate_malformed_xml_non_strict_complete_failure(self) -> None:
        """Test validate non-strict with no extractable content fails."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator(strict=False)
        r = v.validate("just plain text with no tags at all")

        assert r.is_valid is False
        assert r.fallback_used is True
        assert "fallback failed" in r.error_message

    def test_validate_with_xsd_schema_valid(self) -> None:
        """Test validate calls XSD validation when schema_name is provided and lxml available."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator(enable_xsd=True)
        v._lxml_available = True

        mock_xsd_result = MagicMock()
        mock_xsd_result.is_valid = True

        with patch.object(v, "_validate_with_xsd", return_value=mock_xsd_result) as mock_xsd:
            r = v.validate("<root><item>test</item></root>", schema_name="test_schema")
            mock_xsd.assert_called_once()

        assert r.is_valid is True

    def test_validate_with_xsd_schema_fails_strict(self) -> None:
        """Test validate returns XSD error in strict mode when schema validation fails."""
        from attune.validation.xml_validator import ValidationResult, XMLValidator

        v = XMLValidator(enable_xsd=True, strict=True)
        v._lxml_available = True

        xsd_fail = ValidationResult(is_valid=False, error_message="Schema mismatch")

        with patch.object(v, "_validate_with_xsd", return_value=xsd_fail):
            r = v.validate("<root><item>test</item></root>", schema_name="test_schema")

        assert r.is_valid is False
        assert r.error_message == "Schema mismatch"

    def test_validate_with_xsd_schema_fails_non_strict(self) -> None:
        """Test validate returns data with fallback when XSD fails in non-strict mode."""
        from attune.validation.xml_validator import ValidationResult, XMLValidator

        v = XMLValidator(enable_xsd=True, strict=False)
        v._lxml_available = True

        xsd_fail = ValidationResult(is_valid=False, error_message="Schema mismatch")

        with patch.object(v, "_validate_with_xsd", return_value=xsd_fail):
            r = v.validate("<root><item>test</item></root>", schema_name="test_schema")

        assert r.is_valid is True
        assert r.fallback_used is True
        assert r.parsed_data is not None
        assert "Schema validation failed" in r.error_message

    # ---- _validate_with_xsd method ----

    def test_validate_with_xsd_lxml_not_available(self) -> None:
        """Test _validate_with_xsd returns error when lxml not available."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        v._lxml_available = False
        r = v._validate_with_xsd("<root/>", "schema")

        assert r.is_valid is False
        assert "lxml not available" in r.error_message

    def test_validate_with_xsd_import_fails(self) -> None:
        """Test _validate_with_xsd handles lxml import failure gracefully."""
        import sys

        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        v._lxml_available = True

        # Remove lxml from sys.modules to force ImportError
        saved_lxml = sys.modules.pop("lxml", None)
        saved_lxml_etree = sys.modules.pop("lxml.etree", None)
        try:
            # Set None to force ImportError on 'from lxml import etree'
            sys.modules["lxml"] = None
            r = v._validate_with_xsd("<root/>", "test")
        finally:
            # Restore
            if saved_lxml is not None:
                sys.modules["lxml"] = saved_lxml
            else:
                sys.modules.pop("lxml", None)
            if saved_lxml_etree is not None:
                sys.modules["lxml.etree"] = saved_lxml_etree
            else:
                sys.modules.pop("lxml.etree", None)

        assert r.is_valid is False
        assert "lxml import failed" in r.error_message

    def test_validate_with_xsd_schema_not_found(self) -> None:
        """Test _validate_with_xsd returns error for missing schema file."""
        import sys
        import types

        from attune.validation.xml_validator import XMLValidator

        mock_lxml_etree = MagicMock()
        mock_lxml = types.ModuleType("lxml")
        mock_lxml.etree = mock_lxml_etree

        v = XMLValidator(schema_dir="/nonexistent/dir")
        v._lxml_available = True

        saved_lxml = sys.modules.get("lxml")
        saved_lxml_etree = sys.modules.get("lxml.etree")
        try:
            sys.modules["lxml"] = mock_lxml
            sys.modules["lxml.etree"] = mock_lxml_etree
            r = v._validate_with_xsd("<root/>", "missing_schema")
        finally:
            if saved_lxml is not None:
                sys.modules["lxml"] = saved_lxml
            else:
                sys.modules.pop("lxml", None)
            if saved_lxml_etree is not None:
                sys.modules["lxml.etree"] = saved_lxml_etree
            else:
                sys.modules.pop("lxml.etree", None)

        assert r.is_valid is False
        assert "Schema not found" in r.error_message

    def _setup_lxml_mock(self, mock_lxml_etree: MagicMock) -> tuple:
        """Helper to set up lxml mock in sys.modules.

        Args:
            mock_lxml_etree: The mock to use as lxml.etree

        Returns:
            Tuple of (saved_lxml, saved_lxml_etree) for cleanup

        """
        import sys
        import types

        mock_lxml = types.ModuleType("lxml")
        mock_lxml.etree = mock_lxml_etree

        saved_lxml = sys.modules.get("lxml")
        saved_lxml_etree = sys.modules.get("lxml.etree")
        sys.modules["lxml"] = mock_lxml
        sys.modules["lxml.etree"] = mock_lxml_etree
        return saved_lxml, saved_lxml_etree

    def _teardown_lxml_mock(self, saved_lxml: Any, saved_lxml_etree: Any) -> None:
        """Helper to restore lxml in sys.modules after test.

        Args:
            saved_lxml: Original lxml module or None
            saved_lxml_etree: Original lxml.etree module or None

        """
        import sys

        if saved_lxml is not None:
            sys.modules["lxml"] = saved_lxml
        else:
            sys.modules.pop("lxml", None)
        if saved_lxml_etree is not None:
            sys.modules["lxml.etree"] = saved_lxml_etree
        else:
            sys.modules.pop("lxml.etree", None)

    def test_validate_with_xsd_schema_load_error(self) -> None:
        """Test _validate_with_xsd handles schema loading errors."""
        from attune.validation.xml_validator import XMLValidator

        mock_lxml_etree = MagicMock()
        mock_lxml_etree.parse.side_effect = RuntimeError("Bad schema")

        v = XMLValidator(schema_dir="/tmp")
        v._lxml_available = True

        saved = self._setup_lxml_mock(mock_lxml_etree)
        try:
            with patch.object(Path, "exists", return_value=True):
                r = v._validate_with_xsd("<root/>", "bad_schema")
        finally:
            self._teardown_lxml_mock(*saved)

        assert r.is_valid is False
        assert "Schema loading failed" in r.error_message

    def test_validate_with_xsd_valid_schema(self) -> None:
        """Test _validate_with_xsd with valid schema validation passes."""
        from attune.validation.xml_validator import XMLValidator

        mock_schema = MagicMock()
        mock_schema.validate.return_value = True

        mock_lxml_etree = MagicMock()
        mock_lxml_etree.parse.return_value = MagicMock()
        mock_lxml_etree.XMLSchema.return_value = mock_schema
        mock_lxml_etree.fromstring.return_value = MagicMock()

        v = XMLValidator(schema_dir="/tmp")
        v._lxml_available = True

        saved = self._setup_lxml_mock(mock_lxml_etree)
        try:
            with patch.object(Path, "exists", return_value=True):
                r = v._validate_with_xsd("<root/>", "valid_schema")
        finally:
            self._teardown_lxml_mock(*saved)

        assert r.is_valid is True

    def test_validate_with_xsd_invalid_schema_validation(self) -> None:
        """Test _validate_with_xsd returns error when document fails schema validation."""
        from attune.validation.xml_validator import XMLValidator

        mock_error_log = MagicMock()
        mock_schema = MagicMock()
        mock_schema.validate.return_value = False
        mock_schema.error_log = mock_error_log

        mock_lxml_etree = MagicMock()
        mock_lxml_etree.parse.return_value = MagicMock()
        mock_lxml_etree.XMLSchema.return_value = mock_schema
        mock_lxml_etree.fromstring.return_value = MagicMock()

        v = XMLValidator(schema_dir="/tmp")
        v._lxml_available = True

        saved = self._setup_lxml_mock(mock_lxml_etree)
        try:
            with patch.object(Path, "exists", return_value=True):
                r = v._validate_with_xsd("<root/>", "strict_schema")
        finally:
            self._teardown_lxml_mock(*saved)

        assert r.is_valid is False
        assert "Schema validation failed" in r.error_message

    def test_validate_with_xsd_validation_exception(self) -> None:
        """Test _validate_with_xsd handles exception during validation."""
        from attune.validation.xml_validator import XMLValidator

        mock_schema = MagicMock()

        mock_lxml_etree = MagicMock()
        mock_lxml_etree.parse.return_value = MagicMock()
        mock_lxml_etree.XMLSchema.return_value = mock_schema
        mock_lxml_etree.fromstring.side_effect = RuntimeError("Parse error")

        v = XMLValidator(schema_dir="/tmp")
        v._lxml_available = True

        saved = self._setup_lxml_mock(mock_lxml_etree)
        try:
            with patch.object(Path, "exists", return_value=True):
                r = v._validate_with_xsd("<root/>", "error_schema")
        finally:
            self._teardown_lxml_mock(*saved)

        assert r.is_valid is False
        assert "Validation error" in r.error_message

    def test_validate_with_xsd_uses_schema_cache(self) -> None:
        """Test _validate_with_xsd uses cached schema on second call."""
        from attune.validation.xml_validator import XMLValidator

        mock_schema = MagicMock()
        mock_schema.validate.return_value = True

        mock_lxml_etree = MagicMock()
        mock_lxml_etree.fromstring.return_value = MagicMock()

        v = XMLValidator(schema_dir="/tmp")
        v._lxml_available = True
        v._schema_cache["cached_schema"] = mock_schema

        saved = self._setup_lxml_mock(mock_lxml_etree)
        try:
            with patch.object(Path, "exists", return_value=True):
                r = v._validate_with_xsd("<root/>", "cached_schema")
        finally:
            self._teardown_lxml_mock(*saved)

        assert r.is_valid is True
        # parse should NOT be called since schema is cached
        mock_lxml_etree.parse.assert_not_called()

    # ---- _fallback_parse method ----

    def test_fallback_parse_thinking_only(self) -> None:
        """Test fallback extracts thinking tag."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v._fallback_parse("junk <thinking>Deep thought</thinking> more junk", "err")

        assert r.is_valid is True
        assert r.fallback_used is True
        assert r.parsed_data["thinking"] == "Deep thought"

    def test_fallback_parse_answer_only(self) -> None:
        """Test fallback extracts answer tag."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v._fallback_parse("prefix <answer>42</answer> suffix", "err")

        assert r.is_valid is True
        assert r.parsed_data["answer"] == "42"

    def test_fallback_parse_both_tags(self) -> None:
        """Test fallback extracts both thinking and answer."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v._fallback_parse("<thinking>Think</thinking><answer>Act</answer>", "err")

        assert r.parsed_data["thinking"] == "Think"
        assert r.parsed_data["answer"] == "Act"

    def test_fallback_parse_multiline_content(self) -> None:
        """Test fallback handles multiline content in tags."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v._fallback_parse("<thinking>\nLine 1\nLine 2\n</thinking>", "err")

        assert r.is_valid is True
        assert "Line 1" in r.parsed_data["thinking"]
        assert "Line 2" in r.parsed_data["thinking"]

    def test_fallback_parse_no_tags_complete_failure(self) -> None:
        """Test fallback with no recognizable tags returns failure."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v._fallback_parse("no xml content at all", "original error")

        assert r.is_valid is False
        assert r.fallback_used is True
        assert "fallback failed" in r.error_message
        assert "original error" in r.error_message

    def test_fallback_parse_includes_original_error(self) -> None:
        """Test fallback includes original error in message."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        r = v._fallback_parse("<thinking>ok</thinking>", "specific parse error xyz")

        assert "specific parse error xyz" in r.error_message

    # ---- _extract_data method ----

    def test_extract_data_leaf_nodes(self) -> None:
        """Test _extract_data with leaf text nodes."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        root = ET.fromstring("<root><name>Alice</name><age>30</age></root>")
        data = v._extract_data(root)

        assert data == {"name": "Alice", "age": "30"}

    def test_extract_data_nested(self) -> None:
        """Test _extract_data with nested elements."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        root = ET.fromstring("<root><parent><child>val</child></parent></root>")
        data = v._extract_data(root)

        assert data["parent"]["child"] == "val"

    def test_extract_data_with_attributes(self) -> None:
        """Test _extract_data stores root attributes."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        root = ET.fromstring('<root version="2"><item>x</item></root>')
        data = v._extract_data(root)

        assert data["_attributes"] == {"version": "2"}
        assert data["item"] == "x"

    def test_extract_data_no_attributes(self) -> None:
        """Test _extract_data omits _attributes when none exist."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        root = ET.fromstring("<root><item>x</item></root>")
        data = v._extract_data(root)

        assert "_attributes" not in data

    def test_extract_data_empty_node(self) -> None:
        """Test _extract_data returns empty string for empty nodes."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        root = ET.fromstring("<root><empty/></root>")
        data = v._extract_data(root)

        assert data["empty"] == ""

    def test_extract_data_deeply_nested(self) -> None:
        """Test _extract_data handles deeply nested elements."""
        from attune.validation.xml_validator import XMLValidator

        v = XMLValidator()
        root = ET.fromstring("<root><a><b><c>deep</c></b></a></root>")
        data = v._extract_data(root)

        assert data["a"]["b"]["c"] == "deep"

    # ---- validate_xml_response convenience function ----

    def test_validate_xml_response_valid(self) -> None:
        """Test convenience function with valid XML."""
        from attune.validation.xml_validator import validate_xml_response

        r = validate_xml_response("<root><item>val</item></root>")
        assert r.is_valid is True
        assert r.parsed_data["item"] == "val"

    def test_validate_xml_response_invalid_non_strict(self) -> None:
        """Test convenience function uses fallback in non-strict mode."""
        from attune.validation.xml_validator import validate_xml_response

        r = validate_xml_response("garbage <thinking>analysis</thinking> more")
        assert r.is_valid is True
        assert r.fallback_used is True
        assert r.parsed_data["thinking"] == "analysis"

    def test_validate_xml_response_invalid_strict(self) -> None:
        """Test convenience function fails in strict mode."""
        from attune.validation.xml_validator import validate_xml_response

        r = validate_xml_response("<broken", strict=True)
        assert r.is_valid is False

    def test_validate_xml_response_with_schema_name(self) -> None:
        """Test convenience function passes schema_name through."""
        from attune.validation.xml_validator import validate_xml_response

        # Without lxml, schema validation is skipped
        r = validate_xml_response("<root/>", schema_name="test")
        assert r.is_valid is True


# =============================================================================
# Module 4: optimization/context_optimizer.py
# =============================================================================


class TestContextOptimizer:
    """Tests for context_optimizer.py - prompt compression strategies."""

    # ---- CompressionLevel enum ----

    def test_compression_level_values(self) -> None:
        """Test all CompressionLevel enum values."""
        from attune.optimization.context_optimizer import CompressionLevel

        assert CompressionLevel.NONE.value == "none"
        assert CompressionLevel.LIGHT.value == "light"
        assert CompressionLevel.MODERATE.value == "moderate"
        assert CompressionLevel.AGGRESSIVE.value == "aggressive"
        assert len(CompressionLevel) == 4

    # ---- ContextOptimizer init ----

    def test_init_default_moderate(self) -> None:
        """Test default level is MODERATE."""
        from attune.optimization.context_optimizer import CompressionLevel, ContextOptimizer

        opt = ContextOptimizer()
        assert opt.level == CompressionLevel.MODERATE

    def test_init_custom_level(self) -> None:
        """Test custom compression level."""
        from attune.optimization.context_optimizer import CompressionLevel, ContextOptimizer

        opt = ContextOptimizer(CompressionLevel.AGGRESSIVE)
        assert opt.level == CompressionLevel.AGGRESSIVE

    def test_tag_mappings_and_reverse(self) -> None:
        """Test tag mappings and reverse mappings are consistent."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        for full, short in opt._tag_mappings.items():
            assert opt._reverse_mappings[short] == full

    # ---- optimize method ----

    def test_optimize_none_returns_unchanged(self) -> None:
        """Test NONE level returns input unchanged."""
        from attune.optimization.context_optimizer import CompressionLevel, ContextOptimizer

        opt = ContextOptimizer(CompressionLevel.NONE)
        original = "  <thinking>  lots   of   spaces  </thinking>  "
        assert opt.optimize(original) == original

    def test_optimize_light_whitespace_and_comments(self) -> None:
        """Test LIGHT level strips whitespace and removes comments."""
        from attune.optimization.context_optimizer import CompressionLevel, ContextOptimizer

        opt = ContextOptimizer(CompressionLevel.LIGHT)
        result = opt.optimize("<!-- comment -->  <root>  <child>  text  </child>  </root>")

        assert "<!--" not in result
        assert "  " not in result  # No double spaces

    def test_optimize_light_preserves_tags(self) -> None:
        """Test LIGHT level does not compress tag names."""
        from attune.optimization.context_optimizer import CompressionLevel, ContextOptimizer

        opt = ContextOptimizer(CompressionLevel.LIGHT)
        result = opt.optimize("<thinking>text</thinking>")

        assert "<thinking>" in result

    def test_optimize_moderate_compresses_tags_and_redundancy(self) -> None:
        """Test MODERATE level compresses tags and removes redundancy."""
        from attune.optimization.context_optimizer import CompressionLevel, ContextOptimizer

        opt = ContextOptimizer(CompressionLevel.MODERATE)
        result = opt.optimize("<thinking>Please note that test</thinking>")

        assert "<t>" in result
        assert "</t>" in result
        assert "Please note that " not in result

    def test_optimize_aggressive_includes_all_levels(self) -> None:
        """Test AGGRESSIVE level applies all optimizations."""
        from attune.optimization.context_optimizer import CompressionLevel, ContextOptimizer

        opt = ContextOptimizer(CompressionLevel.AGGRESSIVE)
        text = "<!-- comment --> <thinking> Please note that Generate the report </thinking>"
        result = opt.optimize(text)

        # Comment removed
        assert "<!--" not in result
        # Tags compressed
        assert "<t>" in result
        # Redundancy removed
        assert "Please note that " not in result
        # Abbreviation applied
        assert "Gen" in result

    # ---- decompress method ----

    def test_decompress_restores_all_tags(self) -> None:
        """Test decompress restores all compressed tag names."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        for full, short in opt._tag_mappings.items():
            compressed = f"<{short}>content</{short}>"
            result = opt.decompress(compressed)
            assert f"<{full}>" in result
            assert f"</{full}>" in result

    def test_decompress_restores_tags_with_attributes(self) -> None:
        """Test decompress handles opening tags with attributes."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        result = opt.decompress('<t type="deep">analysis</t>')
        assert '<thinking type="deep">' in result
        assert "</thinking>" in result

    def test_decompress_round_trip(self) -> None:
        """Test compress then decompress restores tag names."""
        from attune.optimization.context_optimizer import CompressionLevel, ContextOptimizer

        opt = ContextOptimizer(CompressionLevel.MODERATE)
        original = "<thinking>analysis</thinking><answer>result</answer>"
        compressed = opt.optimize(original)
        decompressed = opt.decompress(compressed)

        assert "<thinking>" in decompressed
        assert "</thinking>" in decompressed
        assert "<answer>" in decompressed
        assert "</answer>" in decompressed

    def test_decompress_unknown_tags_unchanged(self) -> None:
        """Test decompress leaves unknown tags unchanged."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        text = "<custom>value</custom>"
        assert opt.decompress(text) == text

    # ---- _strip_whitespace method ----

    def test_strip_whitespace_collapses_multiple_spaces(self) -> None:
        """Test multiple spaces become single space."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        assert opt._strip_whitespace("hello    world") == "hello world"

    def test_strip_whitespace_removes_tag_spacing(self) -> None:
        """Test spaces between tags are removed."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        result = opt._strip_whitespace("<a>x</a>   <b>y</b>")
        assert "><" in result

    def test_strip_whitespace_removes_empty_lines(self) -> None:
        """Test empty lines are removed."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        result = opt._strip_whitespace("line1\n\n\nline2")
        assert "\n\n" not in result
        assert "line1" in result
        assert "line2" in result

    def test_strip_whitespace_trims_lines(self) -> None:
        """Test leading/trailing whitespace on each line is stripped."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        result = opt._strip_whitespace("  hello  \n  world  ")
        for line in result.split("\n"):
            assert line == line.strip()

    # ---- _remove_comments method ----

    def test_remove_comments_single_line(self) -> None:
        """Test single-line comment removal."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        assert opt._remove_comments("a<!-- x -->b") == "ab"

    def test_remove_comments_multiline(self) -> None:
        """Test multi-line comment removal."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        assert opt._remove_comments("start<!--\nmulti\nline\n-->end") == "startend"

    def test_remove_comments_multiple(self) -> None:
        """Test multiple comments are all removed."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        assert opt._remove_comments("a<!-- 1 -->b<!-- 2 -->c") == "abc"

    def test_remove_comments_no_comments(self) -> None:
        """Test text without comments is unchanged."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        text = "<root>clean</root>"
        assert opt._remove_comments(text) == text

    # ---- _compress_tags method ----

    def test_compress_tags_known_tags(self) -> None:
        """Test known tags are compressed."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        assert opt._compress_tags("<thinking>x</thinking>") == "<t>x</t>"
        assert opt._compress_tags("<answer>x</answer>") == "<a>x</a>"
        assert opt._compress_tags("<description>x</description>") == "<desc>x</desc>"
        assert opt._compress_tags("<recommendation>x</recommendation>") == "<rec>x</rec>"

    def test_compress_tags_unknown_tags_unchanged(self) -> None:
        """Test unknown tags are not compressed."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        assert opt._compress_tags("<custom>x</custom>") == "<custom>x</custom>"

    def test_compress_tags_with_attributes(self) -> None:
        """Test tag compression handles attributes on opening tags."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        result = opt._compress_tags('<thinking type="deep">x</thinking>')
        assert '<t type="deep">' in result
        assert "</t>" in result

    # ---- _remove_redundancy method ----

    def test_remove_redundancy_all_phrases(self) -> None:
        """Test all redundant phrases are removed."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        phrases = {
            "Please note that ": "X is Y",
            "It is important to ": "validate",
            "Make sure to ": "check",
            "Be sure to ": "verify",
            "Remember to ": "test",
            "Don't forget to ": "commit",
        }
        for prefix, suffix in phrases.items():
            result = opt._remove_redundancy(f"{prefix}{suffix}")
            assert result == suffix, f"Failed to remove '{prefix}'"

    def test_remove_redundancy_no_match(self) -> None:
        """Test text without redundant phrases is unchanged."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        text = "Run the tests and verify"
        assert opt._remove_redundancy(text) == text

    # ---- _aggressive_compression method ----

    def test_aggressive_compression_removes_articles(self) -> None:
        """Test articles (a, an, the) removed from non-XML lines."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        result = opt._aggressive_compression("Find the bug in a file and an error")
        assert " the " not in result
        assert " a " not in result

    def test_aggressive_compression_preserves_xml_lines(self) -> None:
        """Test XML-containing lines preserve articles."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        result = opt._aggressive_compression("<tag>the value of a test</tag>")
        assert "the value" in result

    def test_aggressive_compression_abbreviations(self) -> None:
        """Test instruction word abbreviations are applied."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        cases = {
            "Generate": "Gen",
            "Provide": "Give",
            "Identify": "ID",
            "Determine": "Find",
            "Evaluate": "Eval",
            "Recommend": "Rec",
            "Implement": "Impl",
        }
        for original, expected in cases.items():
            result = opt._aggressive_compression(f"{original} something")
            assert expected in result, f"Failed abbreviation: {original} -> {expected}"

    def test_aggressive_compression_phrase_replacements(self) -> None:
        """Test phrase-level replacements."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        assert "below" in opt._aggressive_compression("See the following items")
        assert "should be" not in opt._aggressive_compression("Output should be valid")
        assert "you should" not in opt._aggressive_compression("you should check")
        assert "must be" not in opt._aggressive_compression("Value must be set")

    def test_aggressive_compression_mixed_lines(self) -> None:
        """Test aggressive compression with mixed XML and instruction lines."""
        from attune.optimization.context_optimizer import ContextOptimizer

        opt = ContextOptimizer()
        text = "<tag>preserve the articles</tag>\nGenerate the report\n<data>a value</data>"
        result = opt._aggressive_compression(text)
        lines = result.split("\n")

        # First line (XML) preserves articles
        assert "the articles" in lines[0]
        # Second line (instruction) abbreviates and removes articles
        assert "Gen" in lines[1]
        # Third line (XML) preserves articles
        assert "a value" in lines[2]

    # ---- optimize_xml_prompt convenience function ----

    def test_optimize_xml_prompt_default_moderate(self) -> None:
        """Test convenience function defaults to MODERATE."""
        from attune.optimization.context_optimizer import optimize_xml_prompt

        result = optimize_xml_prompt("<thinking>test</thinking>")
        assert "<t>" in result

    def test_optimize_xml_prompt_none_level(self) -> None:
        """Test convenience function with NONE level."""
        from attune.optimization.context_optimizer import CompressionLevel, optimize_xml_prompt

        original = "<thinking>  test  </thinking>"
        assert optimize_xml_prompt(original, level=CompressionLevel.NONE) == original

    def test_optimize_xml_prompt_light_level(self) -> None:
        """Test convenience function with LIGHT level."""
        from attune.optimization.context_optimizer import CompressionLevel, optimize_xml_prompt

        result = optimize_xml_prompt(
            "<!-- comment --><thinking>  text  </thinking>",
            level=CompressionLevel.LIGHT,
        )
        assert "<!--" not in result
        assert "<thinking>" in result  # Not compressed at LIGHT

    def test_optimize_xml_prompt_aggressive_level(self) -> None:
        """Test convenience function with AGGRESSIVE level."""
        from attune.optimization.context_optimizer import CompressionLevel, optimize_xml_prompt

        result = optimize_xml_prompt(
            "<thinking>Generate the report</thinking>",
            level=CompressionLevel.AGGRESSIVE,
        )
        assert "<t>" in result
        assert "Gen" in result
