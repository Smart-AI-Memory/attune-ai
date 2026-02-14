"""Pattern-Compose methodology for workflow creation.

The recommended approach: Select patterns, compose workflow.

Workflow:
1. Get pattern recommendations based on workflow type and domain
2. User selects patterns to use
3. Generate workflow code from patterns
4. Generate tests with test generator
5. Generate documentation

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from attune.config import _validate_file_path

logger = logging.getLogger(__name__)


class PatternCompose:
    """Pattern-Compose methodology: Select patterns, compose workflow.

    This is the RECOMMENDED methodology for workflow creation because:
    - Leverages proven patterns from 78 existing workflows
    - Fast (10 minutes vs 2 hours manual)
    - Generates tests automatically
    - High quality, consistent code
    """

    def __init__(self):
        """Initialize Pattern-Compose methodology."""
        from attune.test_generator import TestGenerator
        from patterns import get_pattern_registry

        self.registry = get_pattern_registry()
        self.test_generator = TestGenerator()

        # Setup Jinja2 templates
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True,  # Enable autoescape for security (code gen templates should be safe)
        )

    def create_workflow(
        self,
        name: str,
        domain: str,
        workflow_type: str,
        selected_patterns: list[str] | None = None,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Create workflow using Pattern-Compose methodology.

        Args:
            name: Workflow name (e.g., "patient_intake")
            domain: Domain (e.g., "healthcare", "finance")
            workflow_type: Type (e.g., "domain", "coach", "ai")
            selected_patterns: Pre-selected pattern IDs (if None, will recommend)
            output_dir: Output directory (defaults to workflows/)

        Returns:
            Dictionary with:
                - files: List of generated file paths
                - patterns: List of patterns used
                - next_steps: List of next step instructions

        """
        logger.info(f"Creating workflow '{name}' using Pattern-Compose methodology")

        # Get pattern recommendations if not provided
        if selected_patterns is None:
            recommended = self.registry.recommend_for_workflow(
                workflow_type=workflow_type,
                domain=domain,
            )
            selected_patterns = [p.id for p in recommended if p]

        logger.info(f"Using {len(selected_patterns)} patterns: {', '.join(selected_patterns)}")

        # Get pattern objects
        patterns = [self.registry.get(pid) for pid in selected_patterns if self.registry.get(pid)]

        # Determine output directory
        if output_dir is None:
            if workflow_type == "domain":
                output_dir = Path("attune/workflows")
            else:
                output_dir = Path("workflows")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate workflow file
        workflow_file = self._generate_workflow_file(
            name=name,
            domain=domain,
            workflow_type=workflow_type,
            patterns=patterns,
            output_dir=output_dir,
        )

        # Generate tests
        test_files = self._generate_tests(
            name=name,
            pattern_ids=selected_patterns,
        )

        # Generate README
        readme_file = self._generate_readme(
            name=name,
            domain=domain,
            patterns=patterns,
            output_dir=output_dir,
        )

        # Collect all generated files
        generated_files = [workflow_file, readme_file] + test_files

        # Next steps
        next_steps = [
            f"1. Review generated workflow: {workflow_file}",
            f"2. Run tests: pytest {test_files[0] if test_files else 'tests/'}",
            "3. Register workflow in backend/api/workflow_api.py",
            f"4. Test via API: POST /api/workflow/{name}/process",
        ]

        logger.info(f"✓ Workflow '{name}' created successfully!")

        return {
            "files": generated_files,
            "patterns": [p.name for p in patterns],
            "next_steps": next_steps,
        }

    def _generate_workflow_file(
        self,
        name: str,
        domain: str,
        workflow_type: str,
        patterns: list,
        output_dir: Path,
    ) -> Path:
        """Generate workflow Python file.

        Args:
            name: Workflow name
            domain: Domain
            workflow_type: Workflow type
            patterns: List of pattern objects
            output_dir: Output directory

        Returns:
            Path to generated file

        """
        # Get template based on workflow type
        template_name = self._get_template_name(workflow_type, patterns)
        template = self.env.get_template(template_name)

        # Build context
        from datetime import datetime

        # Determine total steps for linear flow workflows
        total_steps = 5  # Default
        linear_pattern = next((p for p in patterns if p.id == "linear_flow"), None)
        if linear_pattern and hasattr(linear_pattern, "total_steps"):
            total_steps = linear_pattern.total_steps

        # Determine empathy level
        empathy_level = 2  # Default: Informational Empathy
        empathy_pattern = next((p for p in patterns if p.id == "empathy_level"), None)
        if empathy_pattern and hasattr(empathy_pattern, "levels"):
            empathy_level = (
                empathy_pattern.default_level if hasattr(empathy_pattern, "default_level") else 2
            )

        context = {
            "workflow_name": name,
            "workflow_class": self._to_class_name(name),
            "domain": domain,
            "workflow_type": workflow_type,
            "methodology": "pattern-compose",
            "timestamp": datetime.now().isoformat(),
            "description": f"{self._to_title(name)} workflow for {domain}",
            "patterns": patterns,
            "pattern_ids": [p.id for p in patterns],
            "has_linear_flow": any(p.id == "linear_flow" for p in patterns),
            "has_approval": any(p.id == "approval" for p in patterns),
            "has_structured_fields": any(p.id == "structured_fields" for p in patterns),
            "total_steps": total_steps,
            "empathy_level": empathy_level,
            "educational_message": f"This workflow will guide you through creating a {self._to_title(name)}.",
        }

        # Render template
        workflow_code = template.render(**context)

        # Write file
        workflow_file = output_dir / f"{name}_workflow.py"
        validated_workflow = _validate_file_path(str(workflow_file))
        with open(validated_workflow, "w") as f:
            f.write(workflow_code)

        logger.info(f"✓ Generated workflow file: {validated_workflow}")
        return workflow_file

    def _generate_tests(self, name: str, pattern_ids: list[str]) -> list[Path]:
        """Generate tests for workflow.

        Args:
            name: Workflow name
            pattern_ids: Pattern IDs

        Returns:
            List of generated test file paths

        """
        logger.info(f"Generating tests for {name}...")

        tests = self.test_generator.generate_tests(
            workflow_id=name,
            pattern_ids=pattern_ids,
        )

        test_files = []

        # Write unit tests
        unit_test_file = Path(f"tests/unit/workflows/test_{name}_workflow.py")
        unit_test_file.parent.mkdir(parents=True, exist_ok=True)
        validated_unit_test = _validate_file_path(str(unit_test_file))
        with open(validated_unit_test, "w") as f:
            f.write(tests["unit"])
        test_files.append(validated_unit_test)
        logger.info(f"✓ Generated unit tests: {validated_unit_test}")

        # Write fixtures
        fixtures_file = Path(f"tests/unit/workflows/fixtures_{name}.py")
        validated_fixtures = _validate_file_path(str(fixtures_file))
        with open(validated_fixtures, "w") as f:
            f.write(tests["fixtures"])
        test_files.append(validated_fixtures)
        logger.info(f"✓ Generated fixtures: {validated_fixtures}")

        return test_files

    def _generate_readme(
        self,
        name: str,
        domain: str,
        patterns: list,
        output_dir: Path,
    ) -> Path:
        """Generate README for workflow.

        Args:
            name: Workflow name
            domain: Domain
            patterns: Pattern objects
            output_dir: Output directory

        Returns:
            Path to README file

        """
        readme_content = f"""# {self._to_title(name)} Workflow

**Domain:** {domain}
**Type:** Workflow
**Generated:** Pattern-Compose Methodology

## Overview

Auto-generated workflow using proven patterns from the Attune AI.

## Patterns Used

{chr(10).join(f"- **{p.name}**: {p.description}" for p in patterns)}

## Usage

```python
from {output_dir.name}.{name}_workflow import {self._to_class_name(name)}

workflow = {self._to_class_name(name)}()
result = await workflow.process(user_input="...")
```

## API Endpoints

```bash
# Process with workflow
POST /api/workflow/{name}/process
{{
  "input": "your input here",
  "context": {{}}
}}
```

## Testing

```bash
# Run unit tests
pytest tests/unit/workflows/test_{name}_workflow.py

# Run with coverage
pytest tests/unit/workflows/test_{name}_workflow.py --cov
```

## Next Steps

1. Customize workflow logic as needed
2. Add domain-specific validation
3. Extend with additional features
4. Update tests for custom logic

---

**Generated by:** Attune AI - Workflow Factory
**Methodology:** Pattern-Compose
"""

        readme_file = output_dir / f"{name}_README.md"
        validated_readme = _validate_file_path(str(readme_file))
        with open(validated_readme, "w") as f:
            f.write(readme_content)

        logger.info(f"✓ Generated README: {validated_readme}")
        return readme_file

    def _get_template_name(self, workflow_type: str, patterns: list) -> str:
        """Get template name based on workflow type and patterns.

        Args:
            workflow_type: Workflow type
            patterns: Pattern objects

        Returns:
            Template filename

        """
        # Check for specific pattern combinations
        has_linear_flow = any(p.id == "linear_flow" for p in patterns)

        if has_linear_flow:
            return "linear_flow_workflow.py.jinja2"
        elif workflow_type == "coach":
            return "coach_workflow.py.jinja2"
        elif workflow_type == "domain":
            return "domain_workflow.py.jinja2"
        else:
            return "base_workflow.py.jinja2"

    def _to_class_name(self, name: str) -> str:
        """Convert workflow name to class name.

        Args:
            name: Workflow name (snake_case)

        Returns:
            Class name (PascalCase)

        """
        parts = name.split("_")
        return "".join(part.capitalize() for part in parts) + "Workflow"

    def _to_title(self, name: str) -> str:
        """Convert workflow name to title.

        Args:
            name: Workflow name (snake_case)

        Returns:
            Title (Title Case)

        """
        parts = name.split("_")
        return " ".join(part.capitalize() for part in parts)
