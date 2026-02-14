"""attune_llm.agents_md.parser - DEPRECATED. Use attune.agents_md.parser instead.

This module re-exports from attune.agents_md.parser for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.agents_md.parser is deprecated. Use attune.agents_md.parser instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.agents_md.parser import *  # noqa: F401,F403
