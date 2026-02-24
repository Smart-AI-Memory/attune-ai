"""Tests for the Socratic forms module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest


class TestFormField:
    """Tests for FormField class."""

    def test_create_text_field(self):
        """Test creating a text field."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="name",
            field_type=FieldType.TEXT,
            label="Your Name",
            validation=FieldValidation(required=True),
        )

        assert field.id == "name"
        assert field.field_type == FieldType.TEXT
        assert field.validation.required is True

    def test_create_select_field_with_options(self):
        """Test creating a select field with options."""
        from attune.socratic.forms import FieldOption, FieldType, FormField

        field = FormField(
            id="language",
            field_type=FieldType.SINGLE_SELECT,
            label="Programming Language",
            options=[
                FieldOption(value="python", label="Python"),
                FieldOption(value="javascript", label="JavaScript"),
            ],
        )

        assert len(field.options) == 2
        assert field.options[0].value == "python"

    def test_field_with_validation(self):
        """Test field with validation rules."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="email",
            field_type=FieldType.TEXT,
            label="Email",
            validation=FieldValidation(
                required=True,
                min_length=5,
                pattern=r"^[\w.-]+@[\w.-]+\.\w+$",
            ),
        )

        assert field.validation.required is True
        assert field.validation.min_length == 5

    def test_field_with_show_when(self):
        """Test conditional field visibility using dict format."""
        from attune.socratic.forms import FieldType, FormField

        # Note: show_when uses dict format, not ShowWhen object
        field = FormField(
            id="security_level",
            field_type=FieldType.SINGLE_SELECT,
            label="Security Level",
            show_when={
                "field_id": "enable_security",
                "operator": "equals",
                "value": True,
            },
        )

        assert field.show_when is not None
        assert field.show_when["field_id"] == "enable_security"


class TestForm:
    """Tests for Form class."""

    def test_create_form(self, sample_form):
        """Test creating a form."""
        assert sample_form.id == "test-form-001"
        assert len(sample_form.fields) == 3
        assert sample_form.round_number == 1

    def test_form_serialization(self, sample_form):
        """Test form serialization to dict."""
        data = sample_form.to_dict()

        assert data["id"] == sample_form.id
        assert data["title"] == sample_form.title
        assert len(data["fields"]) == 3

    @pytest.mark.skip(reason="Form.from_dict() not implemented - only to_dict() available")
    def test_form_deserialization(self, sample_form):
        """Test form deserialization from dict."""
        from attune.socratic.forms import Form

        data = sample_form.to_dict()
        restored = Form.from_dict(data)

        assert restored.id == sample_form.id
        assert len(restored.fields) == len(sample_form.fields)


class TestFormResponse:
    """Tests for FormResponse class."""

    def test_create_form_response(self, sample_form):
        """Test creating a form response."""
        from attune.socratic.forms import FormResponse

        response = FormResponse(
            form_id=sample_form.id,
            answers={
                "languages": ["python", "javascript"],
                "quality_focus": ["security"],
                "notes": "Focus on API endpoints",
            },
        )

        assert response.form_id == sample_form.id
        assert len(response.answers) == 3


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_valid_result(self):
        """Test valid validation result."""
        from attune.socratic.forms import ValidationResult

        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        # API uses field_errors and form_errors, not errors
        assert result.field_errors == {}
        assert result.form_errors == []

    def test_invalid_result_with_field_errors(self):
        """Test invalid validation result with field errors."""
        from attune.socratic.forms import ValidationResult

        result = ValidationResult(
            is_valid=False,
            field_errors={
                "name": "Field 'name' is required",
                "email": "Invalid email format",
            },
        )

        assert result.is_valid is False
        assert len(result.field_errors) == 2

    def test_invalid_result_with_form_errors(self):
        """Test invalid validation result with form-level errors."""
        from attune.socratic.forms import ValidationResult

        result = ValidationResult(
            is_valid=False,
            form_errors=["At least one field must be filled"],
        )

        assert result.is_valid is False
        assert len(result.form_errors) == 1

    def test_all_errors_property(self):
        """Test the all_errors property aggregates errors."""
        from attune.socratic.forms import ValidationResult

        result = ValidationResult(
            is_valid=False,
            field_errors={"name": "Required"},
            form_errors=["Form is incomplete"],
        )

        all_errors = result.all_errors
        assert len(all_errors) == 2


class TestFieldType:
    """Tests for FieldType enum."""

    def test_all_field_types(self):
        """Test all field types exist."""
        from attune.socratic.forms import FieldType

        assert FieldType.TEXT.value == "text"
        assert FieldType.TEXT_AREA.value == "text_area"
        assert FieldType.SINGLE_SELECT.value == "single_select"
        assert FieldType.MULTI_SELECT.value == "multi_select"
        assert FieldType.BOOLEAN.value == "boolean"
        assert FieldType.NUMBER.value == "number"
        assert FieldType.SLIDER.value == "slider"


class TestFormFieldValidate:
    """Tests for FormField.validate() method."""

    def test_validate_required_none_returns_invalid(self):
        """Test required field rejects None value."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="name",
            field_type=FieldType.TEXT,
            label="Name",
            validation=FieldValidation(required=True),
        )
        is_valid, error = field.validate(None)
        assert is_valid is False
        assert "required" in error.lower()

    def test_validate_required_empty_string_returns_invalid(self):
        """Test required field rejects empty string."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="name",
            field_type=FieldType.TEXT,
            label="Name",
            validation=FieldValidation(required=True),
        )
        is_valid, error = field.validate("   ")
        assert is_valid is False
        assert "required" in error.lower()

    def test_validate_required_empty_list_returns_invalid(self):
        """Test required field rejects empty list."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="langs",
            field_type=FieldType.MULTI_SELECT,
            label="Languages",
            validation=FieldValidation(required=True),
        )
        is_valid, error = field.validate([])
        assert is_valid is False
        assert "select" in error.lower()

    def test_validate_optional_none_returns_valid(self):
        """Test optional field accepts None value."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="notes",
            field_type=FieldType.TEXT,
            label="Notes",
            validation=FieldValidation(required=False),
        )
        is_valid, error = field.validate(None)
        assert is_valid is True
        assert error == ""

    def test_validate_min_length_too_short_returns_invalid(self):
        """Test string shorter than min_length is rejected."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="desc",
            field_type=FieldType.TEXT,
            label="Description",
            validation=FieldValidation(min_length=10),
        )
        is_valid, error = field.validate("short")
        assert is_valid is False
        assert "10" in error

    def test_validate_max_length_exceeded_returns_invalid(self):
        """Test string exceeding max_length is rejected."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="name",
            field_type=FieldType.TEXT,
            label="Name",
            validation=FieldValidation(max_length=5),
        )
        is_valid, error = field.validate("toolongvalue")
        assert is_valid is False
        assert "5" in error

    def test_validate_min_value_below_returns_invalid(self):
        """Test numeric below min_value is rejected."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="score",
            field_type=FieldType.NUMBER,
            label="Score",
            validation=FieldValidation(min_value=0),
        )
        is_valid, error = field.validate(-5)
        assert is_valid is False
        assert "at least" in error.lower()

    def test_validate_max_value_above_returns_invalid(self):
        """Test numeric above max_value is rejected."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="score",
            field_type=FieldType.NUMBER,
            label="Score",
            validation=FieldValidation(max_value=100),
        )
        is_valid, error = field.validate(150)
        assert is_valid is False
        assert "at most" in error.lower()

    def test_validate_pattern_mismatch_returns_invalid(self):
        """Test regex pattern mismatch is rejected."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="email",
            field_type=FieldType.TEXT,
            label="Email",
            validation=FieldValidation(
                pattern=r"^[\w.-]+@[\w.-]+\.\w+$",
                error_message="Invalid email format",
            ),
        )
        is_valid, error = field.validate("not-an-email")
        assert is_valid is False
        assert error == "Invalid email format"

    def test_validate_pattern_match_returns_valid(self):
        """Test regex pattern match is accepted."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="email",
            field_type=FieldType.TEXT,
            label="Email",
            validation=FieldValidation(pattern=r"^[\w.-]+@[\w.-]+\.\w+$"),
        )
        is_valid, error = field.validate("user@example.com")
        assert is_valid is True

    def test_validate_custom_validator_called(self):
        """Test custom validator function is invoked."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        def must_be_even(value):
            if value % 2 != 0:
                return False, "Value must be even"
            return True, ""

        field = FormField(
            id="count",
            field_type=FieldType.NUMBER,
            label="Count",
            validation=FieldValidation(custom_validator=must_be_even),
        )
        is_valid, error = field.validate(3)
        assert is_valid is False
        assert error == "Value must be even"

        is_valid, error = field.validate(4)
        assert is_valid is True

    def test_validate_valid_value_returns_valid(self):
        """Test valid value passes all checks."""
        from attune.socratic.forms import FieldType, FieldValidation, FormField

        field = FormField(
            id="name",
            field_type=FieldType.TEXT,
            label="Name",
            validation=FieldValidation(required=True, min_length=2, max_length=50),
        )
        is_valid, error = field.validate("Alice")
        assert is_valid is True
        assert error == ""


class TestFormFieldShouldShow:
    """Tests for FormField.should_show() method."""

    def test_should_show_no_condition_returns_true(self):
        """Test field with no show_when always shows."""
        from attune.socratic.forms import FieldType, FormField

        field = FormField(id="name", field_type=FieldType.TEXT, label="Name")
        assert field.should_show({}) is True

    def test_should_show_exact_match_satisfied_returns_true(self):
        """Test field shows when exact match condition is met."""
        from attune.socratic.forms import FieldType, FormField

        field = FormField(
            id="details",
            field_type=FieldType.TEXT,
            label="Details",
            show_when={"mode": "advanced"},
        )
        assert field.should_show({"mode": "advanced"}) is True

    def test_should_show_exact_match_unmet_returns_false(self):
        """Test field hides when exact match condition is not met."""
        from attune.socratic.forms import FieldType, FormField

        field = FormField(
            id="details",
            field_type=FieldType.TEXT,
            label="Details",
            show_when={"mode": "advanced"},
        )
        assert field.should_show({"mode": "basic"}) is False

    def test_should_show_list_condition_met_returns_true(self):
        """Test field shows when value is in expected list."""
        from attune.socratic.forms import FieldType, FormField

        field = FormField(
            id="security_opts",
            field_type=FieldType.TEXT,
            label="Security Options",
            show_when={"focus": ["security", "compliance"]},
        )
        assert field.should_show({"focus": "security"}) is True

    def test_should_show_list_condition_unmet_returns_false(self):
        """Test field hides when value is not in expected list."""
        from attune.socratic.forms import FieldType, FormField

        field = FormField(
            id="security_opts",
            field_type=FieldType.TEXT,
            label="Security Options",
            show_when={"focus": ["security", "compliance"]},
        )
        assert field.should_show({"focus": "performance"}) is False

    def test_should_show_multiselect_overlap_returns_true(self):
        """Test field shows when multi-select has overlapping values."""
        from attune.socratic.forms import FieldType, FormField

        field = FormField(
            id="sec_detail",
            field_type=FieldType.TEXT,
            label="Security Detail",
            show_when={"areas": ["security", "auth"]},
        )
        assert field.should_show({"areas": ["performance", "security"]}) is True

    def test_should_show_multiselect_no_overlap_returns_false(self):
        """Test field hides when multi-select has no overlap."""
        from attune.socratic.forms import FieldType, FormField

        field = FormField(
            id="sec_detail",
            field_type=FieldType.TEXT,
            label="Security Detail",
            show_when={"areas": ["security", "auth"]},
        )
        assert field.should_show({"areas": ["performance", "testing"]}) is False

    def test_should_show_missing_answer_returns_false(self):
        """Test field hides when required answer key is missing."""
        from attune.socratic.forms import FieldType, FormField

        field = FormField(
            id="details",
            field_type=FieldType.TEXT,
            label="Details",
            show_when={"mode": "advanced"},
        )
        assert field.should_show({}) is False


class TestFormGetVisibleFields:
    """Tests for Form.get_visible_fields() method."""

    def test_get_visible_fields_filters_hidden(self):
        """Test that hidden fields are excluded from visible list."""
        from attune.socratic.forms import FieldType, Form, FormField

        form = Form(
            id="test",
            title="Test",
            fields=[
                FormField(id="always", field_type=FieldType.TEXT, label="Always"),
                FormField(
                    id="conditional",
                    field_type=FieldType.TEXT,
                    label="Conditional",
                    show_when={"mode": "advanced"},
                ),
            ],
        )
        visible = form.get_visible_fields({"mode": "basic"})
        assert len(visible) == 1
        assert visible[0].id == "always"

    def test_get_visible_fields_includes_matching(self):
        """Test that matching conditional fields are included."""
        from attune.socratic.forms import FieldType, Form, FormField

        form = Form(
            id="test",
            title="Test",
            fields=[
                FormField(id="always", field_type=FieldType.TEXT, label="Always"),
                FormField(
                    id="conditional",
                    field_type=FieldType.TEXT,
                    label="Conditional",
                    show_when={"mode": "advanced"},
                ),
            ],
        )
        visible = form.get_visible_fields({"mode": "advanced"})
        assert len(visible) == 2


class TestFormGetFieldsByCategory:
    """Tests for Form.get_fields_by_category() method."""

    def test_get_fields_by_category_groups_correctly(self):
        """Test fields are grouped by their category."""
        from attune.socratic.forms import FieldType, Form, FormField

        form = Form(
            id="test",
            title="Test",
            fields=[
                FormField(id="f1", field_type=FieldType.TEXT, label="F1", category="general"),
                FormField(id="f2", field_type=FieldType.TEXT, label="F2", category="security"),
                FormField(id="f3", field_type=FieldType.TEXT, label="F3", category="general"),
            ],
        )
        grouped = form.get_fields_by_category()
        assert len(grouped["general"]) == 2
        assert len(grouped["security"]) == 1

    def test_get_fields_by_category_respects_visibility(self):
        """Test hidden fields are excluded from category groups."""
        from attune.socratic.forms import FieldType, Form, FormField

        form = Form(
            id="test",
            title="Test",
            fields=[
                FormField(id="f1", field_type=FieldType.TEXT, label="F1", category="general"),
                FormField(
                    id="f2",
                    field_type=FieldType.TEXT,
                    label="F2",
                    category="general",
                    show_when={"mode": "advanced"},
                ),
            ],
        )
        grouped = form.get_fields_by_category({"mode": "basic"})
        assert len(grouped["general"]) == 1

    def test_get_fields_by_category_sorts_by_order(self):
        """Test fields within categories are sorted by order."""
        from attune.socratic.forms import FieldType, Form, FormField

        form = Form(
            id="test",
            title="Test",
            fields=[
                FormField(id="f2", field_type=FieldType.TEXT, label="F2", category="a", order=2),
                FormField(id="f1", field_type=FieldType.TEXT, label="F1", category="a", order=1),
            ],
        )
        grouped = form.get_fields_by_category()
        assert grouped["a"][0].id == "f1"
        assert grouped["a"][1].id == "f2"


class TestFormToDict:
    """Tests for Form.to_dict() serialization."""

    def test_to_dict_includes_field_options(self):
        """Test serialization includes field options with all attributes."""
        from attune.socratic.forms import FieldOption, FieldType, FieldValidation, Form, FormField

        form = Form(
            id="test",
            title="Test Form",
            fields=[
                FormField(
                    id="choice",
                    field_type=FieldType.SINGLE_SELECT,
                    label="Pick One",
                    options=[
                        FieldOption(value="a", label="A", description="Option A", recommended=True),
                    ],
                    validation=FieldValidation(required=True, min_length=1, max_value=100),
                    show_when={"mode": "advanced"},
                ),
            ],
        )
        data = form.to_dict()

        field_data = data["fields"][0]
        assert field_data["id"] == "choice"
        assert field_data["type"] == "single_select"
        assert len(field_data["options"]) == 1
        assert field_data["options"][0]["recommended"] is True
        assert field_data["validation"]["required"] is True
        assert field_data["validation"]["min_length"] == 1
        assert field_data["validation"]["max_value"] == 100
        assert field_data["show_when"] == {"mode": "advanced"}


class TestFormResponseValidate:
    """Tests for FormResponse.validate() method."""

    def test_validate_all_valid_returns_valid(self):
        """Test validation passes when all required fields are provided."""
        from attune.socratic.forms import (
            FieldType,
            FieldValidation,
            Form,
            FormField,
            FormResponse,
        )

        form = Form(
            id="test",
            title="Test",
            fields=[
                FormField(
                    id="name",
                    field_type=FieldType.TEXT,
                    label="Name",
                    validation=FieldValidation(required=True),
                ),
            ],
        )
        response = FormResponse(form_id="test", answers={"name": "Alice"})
        result = response.validate(form)
        assert result.is_valid is True
        assert result.field_errors == {}

    def test_validate_missing_required_returns_errors(self):
        """Test validation fails when required field is missing."""
        from attune.socratic.forms import (
            FieldType,
            FieldValidation,
            Form,
            FormField,
            FormResponse,
        )

        form = Form(
            id="test",
            title="Test",
            fields=[
                FormField(
                    id="name",
                    field_type=FieldType.TEXT,
                    label="Name",
                    validation=FieldValidation(required=True),
                ),
            ],
        )
        response = FormResponse(form_id="test", answers={})
        result = response.validate(form)
        assert result.is_valid is False
        assert "name" in result.field_errors
