"""attune_llm.state - DEPRECATED. Use attune.llm.state instead.

This module has been moved to attune.llm.state as part of the package
consolidation effort. This shim will be removed in v3.0.0.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

warnings.warn(
    "attune_llm.state is deprecated. Use attune.llm.state instead. "
    "Will be removed in v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from attune.llm.state import *  # noqa: F401,F403
