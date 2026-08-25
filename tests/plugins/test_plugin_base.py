"""Comprehensive tests for Plugin System Base Classes

Tests cover:
- PluginMetadata dataclass
- BaseWorkflow abstract class and methods
- BasePlugin abstract class and lifecycle
- Plugin exception classes
"""

import pytest

from attune.plugins.base import (
    BasePlugin,
    BaseWorkflow,
    PluginError,
    PluginLoadError,
    PluginMetadata,
    PluginValidationError,
)


class TestPluginMetadata:
    """Test PluginMetadata dataclass"""

    def test_plugin_metadata_creation(self):
        """Test PluginMetadata creation with all fields"""
        metadata = PluginMetadata(
            name="Test Plugin",
            version="1.0.0",
            domain="test",
            description="A test plugin",
            author="Test Author",
            license="Apache-2.0",
            requires_core_version="1.0.0",
            dependencies=["numpy", "pandas"],
        )

        assert metadata.name == "Test Plugin"
        assert metadata.version == "1.0.0"
        assert metadata.domain == "test"
        assert metadata.description == "A test plugin"
        assert metadata.author == "Test Author"
        assert metadata.license == "Apache-2.0"
        assert metadata.requires_core_version == "1.0.0"
        assert metadata.dependencies == ["numpy", "pandas"]

    def test_plugin_metadata_no_dependencies(self):
        """Test PluginMetadata without dependencies"""
        metadata = PluginMetadata(
            name="Simple Plugin",
            version="0.1.0",
            domain="simple",
            description="Simple",
            author="Author",
            license="MIT",
            requires_core_version="0.1.0",
        )

        assert metadata.dependencies is None


class TestBaseWorkflow:
    """Test BaseWorkflow abstract class"""

    def test_base_wizard_initialization(self):
        """Test BaseWorkflow initialization"""

        class ConcreteWizard(BaseWorkflow):
            async def analyze(self, context):
                return {
                    "issues": [],
                    "predictions": [],
                    "recommendations": [],
                    "patterns": [],
                    "confidence": 1.0,
                }

            def get_required_context(self):
                return ["input_data"]

        wizard = ConcreteWizard(
            name="Test Wizard",
            domain="test",
            category="testing",
        )

        assert wizard.name == "Test Wizard"
        assert wizard.domain == "test"
        assert wizard.category == "testing"

    def test_base_wizard_no_category(self):
        """Test BaseWorkflow without category"""

        class ConcreteWizard(BaseWorkflow):
            async def analyze(self, context):
                return {"issues": []}

            def get_required_context(self):
                return []

        wizard = ConcreteWizard(name="Simple", domain="test")

        assert wizard.category is None

    def test_wizard_validate_context_valid(self):
        """Test validate_context with valid context"""

        class ConcreteWizard(BaseWorkflow):
            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return ["code", "file_path"]

        wizard = ConcreteWizard(name="Test", domain="test")

        context = {"code": "def test(): pass", "file_path": "test.py"}

        assert wizard.validate_context(context) is True

    def test_wizard_validate_context_missing_fields(self):
        """Test validate_context with missing fields"""

        class ConcreteWizard(BaseWorkflow):
            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return ["code", "file_path", "language"]

        wizard = ConcreteWizard(name="Test", domain="test")

        context = {"code": "test"}

        with pytest.raises(
            ValueError,
            match="missing required context: \\['file_path', 'language'\\]",
        ):
            wizard.validate_context(context)

    def test_wizard_contribute_patterns_default(self):
        """Test default contribute_patterns implementation"""

        class ConcreteWizard(BaseWorkflow):
            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return []

        wizard = ConcreteWizard(name="PatternWizard", domain="patterns")

        analysis_result = {"patterns": ["pattern1", "pattern2"], "confidence": 0.9}

        patterns = wizard.contribute_patterns(analysis_result)

        assert patterns["workflow"] == "PatternWizard"
        assert patterns["domain"] == "patterns"
        assert "timestamp" in patterns
        assert patterns["patterns"] == ["pattern1", "pattern2"]

    def test_wizard_contribute_patterns_no_patterns(self):
        """Test contribute_patterns with no patterns in result"""

        class ConcreteWizard(BaseWorkflow):
            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return []

        wizard = ConcreteWizard(name="Test", domain="test")

        patterns = wizard.contribute_patterns({"confidence": 1.0})

        assert patterns["patterns"] == []


class TestBasePlugin:
    """Test BasePlugin abstract class"""

    def test_base_plugin_initialization(self):
        """Test BasePlugin initialization"""

        class ConcretePlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="Apache-2.0",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                return {}

        plugin = ConcretePlugin()

        assert plugin._initialized is False
        assert plugin._workflows == {}

    def test_plugin_initialize(self):
        """Test plugin initialization"""

        class TestWizard(BaseWorkflow):
            def __init__(self):
                super().__init__(name="Test", domain="test")

            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return []

        class ConcretePlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test Plugin",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="Apache-2.0",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                return {"test_wizard": TestWizard}

        plugin = ConcretePlugin()
        plugin.initialize()

        assert plugin._initialized is True
        assert len(plugin._workflows) == 1
        assert "test_wizard" in plugin._workflows

    def test_plugin_initialize_idempotent(self):
        """Test that initialize can be called multiple times safely"""

        class ConcretePlugin(BasePlugin):
            def __init__(self):
                super().__init__()
                self.init_count = 0

            def get_metadata(self):
                return PluginMetadata(
                    name="Test",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="MIT",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                self.init_count += 1
                return {}

        plugin = ConcretePlugin()

        plugin.initialize()
        plugin.initialize()
        plugin.initialize()

        assert plugin.init_count == 1  # Should only register once

    def test_plugin_get_workflow(self):
        """Test get_wizard method"""

        class TestWizard(BaseWorkflow):
            def __init__(self):
                super().__init__(name="Test", domain="test")

            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return []

        class ConcretePlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="MIT",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                return {"test": TestWizard}

        plugin = ConcretePlugin()
        wizard_class = plugin.get_workflow("test")

        assert wizard_class == TestWizard

    def test_plugin_get_wizard_not_found(self):
        """Test get_wizard with non-existent wizard"""

        class ConcretePlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="MIT",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                return {}

        plugin = ConcretePlugin()
        wizard_class = plugin.get_workflow("nonexistent")

        assert wizard_class is None

    def test_plugin_list_workflows(self):
        """Test list_wizards method"""

        class Wizard1(BaseWorkflow):
            def __init__(self):
                super().__init__(name="W1", domain="test")

            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return []

        class Wizard2(BaseWorkflow):
            def __init__(self):
                super().__init__(name="W2", domain="test")

            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return []

        class ConcretePlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="MIT",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                return {"wizard1": Wizard1, "wizard2": Wizard2}

        plugin = ConcretePlugin()
        wizard_list = plugin.list_workflows()

        assert len(wizard_list) == 2
        assert "wizard1" in wizard_list
        assert "wizard2" in wizard_list

    def test_plugin_get_workflow_info(self):
        """Test get_wizard_info method"""

        class TestWizard(BaseWorkflow):
            def __init__(self):
                super().__init__(
                    name="Info Wizard",
                    domain="test",
                    category="info",
                )

            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return ["data1", "data2"]

        class ConcretePlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="MIT",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                return {"test": TestWizard}

        plugin = ConcretePlugin()
        info = plugin.get_workflow_info("test")

        assert info is not None
        assert info["id"] == "test"
        assert info["name"] == "Info Wizard"
        assert info["domain"] == "test"
        assert info["category"] == "info"
        assert info["required_context"] == ["data1", "data2"]

    def test_plugin_get_wizard_info_not_found(self):
        """Test get_wizard_info for non-existent wizard"""

        class ConcretePlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="MIT",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                return {}

        plugin = ConcretePlugin()
        info = plugin.get_workflow_info("nonexistent")

        assert info is None

    def test_get_workflow_skips_init_when_already_initialized(self):
        """Test get_workflow skips initialize when plugin is already initialized."""

        class TestWizard(BaseWorkflow):
            def __init__(self):
                super().__init__(name="Test", domain="test")

            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return []

        class ConcretePlugin(BasePlugin):
            def __init__(self):
                super().__init__()
                self.init_count = 0

            def get_metadata(self):
                return PluginMetadata(
                    name="Test",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="MIT",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                self.init_count += 1
                return {"test": TestWizard}

        plugin = ConcretePlugin()
        plugin.initialize()
        assert plugin.init_count == 1

        # Call get_workflow on already-initialized plugin
        result = plugin.get_workflow("test")
        assert result == TestWizard
        assert plugin.init_count == 1  # initialize not called again

    def test_list_workflows_skips_init_when_already_initialized(self):
        """Test list_workflows skips initialize when plugin is already initialized."""

        class TestWizard(BaseWorkflow):
            def __init__(self):
                super().__init__(name="Test", domain="test")

            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return []

        class ConcretePlugin(BasePlugin):
            def __init__(self):
                super().__init__()
                self.init_count = 0

            def get_metadata(self):
                return PluginMetadata(
                    name="Test",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="MIT",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                self.init_count += 1
                return {"w1": TestWizard, "w2": TestWizard}

        plugin = ConcretePlugin()
        plugin.initialize()
        assert plugin.init_count == 1

        # Call list_workflows on already-initialized plugin
        workflows = plugin.list_workflows()
        assert len(workflows) == 2
        assert plugin.init_count == 1  # initialize not called again

    def test_plugin_register_patterns_default(self):
        """Test default register_patterns implementation"""

        class ConcretePlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Test",
                    version="1.0.0",
                    domain="test",
                    description="Test",
                    author="Test",
                    license="MIT",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                return {}

        plugin = ConcretePlugin()
        patterns = plugin.register_patterns()

        assert patterns == {}


class TestPluginExceptions:
    """Test plugin exception classes"""

    def test_plugin_error(self):
        """Test PluginError base exception"""
        with pytest.raises(PluginError, match="Test error"):
            raise PluginError("Test error")

    def test_plugin_load_error(self):
        """Test PluginLoadError exception"""
        with pytest.raises(PluginLoadError, match="Failed to load"):
            raise PluginLoadError("Failed to load")

    def test_plugin_validation_error(self):
        """Test PluginValidationError exception"""
        with pytest.raises(PluginValidationError, match="Validation failed"):
            raise PluginValidationError("Validation failed")

    def test_exception_inheritance(self):
        """Test exception inheritance hierarchy"""
        assert issubclass(PluginLoadError, PluginError)
        assert issubclass(PluginValidationError, PluginError)
        assert issubclass(PluginError, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
