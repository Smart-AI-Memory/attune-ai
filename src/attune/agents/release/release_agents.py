"""Re-export shim for backward compatibility.

All public symbols that were originally defined in this module have been
refactored into focused submodules:

- base_agent: ReleaseAgent base class and _run_command helper
- security_agent: SecurityAuditorAgent
- coverage_agent: TestCoverageAgent
- quality_agent: CodeQualityAgent
- documentation_agent: DocumentationAgent

This module re-exports every public name so that existing imports like
``from attune.agents.release.release_agents import ReleaseAgent``
continue to work unchanged.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from .base_agent import ReleaseAgent, _run_command
from .coverage_agent import TestCoverageAgent
from .documentation_agent import DocumentationAgent
from .quality_agent import CodeQualityAgent
from .security_agent import SecurityAuditorAgent

__all__ = [
    "CodeQualityAgent",
    "DocumentationAgent",
    "ReleaseAgent",
    "SecurityAuditorAgent",
    "TestCoverageAgent",
    "_run_command",
]
