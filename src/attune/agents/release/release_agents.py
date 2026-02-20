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

from .base_agent import ReleaseAgent, _run_command  # noqa: F401
from .coverage_agent import TestCoverageAgent  # noqa: F401
from .documentation_agent import DocumentationAgent  # noqa: F401
from .quality_agent import CodeQualityAgent  # noqa: F401
from .security_agent import SecurityAuditorAgent  # noqa: F401

__all__ = [
    "ReleaseAgent",
    "SecurityAuditorAgent",
    "TestCoverageAgent",
    "CodeQualityAgent",
    "DocumentationAgent",
    "_run_command",
]
