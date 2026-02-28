"""Tests for specific pattern implementations.

Tests structural, input, validation, behavior, and empathy patterns.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from patterns.behavior import (
    AIEnhancementPattern,
    FixApplicationPattern,
    PredictionPattern,
    RiskAssessmentPattern,
    RiskLevel,
)
from patterns.core import PatternCategory
from patterns.empathy import EducationalBannerPattern, EmpathyLevelPattern, UserGuidancePattern
from patterns.input import (
    CodeAnalysisPattern,
    ContextBasedPattern,
    FieldDefinition,
    StructuredFieldsPattern,
)
from patterns.structural import (
    LinearFlowPattern,
    PhaseConfig,
    PhasedProcessingPattern,
    SessionBasedPattern,
    StepConfig,
)
from patterns.validation import ApprovalPattern, ConfigValidationPattern, StepValidationPattern


class TestStructuralPatterns:
    """Test structural pattern implementations."""

    def test_step_config_creation(self):
        """Should create StepConfig with valid data."""
        step = StepConfig(
            step=1,
            title="Step 1",
            prompt="Complete step 1",
            fields=["field1", "field2"],
            help_text="Help text",
        )

        assert step.step == 1
        assert step.title == "Step 1"
        assert step.fields == ["field1", "field2"]
        assert step.is_review_step is False

    def test_step_config_review_step(self):
        """Should support review step flag."""
        step = StepConfig(
            step=5,
            title="Review",
            prompt="Review and approve",
            fields=["user_approved"],
            help_text="Review all sections",
            is_review_step=True,
        )

        assert step.is_review_step is True

    def test_linear_flow_pattern_creation(self):
        """Should create LinearFlowPattern."""
        pattern = LinearFlowPattern(
            id="test_linear",
            name="Test Linear",
            description="Test pattern",
            frequency=5,
            reusability_score=0.9,
            total_steps=3,
            steps={
                1: StepConfig(
                    step=1,
                    title="Step 1",
                    prompt="Prompt",
                    fields=["f1"],
                    help_text="Help",
                ),
                2: StepConfig(
                    step=2,
                    title="Step 2",
                    prompt="Prompt",
                    fields=["f2"],
                    help_text="Help",
                ),
                3: StepConfig(
                    step=3,
                    title="Review",
                    prompt="Review",
                    fields=["approved"],
                    help_text="Review",
                    is_review_step=True,
                ),
            },
        )

        assert pattern.category == PatternCategory.STRUCTURAL
        assert pattern.total_steps == 3
        assert len(pattern.steps) == 3
        assert pattern.requires_approval is True

    def test_linear_flow_generate_endpoints(self):
        """Should generate correct endpoint list."""
        pattern = LinearFlowPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=0.8,
            total_steps=2,
            steps={
                1: StepConfig(step=1, title="S1", prompt="P", fields=[], help_text="H"),
                2: StepConfig(step=2, title="S2", prompt="P", fields=[], help_text="H"),
            },
        )

        endpoints = pattern.generate_endpoint_list()

        assert "POST /start" in endpoints
        assert "POST /{wizard_id}/step" in endpoints
        assert "POST /{wizard_id}/preview" in endpoints
        assert "POST /{wizard_id}/save" in endpoints
        assert "GET /{wizard_id}/report" in endpoints

    def test_linear_flow_generate_code(self):
        """Should generate FastAPI router code."""
        pattern = LinearFlowPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=0.8,
            total_steps=2,
            steps={
                1: StepConfig(step=1, title="S1", prompt="P", fields=["f1"], help_text="H"),
                2: StepConfig(step=2, title="S2", prompt="P", fields=["f2"], help_text="H"),
            },
        )

        code = pattern.generate_code()

        # Should contain key router elements
        assert "from fastapi import APIRouter" in code
        assert '@router.post("/start")' in code
        assert '@router.post("/{wizard_id}/step")' in code
        assert '@router.post("/{wizard_id}/preview")' in code
        assert "WIZARD_STEPS" in code

    def test_phase_config_creation(self):
        """Should create PhaseConfig."""
        phase = PhaseConfig(
            name="analyze",
            description="Perform analysis",
            required=True,
            parallel_with=["load_config"],
        )

        assert phase.name == "analyze"
        assert phase.required is True
        assert "load_config" in phase.parallel_with

    def test_phased_processing_pattern(self):
        """Should create PhasedProcessingPattern."""
        pattern = PhasedProcessingPattern(
            id="test_phased",
            name="Test Phased",
            description="Test",
            frequency=5,
            reusability_score=0.85,
            phases=[
                PhaseConfig(name="parse", description="Parse input", required=True),
                PhaseConfig(name="analyze", description="Analyze", required=True),
            ],
        )

        assert pattern.category == PatternCategory.STRUCTURAL
        assert len(pattern.phases) == 2
        assert pattern.phases[0].name == "parse"

    def test_phased_processing_generate_code(self):
        """Should generate phased wizard code."""
        pattern = PhasedProcessingPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=0.8,
            phases=[
                PhaseConfig(name="parse", description="Parse data", required=True),
                PhaseConfig(name="analyze", description="Analyze", required=True),
            ],
        )

        code = pattern.generate_code()

        assert "async def analyze(self, context" in code
        assert "Phase 1: Parse data" in code
        assert "Phase 2: Analyze" in code
        assert "parse_result = await self._parse(context)" in code

    def test_session_based_pattern(self):
        """Should create SessionBasedPattern."""
        pattern = SessionBasedPattern(
            id="test_session",
            name="Test Session",
            description="Test",
            frequency=10,
            reusability_score=0.95,
            session_ttl_seconds=3600,
            storage_backend="redis",
        )

        assert pattern.category == PatternCategory.STRUCTURAL
        assert pattern.session_ttl_seconds == 3600
        assert pattern.storage_backend == "redis"


class TestInputPatterns:
    """Test input pattern implementations."""

    def test_field_definition_creation(self):
        """Should create FieldDefinition."""
        field = FieldDefinition(
            name="email",
            field_type="str",
            required=True,
            description="User email address",
            default_value=None,
        )

        assert field.name == "email"
        assert field.field_type == "str"
        assert field.required is True

    def test_structured_fields_pattern(self):
        """Should create StructuredFieldsPattern."""
        pattern = StructuredFieldsPattern(
            id="test_fields",
            name="Test Fields",
            description="Test",
            frequency=10,
            reusability_score=0.9,
            fields_by_step={
                1: [
                    FieldDefinition(
                        name="field1",
                        field_type="str",
                        required=True,
                        description="Field 1",
                    ),
                    FieldDefinition(
                        name="field2",
                        field_type="int",
                        required=False,
                        default_value=0,
                    ),
                ],
            },
        )

        assert pattern.category == PatternCategory.INPUT
        assert len(pattern.fields_by_step[1]) == 2
        assert pattern.fields_by_step[1][0].name == "field1"

    def test_structured_fields_generate_code(self):
        """Should generate Pydantic request models."""
        pattern = StructuredFieldsPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=0.8,
            fields_by_step={
                1: [
                    FieldDefinition(
                        name="name",
                        field_type="str",
                        required=True,
                        description="User name",
                    ),
                    FieldDefinition(name="age", field_type="int", required=False, default_value=0),
                ],
            },
        )

        code = pattern.generate_code()

        assert "class Step1Request(BaseModel):" in code
        assert "name: str" in code
        assert "age: int = 0" in code

    def test_code_analysis_pattern(self):
        """Should create CodeAnalysisPattern."""
        pattern = CodeAnalysisPattern(
            id="test_code",
            name="Test Code Analysis",
            description="Test",
            frequency=15,
            reusability_score=0.9,
            supported_languages=["python", "javascript"],
            returns_issues=True,
        )

        assert pattern.category == PatternCategory.INPUT
        assert "python" in pattern.supported_languages
        assert pattern.returns_issues is True

    def test_context_based_pattern(self):
        """Should create ContextBasedPattern."""
        pattern = ContextBasedPattern(
            id="test_context",
            name="Test Context",
            description="Test",
            frequency=10,
            reusability_score=0.8,
            required_keys=["project_path"],
            optional_keys=["auto_fix", "verify"],
            key_descriptions={"project_path": "Path to project"},
        )

        assert pattern.category == PatternCategory.INPUT
        assert "project_path" in pattern.required_keys
        assert "auto_fix" in pattern.optional_keys


class TestValidationPatterns:
    """Test validation pattern implementations."""

    def test_config_validation_pattern(self):
        """Should create ConfigValidationPattern."""
        pattern = ConfigValidationPattern(
            id="test_config",
            name="Test Config Validation",
            description="Test",
            frequency=15,
            reusability_score=0.9,
            validation_rules=["empathy_level", "classification"],
            fail_fast=True,
        )

        assert pattern.category == PatternCategory.VALIDATION
        assert "empathy_level" in pattern.validation_rules
        assert pattern.fail_fast is True

    def test_config_validation_generate_code(self):
        """Should generate validation method."""
        pattern = ConfigValidationPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=0.8,
        )

        code = pattern.generate_code()

        assert "def _validate_config(self):" in code
        assert "empathy_level" in code
        assert "classification" in code

    def test_step_validation_pattern(self):
        """Should create StepValidationPattern."""
        pattern = StepValidationPattern(
            id="test_step",
            name="Test Step Validation",
            description="Test",
            frequency=15,
            reusability_score=0.9,
            allow_step_skipping=False,
            allow_step_revisiting=True,
        )

        assert pattern.category == PatternCategory.VALIDATION
        assert pattern.allow_step_skipping is False
        assert pattern.allow_step_revisiting is True

    def test_step_validation_generate_code(self):
        """Should generate step validation code."""
        pattern = StepValidationPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=0.8,
        )

        code = pattern.generate_code()

        assert 'submitted_step = step_data.get("step"' in code
        assert "HTTPException" in code
        assert "422" in code

    def test_approval_pattern(self):
        """Should create ApprovalPattern."""
        pattern = ApprovalPattern(
            id="test_approval",
            name="Test Approval",
            description="Test",
            frequency=15,
            reusability_score=0.95,
            requires_preview=True,
            approval_field="user_approved",
            allow_edits_after_preview=True,
        )

        assert pattern.category == PatternCategory.VALIDATION
        assert pattern.requires_preview is True
        assert pattern.approval_field == "user_approved"

    def test_approval_generate_code(self):
        """Should generate save endpoint with approval check."""
        pattern = ApprovalPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=0.9,
            approval_field="approved",
        )

        code = pattern.generate_code()

        assert '@router.post("/{wizard_id}/save")' in code
        assert "preview_report" in code
        assert "approved" in code  # Custom approval field


class TestBehaviorPatterns:
    """Test behavior pattern implementations."""

    def test_risk_level_creation(self):
        """Should create RiskLevel."""
        level = RiskLevel(name="critical", threshold=1, alert_message="Critical issues detected")

        assert level.name == "critical"
        assert level.threshold == 1

    def test_risk_assessment_pattern(self):
        """Should create RiskAssessmentPattern."""
        pattern = RiskAssessmentPattern(
            id="test_risk",
            name="Test Risk",
            description="Test",
            frequency=15,
            reusability_score=0.8,
            risk_levels=[
                RiskLevel(name="critical", threshold=1, alert_message="Critical"),
                RiskLevel(name="high", threshold=5, alert_message="High"),
            ],
        )

        assert pattern.category == PatternCategory.BEHAVIOR
        assert len(pattern.risk_levels) == 2
        assert pattern.risk_levels[0].name == "critical"

    def test_risk_assessment_generate_code(self):
        """Should generate risk analyzer code."""
        pattern = RiskAssessmentPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=0.8,
        )

        code = pattern.generate_code()

        assert "class RiskAnalyzer:" in code
        assert "def analyze(self, issues:" in code
        assert "alert_level" in code

    def test_ai_enhancement_pattern(self):
        """Should create AIEnhancementPattern."""
        pattern = AIEnhancementPattern(
            id="test_ai",
            name="Test AI Enhancement",
            description="Test",
            frequency=15,
            reusability_score=0.7,
            enhancement_guidelines=["Use proper terminology", "Professional tone"],
        )

        assert pattern.category == PatternCategory.BEHAVIOR
        assert len(pattern.enhancement_guidelines) >= 2

    def test_ai_enhancement_generate_code(self):
        """Should generate AI enhancement endpoint."""
        pattern = AIEnhancementPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=0.7,
            enhancement_guidelines=["Be clear"],
        )

        code = pattern.generate_code()

        assert '@router.post("/{wizard_id}/enhance")' in code
        assert "chat_service" in code
        assert "Be clear" in code

    def test_prediction_pattern(self):
        """Should create PredictionPattern."""
        pattern = PredictionPattern(
            id="test_pred",
            name="Test Prediction",
            description="Test",
            frequency=15,
            reusability_score=0.8,
            timeline_days=90,
            prediction_types=["production_failure_risk", "bug_density_increase"],
        )

        assert pattern.category == PatternCategory.BEHAVIOR
        assert pattern.timeline_days == 90
        assert "production_failure_risk" in pattern.prediction_types

    def test_fix_application_pattern(self):
        """Should create FixApplicationPattern."""
        pattern = FixApplicationPattern(
            id="test_fix",
            name="Test Fix",
            description="Test",
            frequency=8,
            reusability_score=0.75,
            auto_fix_enabled=True,
            dry_run_by_default=False,
            supported_fix_types=["lint", "format"],
        )

        assert pattern.category == PatternCategory.BEHAVIOR
        assert pattern.auto_fix_enabled is True
        assert "lint" in pattern.supported_fix_types


class TestEmpathyPatterns:
    """Test empathy pattern implementations."""

    def test_empathy_level_pattern(self):
        """Should create EmpathyLevelPattern."""
        pattern = EmpathyLevelPattern(
            id="test_empathy",
            name="Test Empathy",
            description="Test",
            frequency=16,
            reusability_score=1.0,
            default_level=2,
            level_descriptions={
                0: "Data only",
                1: "Reactive",
                2: "Responsive",
                3: "Proactive",
                4: "Anticipatory",
            },
            allow_user_override=True,
        )

        assert pattern.category == PatternCategory.EMPATHY
        assert pattern.default_level == 2
        assert len(pattern.level_descriptions) == 5
        assert pattern.allow_user_override is True

    def test_empathy_level_generate_code(self):
        """Should generate empathy config code."""
        pattern = EmpathyLevelPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=1.0,
        )

        code = pattern.generate_code()

        assert "@dataclass" in code
        assert "class WizardConfig:" in code
        assert "default_empathy_level: int = 2" in code
        assert "async def process(" in code

    def test_educational_banner_pattern(self):
        """Should create EducationalBannerPattern."""
        pattern = EducationalBannerPattern(
            id="test_banner",
            name="Test Banner",
            description="Test",
            frequency=16,
            reusability_score=1.0,
            banner_text="This is an educational tool",
            banner_type="educational",
            display_locations=["start", "preview", "report"],
            can_dismiss=False,
        )

        assert pattern.category == PatternCategory.EMPATHY
        assert pattern.banner_type == "educational"
        assert "start" in pattern.display_locations
        assert pattern.can_dismiss is False

    def test_educational_banner_generate_code(self):
        """Should generate banner display code."""
        pattern = EducationalBannerPattern(
            id="test",
            name="Test",
            description="Test",
            frequency=1,
            reusability_score=1.0,
            banner_text="Educational tool notice",
            banner_type="warning",
        )

        code = pattern.generate_code()

        assert 'BANNER = """' in code
        assert "Educational tool notice" in code
        assert "⚠️" in code  # Warning icon
        assert '@router.post("/start")' in code
        assert '"banner": BANNER' in code

    def test_user_guidance_pattern(self):
        """Should create UserGuidancePattern."""
        pattern = UserGuidancePattern(
            id="test_guidance",
            name="Test Guidance",
            description="Test",
            frequency=78,
            reusability_score=1.0,
            help_text_per_step={1: "Help for step 1", 2: "Help for step 2"},
            field_examples={"email": ["user@example.com", "test@test.com"]},
            contextual_prompts=True,
        )

        assert pattern.category == PatternCategory.EMPATHY
        assert pattern.help_text_per_step[1] == "Help for step 1"
        assert "user@example.com" in pattern.field_examples["email"]
        assert pattern.contextual_prompts is True
