"""attune_llm.levels - DEPRECATED. Use attune.llm.levels instead.

This module has been moved to attune.llm.levels as part of the package
consolidation effort. This shim will be removed in v3.0.0.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

warnings.warn(
    "attune_llm.levels is deprecated. Use attune.llm.levels instead. "
    "Will be removed in v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from attune.llm.levels import *  # noqa: F401,F403
