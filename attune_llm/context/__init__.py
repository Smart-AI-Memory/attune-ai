"""attune_llm.context - DEPRECATED. Use attune.context instead.

This module re-exports from attune.context for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.context is deprecated. Use attune.context instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.context import *  # noqa: F401,F403
from attune.context import __all__  # noqa: F811
