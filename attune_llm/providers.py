"""attune_llm.providers - DEPRECATED. Use attune.llm.providers instead.

This module has been moved to attune.llm.providers as part of the package
consolidation effort. This shim will be removed in v3.0.0.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

warnings.warn(
    "attune_llm.providers is deprecated. Use attune.llm.providers instead. "
    "Will be removed in v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from attune.llm.providers import *  # noqa: F401,F403
