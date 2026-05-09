"""Tests for socratic/web_ui.py module.

Tests the web UI components for rendering Socratic forms including:
- React component schemas
- HTML template rendering
- API endpoint helpers
- CSS/JS asset generation

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from unittest.mock import MagicMock

import pytest

from attune.socratic.forms import (
    FieldOption,
    FieldType,
    FieldValidation,
    Form,
    FormField,
)
from attune.socratic.session import SessionState, SocraticSession
from attune.socratic.web_ui import (
    FORM_CSS,
    FORM_JS,
    APIResponse,
    ReactBlueprintSchema,
    ReactFormSchema,
    ReactSessionSchema,
    _escape_html,
    _field_type_to_component,
    create_blueprint_response,
    create_form_response,
    get_form_assets,
    render_complete_page,
    render_form_html,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def simple_form():
    """Create a simple form for testing."""
    return Form(
        id="test-form-001",
        title="Test Form",
        description="A test form for unit testing",
        fields=[
            FormField(
                id="name",
                field_type=FieldType.TEXT,
                label="Name",
                placeholder="Enter your name",
                validation=FieldValidation(required=True),
            ),
            FormField(
                id="age",
                field_type=FieldType.NUMBER,
                label="Age",
                validation=FieldValidation(min_value=0, max_value=150),
            ),
        ],
        round_number=1,
        progress=0.5,
    )


@pytest.fixture
def complex_form():
    """Create a complex form with all field types."""
    return Form(
        id="complex-form-001",
        title="Complex Form",
        description="A form with all field types",
        fields=[
            FormField(
                id="languages",
                field_type=FieldType.MULTI_SELECT,
                label="Programming Languages",
                help_text="Select all that apply",
                category="technical",
                options=[
                    FieldOption(value="python", label="Python", recommended=True),
                    FieldOption(value="js", label="JavaScript", description="Frontend"),
                    FieldOption(value="rust", label="Rust"),
                ],
                validation=FieldValidation(required=True),
            ),
            FormField(
                id="focus",
                field_type=FieldType.SINGLE_SELECT,
                label="Quality Focus",
                category="preferences",
                options=[
                    FieldOption(value="security", label="Security"),
                    FieldOption(value="perf", label="Performance", recommended=True),
                ],
            ),
            FormField(
                id="notes",
                field_type=FieldType.TEXT_AREA,
                label="Additional Notes",
                placeholder="Any other notes...",
                category="preferences",
                validation=FieldValidation(max_length=1000),
            ),
            FormField(
                id="enable_auto",
                field_type=FieldType.BOOLEAN,
                label="Enable Automation",
                category="preferences",
            ),
            FormField(
                id="priority",
                field_type=FieldType.SLIDER,
                label="Priority",
                category="preferences",
                validation=FieldValidation(min_value=1, max_value=10),
            ),
            FormField(
                id="advanced_notes",
                field_type=FieldType.TEXT,
                label="Advanced Notes",
                show_when={"enable_auto": True},
                category="preferences",
            ),
        ],
        round_number=2,
        progress=0.75,
        is_final=True,
        categories=["technical", "preferences"],
    )


@pytest.fixture
def mock_session():
    """Create a mock SocraticSession for testing."""
    session = SocraticSession(session_id="test-session-001")
    session.goal = "Automate code reviews for Python"
    session.state = SessionState.AWAITING_ANSWERS
    session.current_round = 1

    # Mock goal_analysis
    goal_analysis = MagicMock()
    goal_analysis.domain = "code_review"
    goal_analysis.confidence = 0.85
    goal_analysis.ambiguities = ["Which languages?"]
    goal_analysis.assumptions = ["Python codebase"]
    session.goal_analysis = goal_analysis

    # Mock requirements
    requirements = MagicMock()
    requirements.completeness_score.return_value = 0.6
    session.requirements = requirements

    return session


@pytest.fixture
def mock_blueprint():
    """Create a mock WorkflowBlueprint for testing."""
    from attune.socratic.blueprint import (
        AgentBlueprint,
        AgentRole,
        AgentSpec,
        StageSpec,
        ToolCategory,
        ToolSpec,
        WorkflowBlueprint,
    )
    from attune.socratic.success import MetricType, SuccessCriteria, SuccessMetric

    agent_spec = AgentSpec(
        id="reviewer-001",
        name="Code Reviewer",
        role=AgentRole.REVIEWER,
        goal="Review code for quality issues",
        backstory="Expert code reviewer" * 30,  # Long backstory for truncation test
        model_tier="capable",
        tools=[
            ToolSpec(
                id="read_file",
                name="Read File",
                description="Read file contents",
                category=ToolCategory.CODE_ANALYSIS,
            ),
        ],
    )

    success_criteria = SuccessCriteria(
        id="test-criteria",
        name="Review Success",
        description="Success metrics for review",
        metrics=[
            SuccessMetric(
                id="issues",
                name="Issues Found",
                description="Number of issues found",
                metric_type=MetricType.COUNT,
            ),
        ],
    )

    return WorkflowBlueprint(
        id="test-blueprint-001",
        name="Test Review Workflow",
        description="A test workflow for reviews",
        domain="code_review",
        supported_languages=["python", "typescript"],
        quality_focus=["security", "performance"],
        automation_level="semi_auto",
        agents=[AgentBlueprint(spec=agent_spec)],
        stages=[
            StageSpec(
                id="review",
                name="Review Stage",
                description="Perform review",
                agent_ids=["reviewer-001"],
                parallel=False,
                depends_on=[],
            ),
        ],
        success_criteria=success_criteria,
    )


# =============================================================================
# REACT FORM SCHEMA TESTS
# =============================================================================


@pytest.mark.unit
class TestReactFormSchema:
    """Tests for ReactFormSchema."""

    def test_from_form_basic(self, simple_form):
        """Test creating schema from simple form."""
        schema = ReactFormSchema.from_form(simple_form)

        assert schema.form_id == "test-form-001"
        assert schema.title == "Test Form"
        assert schema.description == "A test form for unit testing"
        assert schema.progress == 0.5
        assert schema.round_number == 1
        assert schema.is_final is False
        assert len(schema.fields) == 2

    def test_from_form_field_mapping(self, simple_form):
        """Test field mapping in schema."""
        schema = ReactFormSchema.from_form(simple_form)

        name_field = schema.fields[0]
        assert name_field["id"] == "name"
        assert name_field["type"] == "TextInput"
        assert name_field["label"] == "Name"
        assert name_field["placeholder"] == "Enter your name"
        assert name_field["required"] is True

    def test_from_form_validation_mapping(self, simple_form):
        """Test validation rules are mapped."""
        schema = ReactFormSchema.from_form(simple_form)

        age_field = schema.fields[1]
        assert age_field["validation"]["minValue"] == 0
        assert age_field["validation"]["maxValue"] == 150

    def test_from_form_options_mapping(self, complex_form):
        """Test options are mapped correctly."""
        schema = ReactFormSchema.from_form(complex_form)

        languages_field = schema.fields[0]
        assert languages_field["type"] == "CheckboxGroup"
        assert len(languages_field["options"]) == 3

        python_option = languages_field["options"][0]
        assert python_option["value"] == "python"
        assert python_option["label"] == "Python"
        assert python_option["recommended"] is True

    def test_from_form_categories(self, complex_form):
        """Test categories are included."""
        schema = ReactFormSchema.from_form(complex_form)

        assert "technical" in schema.categories
        assert "preferences" in schema.categories

    def test_from_form_show_when(self, complex_form):
        """Test showWhen conditions are mapped."""
        schema = ReactFormSchema.from_form(complex_form)

        advanced_field = next(f for f in schema.fields if f["id"] == "advanced_notes")
        assert advanced_field["showWhen"] == {"enable_auto": True}

    def test_to_json(self, simple_form):
        """Test JSON serialization."""
        schema = ReactFormSchema.from_form(simple_form)
        json_str = schema.to_json()

        parsed = json.loads(json_str)
        assert parsed["form_id"] == "test-form-001"
        assert parsed["title"] == "Test Form"
        assert len(parsed["fields"]) == 2


# =============================================================================
# FIELD TYPE MAPPING TESTS
# =============================================================================


@pytest.mark.unit
class TestFieldTypeMapping:
    """Tests for _field_type_to_component."""

    @pytest.mark.parametrize(
        "field_type,expected",
        [
            (FieldType.SINGLE_SELECT, "RadioGroup"),
            (FieldType.MULTI_SELECT, "CheckboxGroup"),
            (FieldType.TEXT, "TextInput"),
            (FieldType.TEXT_AREA, "TextArea"),
            (FieldType.SLIDER, "Slider"),
            (FieldType.BOOLEAN, "Switch"),
            (FieldType.NUMBER, "NumberInput"),
            (FieldType.GROUP, "FieldGroup"),
        ],
    )
    def test_field_type_mapping(self, field_type, expected):
        """Test each field type maps correctly."""
        result = _field_type_to_component(field_type)
        assert result == expected

    def test_unknown_type_defaults_to_text_input(self):
        """Test unknown field type defaults to TextInput."""
        # Create a mock unknown type
        unknown_type = MagicMock()
        result = _field_type_to_component(unknown_type)
        assert result == "TextInput"


# =============================================================================
# REACT SESSION SCHEMA TESTS
# =============================================================================


@pytest.mark.unit
class TestReactSessionSchema:
    """Tests for ReactSessionSchema."""

    def test_from_session(self, mock_session):
        """Test creating schema from session."""
        schema = ReactSessionSchema.from_session(mock_session)

        assert schema.session_id == "test-session-001"
        assert schema.state == "awaiting_answers"
        assert schema.goal == "Automate code reviews for Python"
        assert schema.domain == "code_review"
        assert schema.confidence == 0.85
        assert schema.current_round == 1

    def test_from_session_with_ambiguities(self, mock_session):
        """Test ambiguities are included."""
        schema = ReactSessionSchema.from_session(mock_session)

        assert "Which languages?" in schema.ambiguities

    def test_from_session_with_assumptions(self, mock_session):
        """Test assumptions are included."""
        schema = ReactSessionSchema.from_session(mock_session)

        assert "Python codebase" in schema.assumptions

    def test_from_session_without_goal_analysis(self):
        """Test handling session without goal analysis."""
        session = SocraticSession(session_id="test-002")
        session.goal = "Some goal"
        session.state = SessionState.AWAITING_GOAL
        session.goal_analysis = None

        # Mock requirements
        requirements = MagicMock()
        requirements.completeness_score.return_value = 0.0
        session.requirements = requirements

        schema = ReactSessionSchema.from_session(session)

        assert schema.domain is None
        assert schema.confidence == 0
        assert schema.ambiguities == []
        assert schema.assumptions == []

    def test_to_json(self, mock_session):
        """Test JSON serialization."""
        schema = ReactSessionSchema.from_session(mock_session)
        json_str = schema.to_json()

        parsed = json.loads(json_str)
        assert parsed["session_id"] == "test-session-001"
        assert parsed["domain"] == "code_review"


# =============================================================================
# REACT BLUEPRINT SCHEMA TESTS
# =============================================================================


@pytest.mark.unit
class TestReactBlueprintSchema:
    """Tests for ReactBlueprintSchema."""

    def test_from_blueprint(self, mock_blueprint):
        """Test creating schema from blueprint."""
        schema = ReactBlueprintSchema.from_blueprint(mock_blueprint)

        assert schema.id == "test-blueprint-001"
        assert schema.name == "Test Review Workflow"
        assert schema.description == "A test workflow for reviews"
        assert schema.domain == "code_review"
        assert "python" in schema.languages
        assert "security" in schema.quality_focus
        assert schema.automation_level == "semi_auto"

    def test_from_blueprint_agents(self, mock_blueprint):
        """Test agent mapping."""
        schema = ReactBlueprintSchema.from_blueprint(mock_blueprint)

        assert len(schema.agents) == 1
        agent = schema.agents[0]
        assert agent["id"] == "reviewer-001"
        assert agent["name"] == "Code Reviewer"
        assert agent["role"] == "reviewer"
        assert agent["modelTier"] == "capable"
        assert "Read File" in agent["tools"]

    def test_from_blueprint_backstory_truncation(self, mock_blueprint):
        """Test long backstory is truncated."""
        schema = ReactBlueprintSchema.from_blueprint(mock_blueprint)

        agent = schema.agents[0]
        # Should be truncated to 200 chars + "..."
        assert len(agent["backstory"]) <= 203
        assert agent["backstory"].endswith("...")

    def test_from_blueprint_stages(self, mock_blueprint):
        """Test stage mapping."""
        schema = ReactBlueprintSchema.from_blueprint(mock_blueprint)

        assert len(schema.stages) == 1
        stage = schema.stages[0]
        assert stage["id"] == "review"
        assert stage["name"] == "Review Stage"
        assert "reviewer-001" in stage["agents"]
        assert stage["parallel"] is False

    def test_from_blueprint_success_criteria(self, mock_blueprint):
        """Test success criteria mapping."""
        schema = ReactBlueprintSchema.from_blueprint(mock_blueprint)

        assert schema.success_criteria is not None
        assert "id" in schema.success_criteria

    def test_from_blueprint_without_success_criteria(self, mock_blueprint):
        """Test blueprint without success criteria."""
        mock_blueprint.success_criteria = None
        schema = ReactBlueprintSchema.from_blueprint(mock_blueprint)

        assert schema.success_criteria is None

    def test_to_json(self, mock_blueprint):
        """Test JSON serialization."""
        schema = ReactBlueprintSchema.from_blueprint(mock_blueprint)
        json_str = schema.to_json()

        parsed = json.loads(json_str)
        assert parsed["id"] == "test-blueprint-001"
        assert parsed["domain"] == "code_review"


# =============================================================================
# HTML ESCAPE TESTS
# =============================================================================


@pytest.mark.unit
class TestHtmlEscape:
    """Tests for _escape_html function."""

    def test_escape_ampersand(self):
        """Test ampersand escaping."""
        assert _escape_html("A & B") == "A &amp; B"

    def test_escape_less_than(self):
        """Test less than escaping."""
        assert _escape_html("a < b") == "a &lt; b"

    def test_escape_greater_than(self):
        """Test greater than escaping."""
        assert _escape_html("a > b") == "a &gt; b"

    def test_escape_double_quote(self):
        """Test double quote escaping."""
        assert _escape_html('Say "hello"') == "Say &quot;hello&quot;"

    def test_escape_single_quote(self):
        """Test single quote escaping."""
        assert _escape_html("It's") == "It&#x27;s"

    def test_escape_multiple(self):
        """Test escaping multiple characters."""
        result = _escape_html('<script>alert("XSS")</script>')
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result

    def test_escape_safe_text(self):
        """Test text without special chars is unchanged."""
        safe = "Hello World 123"
        assert _escape_html(safe) == safe


# =============================================================================
# RENDER FORM HTML TESTS
# =============================================================================


@pytest.mark.unit
class TestRenderFormHtml:
    """Tests for render_form_html function."""

    def test_render_basic_form(self, simple_form):
        """Test rendering basic form."""
        html = render_form_html(simple_form)

        assert '<form id="test-form-001"' in html
        assert 'action="/api/socratic/submit"' in html
        assert "Test Form" in html

    def test_render_custom_action_url(self, simple_form):
        """Test custom action URL."""
        html = render_form_html(simple_form, action_url="/custom/submit")

        assert 'action="/custom/submit"' in html

    def test_render_progress_bar(self, simple_form):
        """Test progress bar rendering."""
        html = render_form_html(simple_form)

        assert 'class="progress-bar"' in html
        # Progress renders as 50.0% (with decimal)
        assert 'style="width: 50' in html
        assert "50%" in html

    def test_render_text_field(self, simple_form):
        """Test text input field rendering."""
        html = render_form_html(simple_form)

        assert 'type="text"' in html
        assert 'id="name"' in html
        assert 'name="name"' in html
        assert 'placeholder="Enter your name"' in html

    def test_render_required_indicator(self, simple_form):
        """Test required field indicator."""
        html = render_form_html(simple_form)

        assert 'class="required"' in html

    def test_render_multi_select(self, complex_form):
        """Test multi-select (checkbox) rendering."""
        html = render_form_html(complex_form)

        assert 'class="checkbox-group"' in html
        assert 'type="checkbox"' in html
        assert 'value="python"' in html

    def test_render_single_select(self, complex_form):
        """Test single-select (radio) rendering."""
        html = render_form_html(complex_form)

        assert 'class="radio-group"' in html
        assert 'type="radio"' in html

    def test_render_textarea(self, complex_form):
        """Test textarea rendering."""
        html = render_form_html(complex_form)

        assert "<textarea" in html
        assert 'maxlength="1000"' in html

    def test_render_boolean(self, complex_form):
        """Test boolean/switch rendering."""
        html = render_form_html(complex_form)

        assert 'class="switch"' in html
        assert 'class="slider"' in html

    def test_render_slider(self):
        """Test slider rendering."""
        # Create a simple form with just a slider (no categories to avoid filtering)
        slider_form = Form(
            id="slider-form",
            title="Slider Form",
            description="Test slider",
            fields=[
                FormField(
                    id="priority",
                    field_type=FieldType.SLIDER,
                    label="Priority",
                    validation=FieldValidation(min_value=1, max_value=10),
                ),
            ],
            round_number=1,
            progress=0.5,
        )
        html = render_form_html(slider_form)

        assert 'type="range"' in html
        assert 'min="1"' in html
        assert 'max="10"' in html

    def test_render_show_when_emits_data_attribute_when_field_visible(self):
        """A field with show_when that's satisfied gets a data-show-when attribute (line 79)."""
        # show_when={"x": None} matches against missing answers (None == None)
        # so the field passes the visibility filter and reaches _render_field_html
        # with show_when truthy.
        sw_form = Form(
            id="sw-form",
            title="SW",
            description="d",
            fields=[
                FormField(
                    id="visible_with_sw",
                    field_type=FieldType.TEXT,
                    label="Visible",
                    show_when={"some_other_field": None},
                ),
            ],
            round_number=1,
            progress=0.0,
        )
        html = render_form_html(sw_form)
        assert "data-show-when=" in html

    def test_render_field_directly_with_option_description(self):
        """_render_field_html called via render_form on a field with options + descriptions
        emits the option-desc span (line 100)."""
        # complex_form already covers test_render_option_description; ensure the
        # specific span class appears.
        from attune.socratic.forms import FieldOption

        opt_form = Form(
            id="opt",
            title="opt",
            description="d",
            fields=[
                FormField(
                    id="lang",
                    field_type=FieldType.SINGLE_SELECT,
                    label="Lang",
                    options=[
                        FieldOption(value="py", label="Python", description="for backend"),
                    ],
                ),
            ],
            round_number=1,
            progress=0.0,
        )
        html = render_form_html(opt_form)
        assert 'class="option-desc"' in html

    def test_render_show_when_filters_hidden_fields(self):
        """Test that fields with unsatisfied show_when are filtered out.

        Note: The form.get_fields_by_category() filters out fields whose
        show_when conditions are not met. This is by design - the client
        handles conditional visibility via JavaScript.
        """
        # Create a simple form with show_when
        show_when_form = Form(
            id="show-when-form",
            title="Show When Form",
            description="Test show_when",
            fields=[
                FormField(
                    id="toggle",
                    field_type=FieldType.BOOLEAN,
                    label="Enable",
                ),
                FormField(
                    id="conditional",
                    field_type=FieldType.TEXT,
                    label="Conditional Field",
                    show_when={"toggle": True},
                ),
            ],
            round_number=1,
            progress=0.5,
        )
        html = render_form_html(show_when_form)

        # Toggle field is visible (no show_when condition)
        assert 'data-field-id="toggle"' in html
        # Conditional field is filtered out (show_when condition not met)
        assert 'data-field-id="conditional"' not in html

    def test_render_recommended_option(self, complex_form):
        """Test recommended option styling."""
        html = render_form_html(complex_form)

        assert "recommended" in html

    def test_render_option_description(self, complex_form):
        """Test option description rendering."""
        html = render_form_html(complex_form)

        assert "Frontend" in html  # Description for JavaScript

    def test_render_help_text(self, complex_form):
        """Test help text rendering."""
        html = render_form_html(complex_form)

        assert 'class="help-text"' in html
        assert "Select all that apply" in html

    def test_render_categories_as_fieldsets(self, complex_form):
        """Test category grouping."""
        html = render_form_html(complex_form)

        assert "<fieldset" in html
        assert "<legend>" in html
        assert 'data-category="technical"' in html

    def test_render_submit_button(self, simple_form):
        """Test submit button rendering."""
        html = render_form_html(simple_form)

        assert 'type="submit"' in html
        assert 'class="btn-primary"' in html
        assert "Continue" in html


# =============================================================================
# API RESPONSE TESTS
# =============================================================================


@pytest.mark.unit
class TestAPIResponse:
    """Tests for APIResponse dataclass."""

    def test_success_response(self):
        """Test successful response."""
        response = APIResponse(
            success=True,
            data={"key": "value"},
            next_action="continue",
        )

        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.error is None
        assert response.next_action == "continue"

    def test_error_response(self):
        """Test error response."""
        response = APIResponse(
            success=False,
            error="Something went wrong",
        )

        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.data is None

    def test_to_json(self):
        """Test JSON serialization."""
        response = APIResponse(
            success=True,
            data={"message": "OK"},
            next_action="generate",
        )

        json_str = response.to_json()
        parsed = json.loads(json_str)

        assert parsed["success"] is True
        assert parsed["data"]["message"] == "OK"
        assert parsed["next_action"] == "generate"


# =============================================================================
# CREATE FORM RESPONSE TESTS
# =============================================================================


@pytest.mark.unit
class TestCreateFormResponse:
    """Tests for create_form_response function."""

    def test_create_response_with_form(self, mock_session, simple_form):
        """Test creating response with form."""
        builder = MagicMock()

        response = create_form_response(mock_session, simple_form, builder)

        assert response.success is True
        assert response.next_action == "continue"
        assert "session" in response.data
        assert "form" in response.data

    def test_create_response_ready_to_generate(self, mock_session):
        """Test response when ready to generate."""
        builder = MagicMock()
        builder.is_ready_to_generate.return_value = True

        response = create_form_response(mock_session, None, builder)

        assert response.success is True
        assert response.next_action == "generate"
        assert "message" in response.data

    def test_create_response_error(self, mock_session):
        """Test error response when neither form nor ready."""
        builder = MagicMock()
        builder.is_ready_to_generate.return_value = False

        response = create_form_response(mock_session, None, builder)

        assert response.success is False
        assert response.error is not None


# =============================================================================
# CREATE BLUEPRINT RESPONSE TESTS
# =============================================================================


@pytest.mark.unit
class TestCreateBlueprintResponse:
    """Tests for create_blueprint_response function."""

    def test_create_blueprint_response(self, mock_blueprint, mock_session):
        """Test creating blueprint response."""
        response = create_blueprint_response(mock_blueprint, mock_session)

        assert response.success is True
        assert response.next_action == "complete"
        assert "session" in response.data
        assert "blueprint" in response.data

    def test_blueprint_response_contains_schema(self, mock_blueprint, mock_session):
        """Test blueprint data contains expected fields."""
        response = create_blueprint_response(mock_blueprint, mock_session)

        blueprint_data = response.data["blueprint"]
        assert "id" in blueprint_data
        assert "name" in blueprint_data
        assert "agents" in blueprint_data


# =============================================================================
# GET FORM ASSETS TESTS
# =============================================================================


@pytest.mark.unit
class TestGetFormAssets:
    """Tests for get_form_assets function."""

    def test_returns_css_and_js(self):
        """Test assets contain CSS and JS."""
        assets = get_form_assets()

        assert "css" in assets
        assert "js" in assets

    def test_css_contains_styles(self):
        """Test CSS contains form styles."""
        assets = get_form_assets()

        assert ".socratic-form" in assets["css"]
        assert ".form-field" in assets["css"]
        assert ".btn-primary" in assets["css"]

    def test_js_contains_script(self):
        """Test JS contains SocraticForm class."""
        assets = get_form_assets()

        assert "SocraticForm" in assets["js"]
        assert "updateVisibility" in assets["js"]


# =============================================================================
# RENDER COMPLETE PAGE TESTS
# =============================================================================


@pytest.mark.unit
class TestRenderCompletePage:
    """Tests for render_complete_page function."""

    def test_render_complete_page(self, simple_form, mock_session):
        """Test rendering complete HTML page."""
        html = render_complete_page(simple_form, mock_session)

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_page_contains_css(self, simple_form, mock_session):
        """Test page includes CSS."""
        html = render_complete_page(simple_form, mock_session)

        assert "<style>" in html
        assert ".socratic-form" in html

    def test_page_contains_js(self, simple_form, mock_session):
        """Test page includes JavaScript."""
        html = render_complete_page(simple_form, mock_session)

        assert "<script>" in html
        assert "SocraticForm" in html

    def test_page_contains_form(self, simple_form, mock_session):
        """Test page includes form."""
        html = render_complete_page(simple_form, mock_session)

        assert '<form id="test-form-001"' in html

    def test_page_contains_session_data(self, simple_form, mock_session):
        """Test page includes session data."""
        html = render_complete_page(simple_form, mock_session)

        assert "window.socraticSession" in html
        assert "code_review" in html

    def test_page_contains_domain_badge(self, simple_form, mock_session):
        """Test page shows domain badge."""
        html = render_complete_page(simple_form, mock_session)

        assert 'class="domain-badge"' in html
        assert "code_review" in html

    def test_page_contains_confidence(self, simple_form, mock_session):
        """Test page shows confidence."""
        html = render_complete_page(simple_form, mock_session)

        assert 'class="confidence"' in html
        assert "85%" in html


# =============================================================================
# CONSTANTS TESTS
# =============================================================================


@pytest.mark.unit
class TestFormConstants:
    """Tests for CSS and JS constants."""

    def test_form_css_not_empty(self):
        """Test FORM_CSS is defined."""
        assert len(FORM_CSS) > 0
        assert ".socratic-form" in FORM_CSS

    def test_form_js_not_empty(self):
        """Test FORM_JS is defined."""
        assert len(FORM_JS) > 0
        assert "class SocraticForm" in FORM_JS

    def test_css_contains_responsive_styles(self):
        """Test CSS includes responsive max-width."""
        assert "max-width" in FORM_CSS

    def test_js_handles_form_submission(self):
        """Test JS includes submission handling."""
        assert "submitSocraticForm" in FORM_JS

    def test_js_handles_visibility(self):
        """Test JS includes visibility handling."""
        assert "updateVisibility" in FORM_JS
        assert "evaluateCondition" in FORM_JS
