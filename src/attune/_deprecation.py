"""Deprecation utilities for Attune AI.

Provides helpers for emitting deprecation warnings when
alternative CLI entry points are used.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import sys
import warnings


def _emit_cli_deprecation(module_name: str, canonical_command: str) -> None:
    """Emit a deprecation warning for alternative CLI entry points.

    Args:
        module_name: The module being invoked (e.g. "attune.telemetry")
        canonical_command: The preferred command (e.g. "attune telemetry <command>")
    """
    warnings.warn(
        f"'python -m {module_name}' is deprecated. " f"Use '{canonical_command}' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    print(
        f"WARNING: 'python -m {module_name}' is deprecated." f" Use '{canonical_command}' instead.",
        file=sys.stderr,
    )
