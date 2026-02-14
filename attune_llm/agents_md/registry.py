"""attune_llm.agents_md.registry - DEPRECATED. Use attune.agents_md.registry instead.

This module re-exports from attune.agents_md.registry for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.agents_md.registry is deprecated. Use attune.agents_md.registry instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.agents_md.registry import *  # noqa: F401,F403
