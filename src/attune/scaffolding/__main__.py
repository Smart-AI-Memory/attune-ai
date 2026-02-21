"""Scaffolding module entry point.

Usage:
    python -m scaffolding create my_workflow --domain healthcare
    python -m scaffolding list-patterns

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune._deprecation import _emit_cli_deprecation

from .cli import main

if __name__ == "__main__":
    _emit_cli_deprecation("attune.scaffolding", "attune workflow run")
    main()
