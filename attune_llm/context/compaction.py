"""attune_llm.context.compaction - DEPRECATED. Use attune.context.compaction instead.

This module re-exports from attune.context.compaction for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.context.compaction is deprecated. Use attune.context.compaction instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.context.compaction import *  # noqa: F401,F403
