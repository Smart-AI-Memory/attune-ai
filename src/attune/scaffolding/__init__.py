"""Methodology Scaffolding for Workflow Factory.

Provides CLI tools and methodologies for creating new workflows quickly
using proven patterns.

Methodologies:
- Pattern-Compose: Select patterns, compose workflow (Recommended)

Usage:
    # Create workflow using Pattern-Compose (recommended)
    python -m scaffolding create my_workflow --domain healthcare

    # Interactive mode
    python -m scaffolding create my_workflow --interactive

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune import __version__


def __getattr__(name: str):
    """Lazy imports for methodology classes that depend on dev-time packages."""
    if name == "PatternCompose":
        from .methodologies.pattern_compose import PatternCompose

        return PatternCompose
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PatternCompose",
    "__version__",
]
