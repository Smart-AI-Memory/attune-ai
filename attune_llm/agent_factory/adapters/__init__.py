"""attune_llm.agent_factory.adapters - DEPRECATED. Use attune.agent_factory.adapters instead.

This module has been moved to attune.agent_factory.adapters as part of the package
consolidation effort. This shim will be removed in v3.0.0.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

warnings.warn(
    "attune_llm.agent_factory.adapters is deprecated. "
    "Use attune.agent_factory.adapters instead. "
    "Will be removed in v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from attune.agent_factory.adapters import *  # noqa: F401,F403
