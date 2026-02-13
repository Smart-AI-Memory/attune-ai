"""attune_llm.agent_factory.adapters.langchain_adapter - DEPRECATED. Use attune.agent_factory.adapters.langchain_adapter instead.

This module has been moved to attune.agent_factory.adapters.langchain_adapter as part of the package
consolidation effort. This shim will be removed in v3.0.0.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

warnings.warn(
    "attune_llm.agent_factory.adapters.langchain_adapter is deprecated. "
    "Use attune.agent_factory.adapters.langchain_adapter instead. "
    "Will be removed in v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from attune.agent_factory.adapters.langchain_adapter import *  # noqa: F401,F403
