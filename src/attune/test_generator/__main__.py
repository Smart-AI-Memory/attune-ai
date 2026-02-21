"""Make test_generator runnable as a module.

Usage:
    python -m test_generator generate soap_note --patterns linear_flow,approval
    python -m test_generator analyze debugging --patterns code_analysis_input

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune._deprecation import _emit_cli_deprecation

from .cli import main

if __name__ == "__main__":
    _emit_cli_deprecation("attune.test_generator", "attune workflow run test-gen")
    main()
