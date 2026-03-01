"""Tests for the Socratic MCP server module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json

import pytest


@pytest.fixture(autouse=True)
def _no_anthropic_key(monkeypatch):
    """Prevent real API calls by removing the Anthropic key."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


class TestSocraticMCPServer:
    """Tests for SocraticMCPServer class."""

    def test_create_server(self):
        """Test creating an MCP server."""
        from attune.socratic.mcp_server import SocraticMCPServer

        # Constructor takes no arguments
        server = SocraticMCPServer()
        assert server is not None

    @pytest.mark.asyncio
    async def test_start_session_tool(self):
        """Test socratic_start_session tool."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()

        # Use handle_tool_call (async method)
        result = await server.handle_tool_call("socratic_start_session", {})

        assert "session_id" in result
        assert "state" in result

    @pytest.mark.asyncio
    async def test_set_goal_tool(self):
        """Test socratic_set_goal tool."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()

        # First start a session
        session_result = await server.handle_tool_call("socratic_start_session", {})
        session_id = session_result["session_id"]

        # Set goal
        result = await server.handle_tool_call(
            "socratic_set_goal",
            {
                "session_id": session_id,
                "goal": "Automate code reviews for Python projects",
            },
        )

        assert result["session_id"] == session_id
        assert "state" in result

    @pytest.mark.asyncio
    async def test_get_questions_tool(self):
        """Test socratic_get_questions tool."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()

        # Start session and set goal
        session_result = await server.handle_tool_call("socratic_start_session", {})
        session_id = session_result["session_id"]

        await server.handle_tool_call(
            "socratic_set_goal",
            {
                "session_id": session_id,
                "goal": "Automate code reviews",
            },
        )

        # Get questions
        result = await server.handle_tool_call(
            "socratic_get_questions",
            {"session_id": session_id},
        )

        assert "questions" in result or "form" in result or "fields" in result or "state" in result

    @pytest.mark.asyncio
    async def test_submit_answers_tool(self):
        """Test socratic_submit_answers tool."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()

        # Setup session
        session_result = await server.handle_tool_call("socratic_start_session", {})
        session_id = session_result["session_id"]

        await server.handle_tool_call(
            "socratic_set_goal",
            {
                "session_id": session_id,
                "goal": "Automate code reviews",
            },
        )

        # Submit answers
        result = await server.handle_tool_call(
            "socratic_submit_answers",
            {
                "session_id": session_id,
                "answers": {"languages": ["python"], "focus_areas": ["security"]},
            },
        )

        assert "session_id" in result

    @pytest.mark.asyncio
    async def test_list_sessions_tool(self):
        """Test socratic_list_sessions tool."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()

        # Create some sessions
        await server.handle_tool_call("socratic_start_session", {})
        await server.handle_tool_call("socratic_start_session", {})

        result = await server.handle_tool_call("socratic_list_sessions", {})

        assert "sessions" in result
        assert len(result["sessions"]) >= 2

    @pytest.mark.asyncio
    async def test_get_session_tool(self):
        """Test socratic_get_session tool."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()

        # Create session
        session_result = await server.handle_tool_call("socratic_start_session", {})
        session_id = session_result["session_id"]

        # Get session
        result = await server.handle_tool_call(
            "socratic_get_session",
            {"session_id": session_id},
        )

        assert result["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_invalid_tool_call(self):
        """Test calling non-existent tool."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()

        # Unknown tool returns error dict, doesn't raise
        result = await server.handle_tool_call("non_existent_tool", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_tool_with_invalid_session(self):
        """Test tool with invalid session ID."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()

        # Returns error dict for invalid session
        result = await server.handle_tool_call(
            "socratic_get_session",
            {"session_id": "non-existent-id"},
        )
        assert "error" in result


class TestSocraticTools:
    """Tests for SOCRATIC_TOOLS constant."""

    def test_tools_defined(self):
        """Test that SOCRATIC_TOOLS is defined."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        assert SOCRATIC_TOOLS is not None
        assert isinstance(SOCRATIC_TOOLS, list)

    def test_tools_have_required_fields(self):
        """Test that all tools have required fields."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        for tool in SOCRATIC_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_expected_tools_exist(self):
        """Test that expected tools exist."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool_names = [t["name"] for t in SOCRATIC_TOOLS]

        expected = [
            "socratic_start_session",
            "socratic_set_goal",
            "socratic_get_questions",
            "socratic_submit_answers",
            "socratic_generate_workflow",
        ]

        for expected_tool in expected:
            assert expected_tool in tool_names, f"Missing tool: {expected_tool}"


class TestMCPServerAsync:
    """Tests for async MCP server methods."""

    @pytest.mark.asyncio
    async def test_async_handle_tool_call(self):
        """Test async handle_tool_call."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()

        result = await server.handle_tool_call("socratic_start_session", {})
        assert "session_id" in result

    @pytest.mark.asyncio
    async def test_ensure_initialized(self):
        """Test lazy initialization."""
        from attune.socratic.mcp_server import SocraticMCPServer

        server = SocraticMCPServer()
        assert server._initialized is False

        # First tool call triggers initialization
        await server.handle_tool_call("socratic_start_session", {})
        assert server._initialized is True


class TestMCPToolSchemas:
    """Tests for MCP tool input schemas."""

    def test_start_session_schema(self):
        """Test socratic_start_session schema."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool = next(t for t in SOCRATIC_TOOLS if t["name"] == "socratic_start_session")
        schema = tool["inputSchema"]

        assert schema["type"] == "object"
        # Should have no required fields (empty list)
        assert schema.get("required", []) == []

    def test_set_goal_schema(self):
        """Test socratic_set_goal schema."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool = next(t for t in SOCRATIC_TOOLS if t["name"] == "socratic_set_goal")
        schema = tool["inputSchema"]

        assert "session_id" in schema["properties"]
        assert "goal" in schema["properties"]
        assert "session_id" in schema.get("required", [])
        assert "goal" in schema.get("required", [])

    def test_schema_valid_json(self):
        """Test all schemas are valid JSON."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        for tool in SOCRATIC_TOOLS:
            # Should be JSON serializable
            json_str = json.dumps(tool)
            parsed = json.loads(json_str)
            assert parsed == tool

    def test_get_questions_schema(self):
        """Test socratic_get_questions schema."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool = next(t for t in SOCRATIC_TOOLS if t["name"] == "socratic_get_questions")
        schema = tool["inputSchema"]

        assert "session_id" in schema["properties"]
        assert "session_id" in schema.get("required", [])

    def test_submit_answers_schema(self):
        """Test socratic_submit_answers schema."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool = next(t for t in SOCRATIC_TOOLS if t["name"] == "socratic_submit_answers")
        schema = tool["inputSchema"]

        assert "session_id" in schema["properties"]
        assert "answers" in schema["properties"]
        assert "session_id" in schema.get("required", [])
        assert "answers" in schema.get("required", [])

    def test_generate_workflow_schema(self):
        """Test socratic_generate_workflow schema."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool = next(t for t in SOCRATIC_TOOLS if t["name"] == "socratic_generate_workflow")
        schema = tool["inputSchema"]

        assert "session_id" in schema["properties"]
        assert "session_id" in schema.get("required", [])


class TestMCPToolsList:
    """Tests for additional tools in SOCRATIC_TOOLS."""

    def test_list_sessions_tool_exists(self):
        """Test socratic_list_sessions tool exists."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool_names = [t["name"] for t in SOCRATIC_TOOLS]
        assert "socratic_list_sessions" in tool_names

    def test_get_session_tool_exists(self):
        """Test socratic_get_session tool exists."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool_names = [t["name"] for t in SOCRATIC_TOOLS]
        assert "socratic_get_session" in tool_names

    def test_list_blueprints_tool_exists(self):
        """Test socratic_list_blueprints tool exists."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool_names = [t["name"] for t in SOCRATIC_TOOLS]
        assert "socratic_list_blueprints" in tool_names

    def test_analyze_goal_tool_exists(self):
        """Test socratic_analyze_goal tool exists."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool_names = [t["name"] for t in SOCRATIC_TOOLS]
        assert "socratic_analyze_goal" in tool_names

    def test_recommend_agents_tool_exists(self):
        """Test socratic_recommend_agents tool exists."""
        from attune.socratic.mcp_server import SOCRATIC_TOOLS

        tool_names = [t["name"] for t in SOCRATIC_TOOLS]
        assert "socratic_recommend_agents" in tool_names
