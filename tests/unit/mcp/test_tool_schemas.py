"""Unit tests for attune.mcp.tool_schemas module.

Tests cover:
- _path_tool: schema builder with required/optional/custom params
- get_workflow_tools: all workflow tool schemas present and valid
- get_utility_tools: utility tool schemas present and valid
- get_help_tools: help tool schemas present and valid
- get_memory_tools: memory tool schemas present and valid
- get_resources: MCP resource definitions
- get_prompts: MCP prompt definitions

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from attune.mcp.tool_schemas import (
    _path_tool,
    get_elicitation_tools,
    get_help_tools,
    get_memory_tools,
    get_prompts,
    get_resources,
    get_utility_tools,
    get_workflow_tools,
)


def _field_types(tools: dict, name: str) -> list[str]:
    """Return the field-type enum for a tool's form schema."""
    items = tools[name]["input_schema"]["properties"]["form"]["properties"]["fields"]["items"]
    return items["properties"]["type"]["enum"]


# -- _path_tool ------------------------------------------------------


class TestPathTool:
    """Tests for _path_tool() schema builder."""

    def test_default_optional_path(self) -> None:
        """Builds schema with optional path param and default."""
        schema = _path_tool("My tool")
        assert schema["description"] == "My tool"
        props = schema["input_schema"]["properties"]
        assert "path" in props
        assert props["path"]["default"] == "."
        assert "required" not in schema["input_schema"]

    def test_required_path(self) -> None:
        """Marks path as required when required=True."""
        schema = _path_tool("Tool", required=True)
        assert schema["input_schema"]["required"] == ["path"]
        assert "default" not in schema["input_schema"]["properties"]["path"]

    def test_custom_param_name(self) -> None:
        """Uses custom param_name instead of 'path'."""
        schema = _path_tool("Tool", param_name="project_root")
        assert "project_root" in schema["input_schema"]["properties"]
        assert "path" not in schema["input_schema"]["properties"]

    def test_custom_param_desc(self) -> None:
        """Uses custom param_desc."""
        schema = _path_tool("Tool", param_desc="Custom desc")
        props = schema["input_schema"]["properties"]
        assert props["path"]["description"] == "Custom desc"

    def test_custom_default(self) -> None:
        """Uses custom default value."""
        schema = _path_tool("Tool", default="src/")
        props = schema["input_schema"]["properties"]
        assert props["path"]["default"] == "src/"

    def test_required_with_custom_param_name(self) -> None:
        """Required list uses custom param_name."""
        schema = _path_tool("Tool", param_name="dir", required=True)
        assert schema["input_schema"]["required"] == ["dir"]


# -- get_workflow_tools -----------------------------------------------


class TestGetWorkflowTools:
    """Tests for get_workflow_tools()."""

    def test_returns_dict(self) -> None:
        """Returns a non-empty dict."""
        tools = get_workflow_tools()
        assert isinstance(tools, dict)
        assert len(tools) > 0

    def test_all_tools_have_description(self) -> None:
        """Every tool has a description string."""
        for name, defn in get_workflow_tools().items():
            assert "description" in defn, f"{name} missing description"
            assert isinstance(defn["description"], str)

    def test_all_tools_have_input_schema(self) -> None:
        """Every tool has an input_schema dict."""
        for name, defn in get_workflow_tools().items():
            assert "input_schema" in defn, f"{name} missing input_schema"
            assert defn["input_schema"]["type"] == "object"

    def test_expected_tools_present(self) -> None:
        """Key workflow tools are registered."""
        tools = get_workflow_tools()
        expected = {
            "security_audit",
            "bug_predict",
            "code_review",
            "test_generation",
            "performance_audit",
            "release_notes",
            "deep_review",
        }
        assert expected.issubset(tools.keys())

    def test_discovery_sweep_present_with_required_path(self) -> None:
        """discovery_sweep is registered and requires only 'path'."""
        tools = get_workflow_tools()
        assert "discovery_sweep" in tools
        schema = tools["discovery_sweep"]["input_schema"]
        assert schema["required"] == ["path"]
        props = schema["properties"]
        assert "budget_usd" in props
        assert "no_llm" in props

    def test_doc_gen_does_not_advertise_dropped_params(self) -> None:
        """doc_type/audience were dropped in the v4.2.0 SDK migration; the
        schema must not advertise params the handler ignores."""
        schema = get_workflow_tools()["doc_gen"]["input_schema"]
        props = schema["properties"]
        assert "source_path" in props
        assert "doc_type" not in props
        assert "audience" not in props

    def test_test_generation_has_module_required(self) -> None:
        """test_generation requires 'module' param."""
        schema = get_workflow_tools()["test_generation"]["input_schema"]
        assert "module" in schema["required"]

    def test_research_synthesis_is_path_based(self) -> None:
        """research_synthesis takes optional path + depth (no required args).

        The workflow is a path-driven 3-agent pipeline; the tool must not
        require the legacy sources/question contract.
        """
        schema = get_workflow_tools()["research_synthesis"]["input_schema"]
        props = schema["properties"]
        assert "path" in props
        assert "depth" in props
        assert props["depth"]["enum"] == ["quick", "standard", "deep"]
        assert "required" not in schema
        assert "sources" not in props
        assert "question" not in props


# -- get_utility_tools ------------------------------------------------


class TestGetUtilityTools:
    """Tests for get_utility_tools()."""

    def test_returns_dict(self) -> None:
        tools = get_utility_tools()
        assert isinstance(tools, dict)

    def test_expected_tools_present(self) -> None:
        tools = get_utility_tools()
        expected = {
            "auth_status",
            "auth_recommend",
            "telemetry_stats",
            "context_get",
            "context_set",
            "list_capabilities",
        }
        assert expected == set(tools.keys())

    def test_context_set_requires_key_and_value(self) -> None:
        schema = get_utility_tools()["context_set"]["input_schema"]
        assert set(schema["required"]) == {"key", "value"}


# -- get_help_tools ---------------------------------------------------


class TestGetHelpTools:
    """Tests for get_help_tools()."""

    def test_returns_dict(self) -> None:
        tools = get_help_tools()
        assert isinstance(tools, dict)

    def test_expected_tools_present(self) -> None:
        tools = get_help_tools()
        expected = {
            "help_lookup",
            "help_maintain",
            "help_init",
            "help_status",
            "help_update",
        }
        assert expected == set(tools.keys())

    def test_help_lookup_requires_topic(self) -> None:
        schema = get_help_tools()["help_lookup"]["input_schema"]
        assert "topic" in schema["required"]

    def test_help_init_requires_action(self) -> None:
        schema = get_help_tools()["help_init"]["input_schema"]
        assert "action" in schema["required"]

    def test_help_lookup_mode_enum(self) -> None:
        """Mode param has correct enum values."""
        props = get_help_tools()["help_lookup"]["input_schema"]["properties"]
        assert "mode" in props
        assert "progressive" in props["mode"]["enum"]
        assert "preamble" in props["mode"]["enum"]


# -- get_memory_tools -------------------------------------------------


class TestGetMemoryTools:
    """Tests for get_memory_tools()."""

    def test_returns_dict(self) -> None:
        tools = get_memory_tools()
        assert isinstance(tools, dict)

    def test_expected_tools_present(self) -> None:
        tools = get_memory_tools()
        expected = {
            "memory_store",
            "memory_retrieve",
            "memory_search",
            "memory_forget",
        }
        assert expected == set(tools.keys())

    def test_memory_store_requires_key_and_value(self) -> None:
        schema = get_memory_tools()["memory_store"]["input_schema"]
        assert set(schema["required"]) == {"key", "value"}

    def test_memory_store_classification_enum(self) -> None:
        props = get_memory_tools()["memory_store"]["input_schema"]["properties"]
        assert set(props["classification"]["enum"]) == {
            "PUBLIC",
            "INTERNAL",
            "SENSITIVE",
        }

    def test_memory_forget_scope_enum(self) -> None:
        props = get_memory_tools()["memory_forget"]["input_schema"]["properties"]
        assert set(props["scope"]["enum"]) == {"session", "persistent", "all"}


# -- get_resources ----------------------------------------------------


class TestGetResources:
    """Tests for get_resources()."""

    def test_returns_dict(self) -> None:
        resources = get_resources()
        assert isinstance(resources, dict)

    def test_all_resources_have_uri(self) -> None:
        for name, defn in get_resources().items():
            assert "uri" in defn, f"{name} missing uri"
            assert defn["uri"].startswith("attune://")

    def test_all_resources_have_name(self) -> None:
        for name, defn in get_resources().items():
            assert "name" in defn, f"{name} missing name"

    def test_expected_resources_present(self) -> None:
        resources = get_resources()
        assert {"workflows", "auth_config", "telemetry"} == set(resources.keys())


# -- get_prompts ------------------------------------------------------


class TestGetPrompts:
    """Tests for get_prompts()."""

    def test_returns_dict(self) -> None:
        prompts = get_prompts()
        assert isinstance(prompts, dict)

    def test_expected_prompts_present(self) -> None:
        prompts = get_prompts()
        assert {"security-scan", "test-gen", "cost-report"} == set(prompts.keys())

    def test_all_prompts_have_name_and_description(self) -> None:
        for key, defn in get_prompts().items():
            assert "name" in defn, f"{key} missing name"
            assert "description" in defn, f"{key} missing description"

    def test_security_scan_has_required_path(self) -> None:
        prompt = get_prompts()["security-scan"]
        required_args = [a for a in prompt["arguments"] if a.get("required")]
        assert len(required_args) == 1
        assert required_args[0]["name"] == "path"

    def test_test_gen_has_optional_batch(self) -> None:
        prompt = get_prompts()["test-gen"]
        batch_arg = next(a for a in prompt["arguments"] if a["name"] == "batch")
        assert batch_arg.get("required") is False


# -- get_elicitation_tools -------------------------------------------


class TestGetElicitationTools:
    """Field-type enum surfaces: v2 rich tools mirror the library, v1 stays at 4.

    The v2 rich field/form schema is SOURCED FROM
    ``attune_forms.mcp_server`` (not hand-declared), so these tests pin
    that mirror against the library — the D3 drift guard that retired
    the recurring hand-sync obligation (forms 0.7.0). A forms release
    that grows the field contract flows through automatically; a
    regression that severs the wiring (someone re-hand-declares the
    schema) fails here loudly.
    """

    def test_v2_tools_present(self) -> None:
        tools = get_elicitation_tools()
        assert "elicitation_render_widget" in tools
        assert "elicitation_ask" in tools

    def test_v1_render_form_stays_four_types(self) -> None:
        # AskUserQuestion has no native number/date — v1 must NOT claim them.
        assert _field_types(get_elicitation_tools(), "elicitation_render_form") == [
            "text_input",
            "single_select",
            "multi_select",
            "boolean",
        ]

    def test_v2_rich_schema_is_sourced_from_forms(self) -> None:
        # D3 drift guard: the v2 rich field+form schema is the library's,
        # verbatim. The rich tools (render_widget, ask, collect_response)
        # all embed it; if any drifts from attune_forms, this fails.
        from attune_forms.mcp_server import _field_schema, _form_schema

        lib_field = _field_schema()
        lib_form = _form_schema()
        tools = get_elicitation_tools()
        for name in (
            "elicitation_render_widget",
            "elicitation_ask",
            "elicitation_collect_response",
        ):
            form = tools[name]["input_schema"]["properties"]["form"]
            assert form == lib_form, f"{name} form schema drifted from attune_forms"
            assert form["properties"]["fields"]["items"] == lib_field

    def test_v2_absorbs_forms_070_field_contract(self) -> None:
        # Regression guard for the forms 0.7.0 sync: the mirror must carry
        # the 0.7.0 additions (would fail against the old hand-declared
        # schema or a pre-0.7.0 library floor).
        items = get_elicitation_tools()["elicitation_render_widget"]["input_schema"]["properties"][
            "form"
        ]["properties"]["fields"]["items"]
        props = items["properties"]
        # additionalProperties: false on the field object (forms #50).
        assert items["additionalProperties"] is False
        # Multi-type `default` incl. object (triage dict) — forms #42/#47.
        assert "object" in props["default"]["type"]
        # `inferred_from` declared alongside `default` (forms #40).
        assert "inferred_from" in props
        # Typed object-array extras (forms #52 F5).
        for key in ("progress_items", "triage_items", "consequences", "assumptions"):
            assert props[key]["items"] == {"type": "object"}, key

    def test_v2_form_object_is_strict(self) -> None:
        # additionalProperties: false on the form object too (forms #50).
        tools = get_elicitation_tools()
        for name in ("elicitation_render_widget", "elicitation_ask"):
            form = tools[name]["input_schema"]["properties"]["form"]
            assert form["additionalProperties"] is False

    def test_v1_schema_is_strict(self) -> None:
        # v1 is hand-declared but must match form_from_dict's strict
        # definition contract — an unknown key is a typo, not extra data.
        form = get_elicitation_tools()["elicitation_render_form"]["input_schema"]["properties"][
            "form"
        ]
        assert form["additionalProperties"] is False
        assert form["properties"]["fields"]["items"]["additionalProperties"] is False

    def test_v2_field_schema_has_numeric_bounds(self) -> None:
        tools = get_elicitation_tools()
        items = tools["elicitation_render_widget"]["input_schema"]["properties"]["form"][
            "properties"
        ]["fields"]["items"]["properties"]
        assert "minimum" in items
        assert "maximum" in items
        assert "max_length" in items
