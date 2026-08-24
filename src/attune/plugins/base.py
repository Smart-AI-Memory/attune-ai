"""Attune AI - Plugin System Base Classes

This module provides the core abstractions for creating domain-specific plugins
that extend the Attune AI.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata about a plugin"""

    name: str
    version: str
    domain: str
    description: str
    author: str
    license: str
    requires_core_version: str  # Minimum core framework version
    dependencies: list[str] | None = None  # Additional package dependencies


class BaseWorkflow(ABC):
    """Base class for plugin-contributed analysis workflows.

    .. deprecated:: 14.2
        This contract predates the engine's workflow runtime and is slated
        for replacement in 15.0.0 (#2238). The engine does NOT run
        ``analyze()``: workflows discovered via entry points must subclass
        :class:`attune.workflows.base.BaseWorkflow` (whose entry point is
        ``execute()``). Use this class only for plugin-internal analyzers
        invoked by your own plugin code.

    Design Philosophy:
    - Domain-agnostic: Works for software, healthcare, finance, etc.
    - Pattern-contributing: Workflows share learnings via pattern library
    """

    def __init__(
        self,
        name: str,
        domain: str,
        empathy_level: int | None = None,
        category: str | None = None,
    ):
        """Initialize a workflow

        Args:
            name: Human-readable workflow name
            domain: Domain this workflow belongs to (e.g., 'software', 'healthcare')
            empathy_level: Optional legacy level declaration (1-5). No longer
                required; retained for backward compatibility while its fate
                is decided for 15.0.0.
            category: Optional category within domain

        """
        self.name = name
        self.domain = domain
        self.empathy_level = 1 if empathy_level is None else empathy_level
        self.category = category
        self.logger = logging.getLogger(f"workflow.{domain}.{name}")

    @abstractmethod
    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze the given context and return results.

        This is the main entry point for all workflows. The context structure
        is domain-specific but the return format should follow a standard pattern.
        Subclasses must implement domain-specific analysis logic that aligns with
        the workflow's empathy level.

        Args:
            context: dict[str, Any]
                Domain-specific context dictionary. Must contain all fields returned
                by get_required_context(). Examples:
                - Software: {'code': str, 'file_path': str, 'language': str}
                - Healthcare: {'patient_id': str, 'vitals': dict, 'medications': list}
                - Finance: {'transactions': list, 'account': dict, 'period': str}

        Returns:
            dict[str, Any]
                Analysis results dictionary containing:
                - 'issues': list[dict] - Current issues found (Levels 1-3 analysis)
                - 'predictions': list[dict] - Future issues predicted (Level 4 analysis)
                - 'recommendations': list[dict] - Actionable next steps
                - 'patterns': list[str] - Patterns detected for the pattern library
                - 'confidence': float - Confidence score between 0.0 and 1.0
                - 'workflow': str - Name of the workflow that performed analysis
                - 'empathy_level': int - Empathy level of this analysis (1-5)
                - 'timestamp': str - ISO format timestamp of analysis

        Raises:
            ValueError: If context is invalid or missing required fields
            RuntimeError: If analysis fails due to domain-specific errors
            TimeoutError: If analysis takes too long to complete

        Note:
            - Validate context using self.validate_context() at the beginning
            - Each issue/prediction should include 'severity', 'description', 'affected_component'
            - Use self.contribute_patterns() to extract learnings for the pattern library
            - Confidence scores should reflect uncertainty in the analysis
            - This method is async to support long-running analyses

        """

    @abstractmethod
    def get_required_context(self) -> list[str]:
        """Declare what context fields this workflow needs.

        This method defines the contract between the caller and the workflow.
        The caller must provide all declared fields before calling analyze().
        This enables validation via validate_context() and helps with introspection.

        Returns:
            list[str]
                List of required context field names (keys). Each string should be
                a simple identifier that matches the keys in context dictionaries
                passed to analyze().

        Examples:
            Software workflow returns: ['code', 'file_path', 'language']
            Healthcare workflow returns: ['patient_id', 'vitals', 'medications']
            Finance workflow returns: ['transactions', 'account_id', 'period']

        Note:
            - Must return at least one field (even if minimal)
            - Field names should match exactly what analyze() expects in context
            - Order is not significant but consistency helps with documentation
            - Consider validation requirements when declaring fields
            - Used by validate_context() to check required fields before analyze()

        """

    def validate_context(self, context: dict[str, Any]) -> bool:
        """Validate that context contains required fields.

        Args:
            context: Context to validate

        Returns:
            True if valid, raises ValueError if invalid

        """
        required = self.get_required_context()
        missing = [key for key in required if key not in context]

        if missing:
            raise ValueError(f"Workflow '{self.name}' missing required context: {missing}")

        return True

    def get_empathy_level(self) -> int:
        """Get the empathy level this workflow operates at"""
        return self.empathy_level

    def contribute_patterns(self, analysis_result: dict[str, Any]) -> dict[str, Any]:
        """Extract patterns from analysis for the shared pattern library.

        This enables cross-domain learning (Level 5 Systems Empathy).

        Args:
            analysis_result: Result from analyze()

        Returns:
            Dictionary of patterns in standard format

        """
        # Default implementation - override for custom pattern extraction
        return {
            "workflow": self.name,
            "domain": self.domain,
            "timestamp": datetime.now().isoformat(),
            "patterns": analysis_result.get("patterns", []),
        }


class BasePlugin(ABC):
    """Base class for domain plugins.

    A plugin is a collection of workflows and patterns for a specific domain.

    Example:
        - SoftwarePlugin: 16+ coach workflows for code analysis
        - HealthcarePlugin: Clinical and compliance workflows
        - FinancePlugin: Fraud detection, compliance workflows

    """

    def __init__(self):
        """Initialize the domain plugin and register its workflows."""
        self.logger = logging.getLogger(f"plugin.{self.get_metadata().domain}")
        self._workflows: dict[str, type[BaseWorkflow]] = {}
        self._initialized = False

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return metadata about this plugin.

        This method provides essential information about the plugin that the
        framework uses for loading, validation, and discovery. It must return
        consistent metadata across multiple calls.

        Returns:
            PluginMetadata
                A PluginMetadata instance containing:
                - name: str - Human-readable plugin name (e.g., 'Software Plugin')
                - version: str - Semantic version string (e.g., '1.0.0')
                - domain: str - Domain this plugin serves (e.g., 'software', 'healthcare')
                - description: str - Brief description of plugin functionality
                - author: str - Plugin author or organization name
                - license: str - License identifier (e.g., 'Apache-2.0', 'MIT')
                - requires_core_version: str - Minimum core framework version (e.g., '1.0.0')
                - dependencies: list[str] - Optional list of required packages

        Note:
            - Called during plugin initialization to validate compatibility
            - Used for plugin discovery and listing
            - Should be immutable (return same values each call)
            - Version should follow semantic versioning
            - Domain names should be lowercase and consistent across plugins
            - Core version requirement ensures framework compatibility

        """

    @abstractmethod
    def register_workflows(self) -> dict[str, type[BaseWorkflow]]:
        """Register all workflows provided by this plugin.

        This method defines all analysis workflows available in this plugin.
        Workflows are lazy-instantiated by get_workflow() when first requested.
        This method is called during plugin initialization.

        Returns:
            dict[str, type[BaseWorkflow]]
                Dictionary mapping workflow identifiers to Workflow classes (not instances).
                Keys should be lowercase, snake_case identifiers. Values should be
                uninstantiated class references.

        Returns:
            dict[str, type[BaseWorkflow]]
                Mapping structure:
                {
                    'workflow_id': WorkflowClass,
                    'another_workflow': AnotherWorkflowClass,
                    ...
                }

        Example:
            Software plugin might return:
            {
                'security': SecurityWorkflow,
                'performance': PerformanceWorkflow,
                'maintainability': MaintainabilityWorkflow,
                'accessibility': AccessibilityWorkflow,
            }

        Note:
            - Return only the class, not instances (instantiation is lazy)
            - Use consistent, descriptive workflow IDs
            - All returned classes must be subclasses of BaseWorkflow
            - Can return empty dict {} if plugin provides no workflows initially
            - Called once during initialization via initialize()
            - Framework caches results in self._workflows

        """

    def register_patterns(self) -> dict[str, Any]:
        """Register domain-specific patterns for the pattern library.

        Returns:
            Dictionary of patterns in standard format

        """
        # Optional - override if plugin provides pre-built patterns
        return {}

    def initialize(self) -> None:
        """Initialize the plugin (lazy initialization).

        Called once before first use. Override to perform setup:
        - Load configuration
        - Initialize domain-specific services
        - Validate dependencies
        """
        if self._initialized:
            return

        self.logger.info(f"Initializing plugin: {self.get_metadata().name}")

        # Register workflows
        self._workflows = self.register_workflows()

        self.logger.info(
            f"Plugin '{self.get_metadata().name}' initialized with {len(self._workflows)} workflows",
        )

        self._initialized = True

    def on_activate(self) -> None:  # noqa: B027 -- intentional no-op default; subclasses override
        """Called after the plugin is fully registered in the registry.

        Override to perform post-registration setup such as:
        - Connecting to external services
        - Registering event listeners
        - Starting background tasks

        This is called once, after initialize() and register_plugin() succeed.
        """

    def register_mcp_tools(self, server: Any) -> None:  # noqa: B027
        """Register MCP tools contributed by this plugin.

        Override to add plugin-specific MCP tools to the
        server's tool registry. Called during server
        initialization after plugins are loaded.

        Args:
            server: AttuneMCPServer instance to register
                tools on.

        """

    def get_cli_commands(self) -> list[dict[str, str]]:
        """Return CLI commands contributed by this plugin.

        Override to expose plugin-specific CLI subcommands that will be
        registered under ``attune <plugin-domain> <command>``.

        Returns:
            List of command descriptors, each a dict with:
            - 'name': Command name (e.g., 'scan')
            - 'description': One-line help text
            - 'module': Dotted import path to the command handler module

        """
        return []

    def get_workflow(self, workflow_id: str) -> type[BaseWorkflow] | None:
        """Get a workflow by ID.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Workflow class or None if not found

        """
        if not self._initialized:
            self.initialize()

        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[str]:
        """List all workflow IDs provided by this plugin.

        Returns:
            List of workflow identifiers

        """
        if not self._initialized:
            self.initialize()

        return list(self._workflows.keys())

    def get_workflow_info(self, workflow_id: str) -> dict[str, Any] | None:
        """Get information about a workflow without instantiating it.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dictionary with workflow metadata

        """
        workflow_class = self.get_workflow(workflow_id)
        if not workflow_class:
            return None

        # Create temporary instance to get metadata
        # (workflows should be lightweight to construct)
        # Subclasses provide their own defaults for name, domain, empathy_level
        temp_instance = workflow_class()  # type: ignore[call-arg]

        return {
            "id": workflow_id,
            "name": temp_instance.name,
            "domain": temp_instance.domain,
            "empathy_level": temp_instance.empathy_level,
            "category": temp_instance.category,
            "required_context": temp_instance.get_required_context(),
        }


class PluginError(Exception):
    """Base exception for plugin-related errors"""


class PluginLoadError(PluginError):
    """Raised when plugin fails to load"""


class PluginValidationError(PluginError):
    """Raised when plugin fails validation"""
