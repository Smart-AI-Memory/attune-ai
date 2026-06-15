"""Tests for the release_agents re-export shim.

release_agents.py re-exports the agent classes that were refactored into
focused submodules, so existing
``from attune.agents.release.release_agents import ReleaseAgent`` imports
keep working. Previously omitted "Requires LLM API calls" — it is a pure
import shim with no LLM. Un-omitted alongside this file per the
omit-audit.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.agents.release import release_agents


class TestReExportShim:
    def test_all_names_exported(self):
        for name in (
            "CodeQualityAgent",
            "DocumentationAgent",
            "ReleaseAgent",
            "SecurityAuditorAgent",
            "TestCoverageAgent",
        ):
            assert name in release_agents.__all__
            assert hasattr(release_agents, name)

    def test_reexports_are_the_canonical_classes(self):
        from attune.agents.release.base_agent import ReleaseAgent as BaseReleaseAgent

        assert release_agents.ReleaseAgent is BaseReleaseAgent

    def test_run_command_helper_reexported(self):
        from attune.agents.release.base_agent import _run_command as canonical

        assert release_agents._run_command is canonical


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
