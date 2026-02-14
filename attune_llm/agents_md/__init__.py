"""attune_llm.agents_md - DEPRECATED. Use attune.agents_md instead.

This module re-exports from attune.agents_md for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.agents_md is deprecated. Use attune.agents_md instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.agents_md import *  # noqa: F401,F403
from attune.agents_md import __all__  # noqa: F811
