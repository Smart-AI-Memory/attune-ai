"""Wiring consistency tests.

Verify that every registered name (tool, workflow, keyword, entry point)
resolves to something real.  These are pure structural checks — no
execution, no mocks, no I/O.
"""

import importlib
import importlib.metadata
import inspect
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# 2. Empathy MCP: every registered tool has a dispatch branch
# ---------------------------------------------------------------------------


class TestEmpathyMCPWiring:
    """Every key in _register_tools() must have an if/elif branch in call_tool()."""

    def _registered_tools(self) -> set[str]:
        from attune.mcp.server import AttuneMCPServer

        # Instantiate a lightweight server and inspect the registered tools dict
        server = AttuneMCPServer.__new__(AttuneMCPServer)
        server._memory = None
        server._attune_level = 3
        server._context = {}
        server._plugin_handlers = {}
        return set(server._register_tools().keys())

    def _dispatched_tools(self) -> set[str]:
        from attune.mcp.server import AttuneMCPServer

        # _build_dispatch_table returns {tool_name: handler}
        server = AttuneMCPServer.__new__(AttuneMCPServer)
        server._memory = None
        server._attune_level = 3
        server._context = {}
        server._plugin_handlers = {}
        table = server._build_dispatch_table()
        return set(table.keys())

    def test_every_registered_tool_has_dispatch(self):
        registered = self._registered_tools()
        dispatched = self._dispatched_tools()
        missing = registered - dispatched
        assert not missing, f"Tools registered but not dispatched in call_tool(): {missing}"

    def test_every_dispatched_tool_is_registered(self):
        registered = self._registered_tools()
        dispatched = self._dispatched_tools()
        extra = dispatched - registered
        assert not extra, f"Tools dispatched in call_tool() but not registered: {extra}"

    def test_sets_are_equal(self):
        assert self._registered_tools() == self._dispatched_tools()


# ---------------------------------------------------------------------------
# 3. Workflow registry: every default name resolves
# ---------------------------------------------------------------------------


class TestWorkflowRegistryWiring:
    """Every _DEFAULT_WORKFLOW_NAMES class must exist in _LAZY_WORKFLOW_IMPORTS,
    and every referenced module must be importable.
    """

    def test_every_default_name_in_lazy_imports(self):
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES, _LAZY_WORKFLOW_IMPORTS

        for workflow_id, class_name in _DEFAULT_WORKFLOW_NAMES.items():
            assert class_name in _LAZY_WORKFLOW_IMPORTS, (
                f"Workflow '{workflow_id}' references class '{class_name}' "
                f"which is missing from _LAZY_WORKFLOW_IMPORTS"
            )

    def test_lazy_import_modules_are_importable(self):
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES, _LAZY_WORKFLOW_IMPORTS

        # Only check modules referenced by default workflows (keeps it fast)
        checked_classes = set(_DEFAULT_WORKFLOW_NAMES.values())
        for class_name in checked_classes:
            module_path, attr_name = _LAZY_WORKFLOW_IMPORTS[class_name]
            # Resolve relative imports against attune.workflows
            if module_path.startswith("."):
                full_module = "attune.workflows" + module_path
            else:
                full_module = module_path
            mod = importlib.import_module(full_module)
            assert hasattr(mod, attr_name), (
                f"Module '{full_module}' has no attribute '{attr_name}' "
                f"(referenced by class '{class_name}')"
            )


# ---------------------------------------------------------------------------
# 4. Entry points: every pyproject.toml workflow entry point is importable
# ---------------------------------------------------------------------------


class TestWorkflowEntryPoints:
    """Any attune.workflows entry point present must load and have execute.

    attune's own built-ins are deliberately NOT registered as entry
    points (they stay lazy via ``_DEFAULT_WORKFLOW_NAMES``; see the
    pyproject NOTE and #2238) — the group is for third-party packages,
    so an empty group is a valid state. A stale editable install may
    still carry the retired block's entries; when any entry exists it
    must still load correctly.
    """

    def test_workflow_entry_points_are_loadable(self):
        eps = list(importlib.metadata.entry_points(group="attune.workflows"))

        for ep in eps:
            cls = ep.load()
            assert isinstance(
                cls, type
            ), f"Entry point '{ep.name}' did not load a class (got {type(cls).__name__})"
            assert hasattr(
                cls, "execute"
            ), f"Entry point '{ep.name}' loaded {cls.__name__} which has no execute method"

    def test_builtin_workflows_stay_out_of_entry_points(self):
        """The retired built-in block must not re-enter pyproject (#2238)."""
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        headers = [
            line.strip()
            for line in pyproject.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        ]
        assert '[project.entry-points."attune.workflows"]' not in headers, (
            "attune's built-ins are lazy via _DEFAULT_WORKFLOW_NAMES; "
            "registering them as attune.workflows entry points makes "
            "discover_workflows() import them eagerly"
        )


# ---------------------------------------------------------------------------
# 5. CLI router: every keyword maps to a known hub
# ---------------------------------------------------------------------------


class TestCLIRouterWiring:
    """Every skill referenced by _keyword_to_skill must be a known hub."""

    KNOWN_HUBS = {
        "dev",
        "testing",
        "workflows",
        "docs",
        "plan",
        "release",
        "wizard",
        "agent",
        "batch",
        "bulk",
        "pipeline",
        "utilities",
        "brainstorm",
    }

    def test_every_keyword_maps_to_known_hub(self):
        from attune.cli_router import HybridRouter

        router = HybridRouter.__new__(HybridRouter)
        # Manually init the mapping without triggering file I/O
        router._keyword_to_skill = {}
        # Re-read from source to get the mapping without side effects
        source = inspect.getsource(HybridRouter.__init__)
        # Extract (skill, args) pairs: ("skill_name", "args")
        skills_referenced = set(re.findall(r'\("(\w+)"(?:,\s*"[^"]*")?\)', source))
        unknown = skills_referenced - self.KNOWN_HUBS
        assert not unknown, (
            f"Keywords reference unknown hubs: {unknown}. " f"Known hubs: {sorted(self.KNOWN_HUBS)}"
        )

    def test_hub_descriptions_cover_all_skills(self):
        """_hub_descriptions should document every hub used in _keyword_to_skill."""
        from attune.cli_router import HybridRouter

        source_init = inspect.getsource(HybridRouter.__init__)

        # Extract skills from _keyword_to_skill assignments
        skills_used = set(re.findall(r'\("(\w+)"(?:,\s*"[^"]*")?\)', source_init))

        # Extract keys from _hub_descriptions
        hub_desc_keys = (
            set(re.findall(r'"(\w+)":\s*"[^"]*"', source_init.split("_hub_descriptions")[1]))
            if "_hub_descriptions" in source_init
            else set()
        )

        undocumented = skills_used - hub_desc_keys
        assert not undocumented, (
            f"Hubs used in _keyword_to_skill but missing from _hub_descriptions: " f"{undocumented}"
        )


# ---------------------------------------------------------------------------
# 6. Wizard entry points: every wizard is importable
# ---------------------------------------------------------------------------


class TestWizardEntryPoints:
    """Every attune.wizards entry point must load successfully."""

    def test_wizard_entry_points_are_loadable(self):
        eps = list(importlib.metadata.entry_points(group="attune.wizards"))
        assert eps, "No attune.wizards entry points found — is the package installed?"

        for ep in eps:
            cls = ep.load()
            assert isinstance(cls, type), (
                f"Wizard entry point '{ep.name}' did not load a class "
                f"(got {type(cls).__name__})"
            )
