"""attune_llm.hooks.scripts - DEPRECATED. Use attune.hooks.scripts instead.

This module re-exports from attune.hooks.scripts for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.scripts is deprecated. Use attune.hooks.scripts instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.scripts import *  # noqa: F401,F403
from attune.hooks.scripts import __all__  # noqa: F811
