"""TDD-First methodology for workflow creation.

Write tests first, then implement workflow.

Workflow:
1. Generate comprehensive tests based on patterns
2. Run tests (they should all fail)
3. Generate minimal workflow skeleton
4. Implement workflow to make tests pass

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from pathlib import Path

from test_generator import TestGenerator

from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)


class TDDFirst:
    """TDD-First methodology: Write tests first, implement workflow.

    Benefits:
    - Better test coverage (tests written before code)
    - Clear specification (tests define behavior)
    - Prevents over-engineering (only code what's tested)
    """

    def __init__(self):
        """Initialize TDD-First methodology."""
        self.test_generator = TestGenerator()

    def create_workflow(
        self,
        name: str,
        domain: str,
        workflow_type: str,
        pattern_ids: list[str],
    ) -> dict:
        """Create workflow using TDD-First methodology.

        Args:
            name: Workflow name
            domain: Domain
            workflow_type: Workflow type
            pattern_ids: Pattern IDs to use

        Returns:
            Dictionary with files and next steps

        """
        logger.info(f"Creating workflow '{name}' using TDD-First methodology")

        # Step 1: Generate tests FIRST
        logger.info("Step 1: Generating tests...")
        tests = self.test_generator.generate_tests(
            workflow_id=name,
            pattern_ids=pattern_ids,
        )

        # Write test files
        test_dir = Path("tests/unit/workflows")
        test_dir.mkdir(parents=True, exist_ok=True)

        unit_test_file = test_dir / f"test_{name}_workflow.py"
        validated_unit_test = _validate_file_path(str(unit_test_file))
        with open(validated_unit_test, "w") as f:
            f.write(tests["unit"])

        fixtures_file = test_dir / f"fixtures_{name}.py"
        validated_fixtures = _validate_file_path(str(fixtures_file))
        with open(validated_fixtures, "w") as f:
            f.write(tests["fixtures"])

        # Step 2: Generate minimal workflow skeleton
        logger.info("Step 2: Generating minimal workflow skeleton...")
        workflow_file = self._generate_skeleton(name, workflow_type)

        logger.info(f"✓ Workflow '{name}' scaffolded with TDD-First methodology!")

        return {
            "files": [unit_test_file, fixtures_file, workflow_file],
            "next_steps": [
                f"1. Run tests (they should FAIL): pytest {unit_test_file}",
                "2. Read test failures to understand requirements",
                f"3. Implement workflow in {workflow_file} to make tests pass",
                "4. Run tests again until all pass",
                "5. Refactor while keeping tests green",
            ],
        }

    def _generate_skeleton(self, name: str, workflow_type: str) -> Path:
        """Generate minimal workflow skeleton.

        Args:
            name: Workflow name
            workflow_type: Workflow type

        Returns:
            Path to skeleton file

        """
        class_name = "".join(part.capitalize() for part in name.split("_")) + "Workflow"

        skeleton = f'''"""
{class_name} - Minimal skeleton for TDD.

Implement methods to make tests pass.
"""


class {class_name}:
    """Workflow for {name}."""

    def __init__(self):
        """Initialize workflow."""
        pass

    async def process(self, **kwargs):
        """Process workflow request.

        TODO: Implement to make tests pass.
        """
        raise NotImplementedError("Implement to make tests pass")
'''

        workflow_dir = Path("workflows")
        workflow_dir.mkdir(parents=True, exist_ok=True)

        workflow_file = workflow_dir / f"{name}_workflow.py"
        validated_workflow = _validate_file_path(str(workflow_file))
        with open(validated_workflow, "w") as f:
            f.write(skeleton)

        return validated_workflow
