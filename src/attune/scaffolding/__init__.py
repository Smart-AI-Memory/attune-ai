"""Methodology Scaffolding for Workflow Factory.

Provides CLI tools and methodologies for creating new workflows quickly
using proven patterns.

Methodologies:
- Pattern-Compose: Select patterns, compose workflow (Recommended)
- TDD-First: Write tests first, implement workflow
- Prototype-Refine: Quick prototype, then refactor
- Risk-Driven: Focus on high-risk paths first
- Empathy-Centered: Design for user experience

Usage:
    # Create workflow using Pattern-Compose (recommended)
    python -m scaffolding create my_workflow --domain healthcare

    # Create with specific methodology
    python -m scaffolding create my_workflow --methodology tdd

    # Interactive mode
    python -m scaffolding create my_workflow --interactive

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""


def __getattr__(name: str):
    """Lazy imports for methodology classes that depend on dev-time packages."""
    if name == "PatternCompose":
        from .methodologies.pattern_compose import PatternCompose

        return PatternCompose
    if name == "TDDFirst":
        from .methodologies.tdd_first import TDDFirst

        return TDDFirst
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PatternCompose",
    "TDDFirst",
]

__version__ = "1.0.0"
