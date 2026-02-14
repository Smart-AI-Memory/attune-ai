"""attune_llm.hooks - DEPRECATED. Use attune.hooks instead.

This module re-exports from attune.hooks for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks is deprecated. Use attune.hooks instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks import *  # noqa: F401,F403
from attune.hooks import __all__  # noqa: F811
