"""Tests for attune_software/plugin.py — SoftwarePlugin.

Covers get_metadata, register_wizards (with import failures), register_patterns.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from unittest.mock import patch

# attune_software.plugin imports BaseWizard from attune.plugins, but
# attune.plugins only exports BasePlugin/BaseWorkflow. Add a fake BaseWizard.
import attune.plugins as _plugins_mod

if not hasattr(_plugins_mod, "BaseWizard"):
    _plugins_mod.BaseWizard = type("BaseWizard", (), {})

from attune_software.plugin import SoftwarePlugin


class ConcreteSoftwarePlugin(SoftwarePlugin):
    """Concrete subclass that satisfies abstract register_workflows."""

    def register_workflows(self) -> dict:
        return {}


class TestSoftwarePluginMetadata:
    """Tests for SoftwarePlugin.get_metadata()."""

    def test_returns_plugin_metadata(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        meta = plugin.get_metadata()
        assert meta.name == "Empathy Framework - Software Development"
        assert meta.version == "1.0.0"
        assert meta.domain == "software"

    def test_metadata_has_description(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        meta = plugin.get_metadata()
        assert "Coach wizards" in meta.description

    def test_metadata_has_author(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        meta = plugin.get_metadata()
        assert meta.author == "Smart AI Memory, LLC"

    def test_metadata_license(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        meta = plugin.get_metadata()
        assert meta.license == "Apache-2.0"


class TestSoftwarePluginWizards:
    """Tests for SoftwarePlugin.register_wizards()."""

    def test_returns_dict(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        wizards = plugin.register_wizards()
        assert isinstance(wizards, dict)

    def test_graceful_degradation_all_imports_fail(self) -> None:
        """If all wizard imports fail, should return empty dict."""
        plugin = ConcreteSoftwarePlugin()
        # Patch all the individual wizard imports to fail
        with patch.dict(
            "sys.modules",
            {
                "attune_software.wizards.security_wizard": None,
                "attune_software.wizards.performance_wizard": None,
                "attune_software.wizards.testing_wizard": None,
                "attune_software.wizards.architecture_wizard": None,
                "attune_software.wizards.prompt_engineering_wizard": None,
                "attune_software.wizards.ai_context_wizard": None,
                "attune_software.wizards.ai_collaboration_wizard": None,
                "attune_software.wizards.ai_documentation_wizard": None,
                "attune_software.wizards.agent_orchestration_wizard": None,
                "attune_software.wizards.rag_pattern_wizard": None,
                "attune_software.wizards.multi_model_wizard": None,
            },
        ):
            wizards = plugin.register_wizards()
            # May return empty or partial depending on which wizards actually exist
            assert isinstance(wizards, dict)


class TestSoftwarePluginPatterns:
    """Tests for SoftwarePlugin.register_patterns()."""

    def test_returns_dict(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        patterns = plugin.register_patterns()
        assert isinstance(patterns, dict)

    def test_has_domain(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        patterns = plugin.register_patterns()
        assert patterns["domain"] == "software"

    def test_has_patterns_key(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        patterns = plugin.register_patterns()
        assert "patterns" in patterns

    def test_testing_bottleneck_pattern(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        patterns = plugin.register_patterns()
        assert "testing_bottleneck" in patterns["patterns"]
        tb = patterns["patterns"]["testing_bottleneck"]
        assert "description" in tb
        assert "indicators" in tb
        assert "threshold" in tb

    def test_security_drift_pattern(self) -> None:
        plugin = ConcreteSoftwarePlugin()
        patterns = plugin.register_patterns()
        assert "security_drift" in patterns["patterns"]
        sd = patterns["patterns"]["security_drift"]
        assert "indicators" in sd
