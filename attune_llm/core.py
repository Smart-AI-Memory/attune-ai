"""attune_llm.core - DEPRECATED. Use attune.llm.core instead.

This module has been moved to attune.llm.core as part of the package
consolidation effort. This shim will be removed in v3.0.0.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

warnings.warn(
    "attune_llm.core is deprecated. Use attune.llm.core instead. " "Will be removed in v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from attune.llm.core import *  # noqa: F401,F403
