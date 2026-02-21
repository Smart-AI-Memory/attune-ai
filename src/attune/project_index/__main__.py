"""Enable running project_index as a module.

Usage:
    python -m attune.project_index refresh
    python -m attune.project_index summary
    python -m attune.project_index report health
    python -m attune.project_index query needing_tests

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune._deprecation import _emit_cli_deprecation

from .cli import main

if __name__ == "__main__":
    _emit_cli_deprecation("attune.project_index", "attune workflow run")
    exit(main())
