"""Test Audit Workflow Package.

Autonomous test coverage audit and generation. Runs a four-stage pipeline
to analyze code coverage, plan test additions, generate test specs, and
verify improvements.

Exports:
    TestAuditWorkflow: The main workflow class.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .workflow import TestAuditWorkflow

__all__ = ["TestAuditWorkflow"]
