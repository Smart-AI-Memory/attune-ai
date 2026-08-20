"""Tests for form_to_elicitation_schema — artifact → MCP requestedSchema.

Covers every QuestionType mapping plus title/description/default/required
threading. The lead v2 surface (D8) consumes this schema via
``ServerSession.elicit_form``.
"""

from __future__ import annotations

from attune.elicitation import form_from_dict, form_to_elicitation_schema


def _schema(field: dict) -> dict:
    form = form_from_dict({"title": "T", "fields": [field]})
    return form_to_elicitation_schema(form)


def _prop(field: dict) -> dict:
    return _schema(field)["properties"][field["id"]]


class TestTypeMapping:
    def test_single_select(self):
        p = _prop({"id": "g", "text": "Goal", "type": "single_select", "options": ["a", "b"]})
        assert p == {"title": "Goal", "type": "string", "enum": ["a", "b"]}

    def test_multi_select_required_sets_min_items(self):
        p = _prop({"id": "f", "text": "Focus", "type": "multi_select", "options": ["x", "y"]})
        assert p["type"] == "array"
        assert p["items"] == {"type": "string", "enum": ["x", "y"]}
        assert p["minItems"] == 1

    def test_multi_select_optional_no_min_items(self):
        p = _prop(
            {
                "id": "f",
                "text": "Focus",
                "type": "multi_select",
                "options": ["x", "y"],
                "required": False,
            }
        )
        assert "minItems" not in p

    def test_boolean(self):
        # forms 0.7.0 (#46): boolean projects to a two-value string enum,
        # not a JSON boolean — the validator accepts only "Yes"/"No" and
        # every surface renders those.
        p = _prop({"id": "b", "text": "Ship?", "type": "boolean"})
        assert p == {"title": "Ship?", "type": "string", "enum": ["Yes", "No"]}

    def test_number_with_bounds(self):
        p = _prop({"id": "n", "text": "Age", "type": "number", "minimum": 0, "maximum": 120})
        assert p == {"title": "Age", "type": "number", "minimum": 0, "maximum": 120}

    def test_number_without_bounds(self):
        p = _prop({"id": "n", "text": "Age", "type": "number"})
        assert p == {"title": "Age", "type": "number"}

    def test_date(self):
        p = _prop({"id": "d", "text": "When", "type": "date"})
        assert p == {"title": "When", "type": "string", "format": "date"}

    def test_textarea_with_max_length(self):
        p = _prop({"id": "t", "text": "Bio", "type": "textarea", "max_length": 280})
        assert p == {"title": "Bio", "type": "string", "maxLength": 280}

    def test_text_input_without_max_length(self):
        p = _prop({"id": "t", "text": "Name", "type": "text_input"})
        assert p == {"title": "Name", "type": "string"}


class TestSchemaShape:
    def test_help_text_becomes_description(self):
        p = _prop({"id": "n", "text": "Age", "type": "number", "help_text": "Years since birth"})
        assert p["description"] == "Years since birth"

    def test_default_threaded(self):
        p = _prop(
            {"id": "g", "text": "Goal", "type": "single_select", "options": ["a"], "default": "a"}
        )
        assert p["default"] == "a"

    def test_object_shape_and_required_list(self):
        form = form_from_dict(
            {
                "title": "T",
                "fields": [
                    {"id": "req", "text": "R", "type": "text_input"},
                    {"id": "opt", "text": "O", "type": "text_input", "required": False},
                ],
            }
        )
        schema = form_to_elicitation_schema(form)
        assert schema["type"] == "object"
        assert set(schema["properties"]) == {"req", "opt"}
        assert schema["required"] == ["req"]
