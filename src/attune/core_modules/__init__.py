"""Core EmpathyOS Modules.

Modular implementation of EmpathyOS functionality.

Re-exports EmpathyOS and CollaborationState for backward compatibility.
Uses lazy imports to avoid circular dependency with core.py.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""


def __getattr__(name: str):
    """Lazy imports to avoid circular dependency with core.py."""
    if name == "EmpathyOS":
        from ..core import EmpathyOS

        return EmpathyOS
    if name == "CollaborationState":
        from ..core import CollaborationState

        return CollaborationState
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CollaborationState",
    "EmpathyOS",
]
