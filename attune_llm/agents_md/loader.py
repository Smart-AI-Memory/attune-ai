"""attune_llm.agents_md.loader - DEPRECATED. Use attune.agents_md.loader instead.

This module re-exports from attune.agents_md.loader for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.agents_md.loader is deprecated. Use attune.agents_md.loader instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.agents_md.loader import *  # noqa: F401,F403
